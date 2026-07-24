from django.db import models

from accounts.models import User
from projects.models import Project


class ChatRoom(models.Model):
    class Type(models.TextChoices):
        DIRECT = 'DIRECT', 'Direct Message'
        GROUP = 'GROUP', 'Group Chat'

    type = models.CharField(max_length=20, choices=Type.choices)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True)

    # True once the related project reaches TERMINATED. The room and its
    # messages are kept forever (never hard-deleted); this just stops new
    # messages from being sent.
    is_closed = models.BooleanField(default=False)


class ChatParticipant(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    notifications_muted = models.BooleanField(default=False)  # reserved for future use

    # Soft-delete: False means this user removed the conversation from
    # their own inbox. The room/messages are untouched for the other side.
    is_active = models.BooleanField(default=True)
    left_at = models.DateTimeField(null=True, blank=True)

    # Used to compute the unread-message badge in the inbox.
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['room', 'user'], name='unique_chat_participant_pk')
        ]


class Message(models.Model):
    id = models.BigAutoField(primary_key=True)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.RESTRICT)
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)