from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User

from . import services
from .models import ChatRoom
from .serialization import serialize_message


@login_required
def inbox_view(request):
    conversations = services.get_inbox_for_user(request.user)
    return render(request, 'chat/inbox.html', {'conversations': conversations})


@login_required
def room_view(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)

    if not services.is_active_participant(room.id, request.user.id):
        return HttpResponseForbidden("You are not a participant of this conversation.")

    services.mark_room_read(room.id, request.user.id)
    messages = services.get_room_messages(room.id)

    context = {
        'room': room,
        'messages': messages,
        'websocket_path': f'/ws/chat/room/{room.id}/',
    }
    return render(request, 'chat/room.html', context)


@login_required
def start_direct_chat_view(request, user_id):
    """
    Target of the "Start Chat" button on a user's public profile.
    Does NOT create a ChatRoom — only the first sent message does that.
    """
    other_user = get_object_or_404(User, id=user_id, is_active=True)

    if other_user.id == request.user.id:
        return redirect('chat:inbox')

    existing_room_id = (
        ChatRoom.objects.filter(type=ChatRoom.Type.DIRECT, chatparticipant__user=request.user)
        .filter(chatparticipant__user=other_user)
        .values_list('id', flat=True)
        .first()
    )
    if existing_room_id:
        return redirect('chat:room', room_id=existing_room_id)

    context = {
        'other_user': other_user,
        'websocket_path': f'/ws/chat/user/{other_user.id}/',
    }
    return render(request, 'chat/new_direct_chat.html', context)


@login_required
def messages_history_api(request, room_id):
    """AJAX endpoint for the 'load older messages' button (keyset pagination)."""
    if not services.is_active_participant(room_id, request.user.id):
        return HttpResponseForbidden()

    before_id = request.GET.get('before')
    before_id = int(before_id) if before_id and before_id.isdigit() else None

    messages = services.get_room_messages(room_id, before_id=before_id, limit=30)
    return JsonResponse({'messages': [serialize_message(m) for m in messages]})


@login_required
@require_POST
def delete_conversation_view(request, room_id):
    """DELETE /conversations/:id equivalent — soft delete, only for this user."""
    if not services.is_active_participant(room_id, request.user.id):
        return HttpResponseForbidden()

    services.soft_leave_room(room_id, request.user.id)
    return JsonResponse({'status': 'ok'})