"""
Core business logic for the chat app: room creation, participant
management, read-state tracking, and inbox/message queries.
Kept separate from views/consumers so both the HTTP layer and the
WebSocket layer can reuse the exact same logic.
"""
from django.db.models import Max
from django.utils import timezone

from .models import ChatRoom, ChatParticipant, Message

MAX_MESSAGE_LENGTH = 5000


# ---------------------------------------------------------------------------
# Room / participant helpers
# ---------------------------------------------------------------------------

def get_or_create_direct_room(user_a, user_b):
    """
    Returns the DIRECT ChatRoom between two users, creating it (and both
    ChatParticipant rows) if it doesn't exist yet. Reactivates a
    participant who had previously soft-deleted this conversation.
    """
    existing_room_id = (
        ChatRoom.objects.filter(type=ChatRoom.Type.DIRECT, chatparticipant__user=user_a)
        .filter(chatparticipant__user=user_b)
        .values_list('id', flat=True)
        .first()
    )

    room = (
        ChatRoom.objects.get(id=existing_room_id)
        if existing_room_id
        else ChatRoom.objects.create(type=ChatRoom.Type.DIRECT, project=None)
    )

    for user in (user_a, user_b):
        participant, created = ChatParticipant.objects.get_or_create(
            room=room, user=user,
            defaults={'is_active': True, 'last_read_at': timezone.now()},
        )
        if not created and not participant.is_active:
            participant.is_active = True
            participant.left_at = None
            participant.save(update_fields=['is_active', 'left_at'])

    return room


def save_message(room_id, sender_id, content):
    content = content.strip()[:MAX_MESSAGE_LENGTH]
    return Message.objects.create(room_id=room_id, sender_id=sender_id, content=content)


def send_first_or_next_direct_message(user_id, other_user_id, content):
    """Used by DirectChatConsumer: guarantees the room exists, then saves the message."""
    from accounts.models import User

    user = User.objects.get(id=user_id)
    other_user = User.objects.get(id=other_user_id)
    room = get_or_create_direct_room(user, other_user)

    if room.is_closed:
        return room, None

    message = save_message(room.id, user_id, content)
    return room, message


def is_active_participant(room_id, user_id):
    return ChatParticipant.objects.filter(
        room_id=room_id, user_id=user_id, is_active=True
    ).exists()


def soft_leave_room(room_id, user_id):
    """DELETE /conversations/:id equivalent — hides the conversation for this user only."""
    ChatParticipant.objects.filter(room_id=room_id, user_id=user_id).update(
        is_active=False, left_at=timezone.now()
    )


def mark_room_read(room_id, user_id):
    ChatParticipant.objects.filter(room_id=room_id, user_id=user_id).update(
        last_read_at=timezone.now()
    )


# ---------------------------------------------------------------------------
# Group chat automation (called from signals.py)
# ---------------------------------------------------------------------------

def open_group_chat_for_project(project):
    """
    Called when a project's state transitions into IN_PROGRESS for the
    first time. Creates the GROUP ChatRoom (if missing) and adds all
    currently active members, plus the PM, as participants.
    """
    room, _ = ChatRoom.objects.get_or_create(project=project, type=ChatRoom.Type.GROUP)

    active_member_ids = set(
        project.projectmember_set.filter(member_status='ACTIVE').values_list('user_id', flat=True)
    )
    # The PM might have no technical role in ProjectMember, but must
    # always be part of the group chat.
    active_member_ids.add(project.pm_id)

    for user_id in active_member_ids:
        participant, created = ChatParticipant.objects.get_or_create(
            room=room, user_id=user_id,
            defaults={'is_active': True, 'last_read_at': timezone.now()},
        )
        if not created and not participant.is_active:
            participant.is_active = True
            participant.left_at = None
            participant.save(update_fields=['is_active', 'left_at'])

    return room


def close_group_chat_for_project(project):
    """Called when a project reaches TERMINATED. Room becomes read-only."""
    ChatRoom.objects.filter(project=project, type=ChatRoom.Type.GROUP).update(is_closed=True)


def sync_participant_for_membership_change(project, user_id, member_status):
    """
    Keeps the GROUP chat roster in sync with projects_projectmember
    changes that happen AFTER the group chat already exists (e.g.
    someone resigns, or a new member joins mid-project).
    """
    room = ChatRoom.objects.filter(project=project, type=ChatRoom.Type.GROUP).first()
    if room is None:
        return  # project isn't IN_PROGRESS yet, nothing to sync

    if member_status == 'ACTIVE':
        participant, created = ChatParticipant.objects.get_or_create(
            room=room, user_id=user_id,
            defaults={'is_active': True, 'last_read_at': timezone.now()},
        )
        if not created and not participant.is_active:
            participant.is_active = True
            participant.left_at = None
            participant.save(update_fields=['is_active', 'left_at'])
    else:  # RESIGNED / REMOVED
        ChatParticipant.objects.filter(room=room, user_id=user_id).update(
            is_active=False, left_at=timezone.now()
        )


# ---------------------------------------------------------------------------
# Inbox / message history queries
# ---------------------------------------------------------------------------

def get_inbox_for_user(user):
    """
    Returns one dict per active conversation the user belongs to, sorted
    by most recent message first, with display name, last message
    preview, and unread count.
    """
    participants = (
        ChatParticipant.objects.filter(user=user, is_active=True)
        .select_related('room', 'room__project')
        .annotate(last_message_at=Max('room__message__sent_at'))
        .order_by('-last_message_at')
    )

    inbox = []
    for participant in participants:
        room = participant.room
        last_message = room.message_set.order_by('-id').first()

        unread_qs = room.message_set.exclude(sender=user)
        if participant.last_read_at:
            unread_qs = unread_qs.filter(sent_at__gt=participant.last_read_at)
        unread_count = unread_qs.count()

        if room.type == ChatRoom.Type.DIRECT:
            other = (
                ChatParticipant.objects.filter(room=room)
                .exclude(user=user)
                .select_related('user', 'user__avatar_icon')
                .first()
            )
            display_name = other.user.username if other else 'Unknown'
            avatar = other.user.avatar_icon if other else None
        else:
            display_name = room.project.title if room.project else 'Group Chat'
            avatar = None

        inbox.append({
            'room_id': room.id,
            'type': room.type,
            'display_name': display_name,
            'avatar_icon': avatar,
            'last_message_content': last_message.content if last_message else '',
            'last_message_at': last_message.sent_at if last_message else None,
            'unread_count': unread_count,
            'is_closed': room.is_closed,
        })

    return inbox


def get_room_messages(room_id, before_id=None, limit=30):
    """
    Keyset (cursor) pagination: returns up to `limit` messages older than
    `before_id`, oldest-first (ready to append to the top of the chat).
    """
    qs = Message.objects.filter(room_id=room_id).select_related('sender').order_by('-id')
    if before_id:
        qs = qs.filter(id__lt=before_id)

    messages = list(qs[:limit])
    messages.reverse()
    return messages