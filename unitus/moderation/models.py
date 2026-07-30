from django.db import models
from accounts.models import User


class Report(models.Model):
    class Reason(models.TextChoices):
        INACTIVITY = 'INACTIVITY'
        INSULTING = 'INSULTING'
        FAKE_PROJECT = 'FAKE_PROJECT'
        OTHER = 'OTHER'

    class Status(models.TextChoices):
        PENDING_REVIEW = 'PENDING_REVIEW'
        RESOLVED = 'RESOLVED'
        DISMISSED = 'DISMISSED'

    reporter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports_made')
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_received')
    reason = models.CharField(max_length=20, choices=Reason.choices)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_REVIEW)
    reviewed_by_admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports_reviewed')
    created_at = models.DateTimeField(auto_now_add=True)


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = 'CREATE'
        UPDATE = 'UPDATE'
        DELETE = 'DELETE'
        STATUS_CHANGE = 'STATUS_CHANGE'

    id = models.BigAutoField(primary_key=True)
    entity_type = models.CharField(max_length=50)
    entity_id = models.IntegerField()
    action = models.CharField(max_length=20, choices=Action.choices)
    # NEW: short human-readable summary of what changed, e.g.
    # "account_status: ACTIVE -> BANNED" or "PENDING_REVIEW -> RESOLVED".
    # Nullable so it's backwards compatible with any rows written before
    # this field existed.
    details = models.CharField(max_length=255, null=True, blank=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.entity_type}#{self.entity_id} {self.action}'
