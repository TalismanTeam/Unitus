from django.utils import timezone
from django.template.defaultfilters import date as django_date

def serialize_message(message):
    local_time = timezone.localtime(message.sent_at)
    
    return {
        'id': message.id,
        'room_id': message.room_id,
        'sender_id': message.sender_id,
        'sender_username': message.sender.username,
        'content': message.content,

        'sent_at': django_date(local_time, "F j, Y, g:i a"),
    }