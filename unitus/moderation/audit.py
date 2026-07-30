import logging

from .models import AuditLog

logger = logging.getLogger(__name__)


def log_action(*, entity_type, entity_id, action, performed_by, details=None):
    """
    Writes one row to AuditLog. Call this from anywhere in the project that
    changes something an admin should be able to see later — report status
    changes, a user getting suspended/banned, etc.

    entity_type: short string naming the model, e.g. "Report", "User".
    entity_id:   pk of the affected row.
    action:      one of AuditLog.Action.values.
    performed_by: the admin/user who did it (can be None for system actions).
    details:     optional short human-readable summary of the change.

    Never raises — a logging failure should never block the action that
    triggered it, it just gets logged to the app logger instead.
    """
    try:
        AuditLog.objects.create(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            performed_by=performed_by,
            details=details,
        )
    except Exception:
        logger.exception(
            'Failed to write AuditLog entry for %s#%s (%s)',
            entity_type, entity_id, action,
        )
