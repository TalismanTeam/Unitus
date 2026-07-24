def serialize_message(message):
    return {
        'id': message.id,
        'room_id': message.room_id,
        'sender_id': message.sender_id,
        'sender_username': message.sender.username,
        'content': message.content,
        'sent_at': message.sent_at.isoformat(),
    }