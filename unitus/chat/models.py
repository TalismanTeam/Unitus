from django.db import models
from accounts.models import User
from projects.models import Project


class ChatRoom(models.Model):
    class Type(models.TextChoices):
        DIRECT_MESSAGE = 'DIRECT_MESSAGE'
        GROUP_CHAT = 'GROUP_CHAT'

    type = models.CharField(max_length=20, choices=Type.choices)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True)


class ChatParticipant(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notifications_muted = models.BooleanField(default=False)

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