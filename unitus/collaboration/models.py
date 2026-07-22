from django.db import models
from accounts.models import User
from projects.models import Project, ProjectRole


class Ticket(models.Model):
    class TicketType(models.TextChoices):
        COLLAB_REQUEST = 'COLLAB_REQUEST'
        INVITATION = 'INVITATION'
        RESIGNATION = 'RESIGNATION'

    class Status(models.TextChoices):
        PENDING_FEEDBACK = 'PENDING_FEEDBACK'
        WAITING_FOR_US = 'WAITING_FOR_US'
        CLOSED_ACCEPTED = 'CLOSED_ACCEPTED'
        CLOSED_REJECTED = 'CLOSED_REJECTED'
        CANCELLED = 'CANCELLED'

    sender = models.ForeignKey(User, on_delete=models.RESTRICT, related_name='sent_tickets')
    receiver = models.ForeignKey(User, on_delete=models.RESTRICT, related_name='received_tickets')
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    project_role = models.ForeignKey(ProjectRole, on_delete=models.CASCADE, null=True, blank=True)
    ticket_type = models.CharField(max_length=20, choices=TicketType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_FEEDBACK, db_index=True)
    message_text = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)