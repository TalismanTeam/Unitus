def serialize_user_summary(user):
    return {
        'id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
    }


def serialize_project_summary(project):
    return {
        'id': project.id,
        'title': project.title,
        'state': project.state,
    }


def serialize_project_role_summary(project_role):
    if project_role is None:
        return None
    return {
        'id': project_role.id,
        'role_title': project_role.role_title,
    }


def serialize_ticket(ticket, request_user):
    """
    request_user is the logged-in user viewing this ticket. Used only to
    compute the 'direction' field (sent vs received) — the ticket itself
    already stores sender/receiver regardless of who's looking at it.
    """
    return {
        'id': ticket.id,
        'ticket_type': ticket.ticket_type,
        'status': ticket.status,
        'message_text': ticket.message_text,
        'created_at': ticket.created_at.isoformat(),
        'updated_at': ticket.updated_at.isoformat(),
        'direction': 'sent' if ticket.sender_id == request_user.id else 'received',
        'project': serialize_project_summary(ticket.project),
        'project_role': serialize_project_role_summary(ticket.project_role),
        'sender': serialize_user_summary(ticket.sender),
        'receiver': serialize_user_summary(ticket.receiver),
    }
