def serialize_report(report, *, for_admin=False):
    """
    Dict-builder for a Report instance.

    `for_admin=True` includes the reporter's identity and review metadata
    (who reviewed it, if anyone) — fields a reported user should never see
    about themselves, and fields irrelevant to the reporting user once
    they've submitted their report.
    """
    data = {
        'id': report.id,
        'reason': report.reason,
        'description': report.description,
        'status': report.status,
        'created_at': report.created_at.isoformat(),
        'reported_user': {
            'id': report.reported_user_id,
            'username': report.reported_user.username,
        },
    }

    if for_admin:
        data['reporter'] = (
            {'id': report.reporter_id, 'username': report.reporter.username}
            if report.reporter_id else None
        )
        data['reviewed_by_admin'] = (
            {'id': report.reviewed_by_admin_id, 'username': report.reviewed_by_admin.username}
            if report.reviewed_by_admin_id else None
        )

    return data


def serialize_audit_log(entry):
    """Dict-builder for an AuditLog row. Admin-only data by nature."""
    return {
        'id': entry.id,
        'entity_type': entry.entity_type,
        'entity_id': entry.entity_id,
        'action': entry.action,
        'details': entry.details,
        'performed_by': (
            {'id': entry.performed_by_id, 'username': entry.performed_by.username}
            if entry.performed_by_id else None
        ),
        'timestamp': entry.timestamp.isoformat(),
    }
