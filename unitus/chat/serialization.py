from django.utils import timezone
from django.template.defaultfilters import date as django_date

def serialize_message(message):
    local_time = timezone.localtime(message.sent_at)
    
    return {
        'id': message.id,
        'room_id': message.room_id,
        'sender': {
            'id': message.sender_id,
            'username': message.sender.username,
        },
        'content': message.content,

        # 'sent_at': django_date(local_time, "F j, Y, g:i a"),
        'sent_at': message.sent_at.isoformat(),
    }


def serialize_conversation_summary(summary):
    return {
        'room_id': summary['room_id'],
        'type': summary['type'],
        'display_name': summary['display_name'],
        'avatar_icon_name': summary['avatar_icon'].icon_name if summary['avatar_icon'] else None,
        'last_message_content': summary['last_message_content'],
        'last_message_at': summary['last_message_at'].isoformat() if summary['last_message_at'] else None,
        'unread_count': summary['unread_count'],
        'is_closed': summary['is_closed'],
    }