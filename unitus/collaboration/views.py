import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from accounts.models import User
from projects.models import Project, ProjectRole, ProjectMember

from .models import Ticket
from .serialization import serialize_ticket

# Accepts either the SRS-doc-friendly names ('application' / 'invitation' /
# 'resignation') or the raw model values ('COLLAB_REQUEST' / 'INVITATION' /
# 'RESIGNATION') in the POST /tickets 'type' field.
TICKET_TYPE_ALIASES = {
    'application': Ticket.TicketType.COLLAB_REQUEST,
    'invitation': Ticket.TicketType.INVITATION,
    'resignation': Ticket.TicketType.RESIGNATION,
}
TICKET_TYPE_ALIASES.update({value: value for value in Ticket.TicketType.values})

CLOSED_STATUSES = [
    Ticket.Status.CLOSED_ACCEPTED,
    Ticket.Status.CLOSED_REJECTED,
    Ticket.Status.CANCELLED,
]


def _parse_json_body(request):
    try:
        return json.loads(request.body or '{}'), None
    except json.JSONDecodeError:
        return None, JsonResponse({'error': 'Invalid JSON body'}, status=400)


def _error(message, status=400):
    return JsonResponse({'error': message}, status=status)


# ---------------------------------------------------------------------------
# GET / — renders the ticket management page (templates/ticketManagement.html).
# The JS on that page then calls the JSON endpoints below via fetch().
# ---------------------------------------------------------------------------

@login_required
def ticket_management_view(request):
    return render(request, 'ticketManagement.html')


# ---------------------------------------------------------------------------
# POST /tickets, GET /tickets?type=&status=
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(['GET', 'POST'])
def tickets_view(request):
    if request.method == 'POST':
        return _create_ticket(request)
    return _list_tickets(request)


def _create_ticket(request):
    body, err = _parse_json_body(request)
    if err:
        return err

    raw_type = body.get('type')
    ticket_type = TICKET_TYPE_ALIASES.get(raw_type)
    if ticket_type is None:
        return _error("'type' must be one of: application, invitation, resignation")

    message_text = body.get('message_text')

    if ticket_type == Ticket.TicketType.COLLAB_REQUEST:
        ticket, err = _create_application(request.user, body, message_text)
    elif ticket_type == Ticket.TicketType.INVITATION:
        ticket, err = _create_invitation(request.user, body, message_text)
    else:  # RESIGNATION
        ticket, err = _create_resignation(request.user, body, message_text)

    if err:
        return err
    return JsonResponse(serialize_ticket(ticket, request.user), status=201)


def _create_application(sender, body, message_text):
    project_id = body.get('project_id')
    project_role_id = body.get('project_role_id')
    if not project_id or not project_role_id:
        return None, _error("'project_id' and 'project_role_id' are required")

    project = Project.objects.filter(id=project_id).first()
    if project is None:
        return None, _error('Project not found', status=404)

    role = ProjectRole.objects.filter(id=project_role_id, project=project).first()
    if role is None:
        return None, _error('Project role not found for this project', status=404)

    if project.state != Project.State.RECRUITING:
        return None, _error('This project is not currently recruiting')

    if ProjectMember.objects.filter(
        project=project, user=sender, member_status=ProjectMember.MemberStatus.ACTIVE
    ).exists():
        return None, _error('You are already an active member of this project')

    if Ticket.objects.filter(
        sender=sender, project=project, project_role=role,
        ticket_type=Ticket.TicketType.COLLAB_REQUEST,
        status=Ticket.Status.PENDING_FEEDBACK,
    ).exists():
        return None, _error('You already have a pending application for this role')

    ticket = Ticket.objects.create(
        sender=sender,
        receiver=project.pm,
        project=project,
        project_role=role,
        ticket_type=Ticket.TicketType.COLLAB_REQUEST,
        message_text=message_text,
    )
    return ticket, None


def _create_invitation(sender, body, message_text):
    project_id = body.get('project_id')
    project_role_id = body.get('project_role_id')
    receiver_id = body.get('receiver_id')
    if not project_id or not project_role_id or not receiver_id:
        return None, _error("'project_id', 'project_role_id' and 'receiver_id' are required")

    project = Project.objects.filter(id=project_id).first()
    if project is None:
        return None, _error('Project not found', status=404)

    if project.pm_id != sender.id:
        return None, _error('Only the project manager can send invitations', status=403)

    role = ProjectRole.objects.filter(id=project_role_id, project=project).first()
    if role is None:
        return None, _error('Project role not found for this project', status=404)

    receiver = User.objects.filter(id=receiver_id).first()
    if receiver is None:
        return None, _error('Invited user not found', status=404)

    if ProjectMember.objects.filter(
        project=project, user=receiver, member_status=ProjectMember.MemberStatus.ACTIVE
    ).exists():
        return None, _error('That user is already an active member of this project')

    if Ticket.objects.filter(
        receiver=receiver, project=project, project_role=role,
        ticket_type=Ticket.TicketType.INVITATION,
        status=Ticket.Status.PENDING_FEEDBACK,
    ).exists():
        return None, _error('An invitation for this role is already pending for that user')

    ticket = Ticket.objects.create(
        sender=sender,
        receiver=receiver,
        project=project,
        project_role=role,
        ticket_type=Ticket.TicketType.INVITATION,
        message_text=message_text,
    )
    return ticket, None


def _create_resignation(sender, body, message_text):
    project_id = body.get('project_id')
    project_role_id = body.get('project_role_id')  # optional
    if not project_id:
        return None, _error("'project_id' is required")

    project = Project.objects.filter(id=project_id).first()
    if project is None:
        return None, _error('Project not found', status=404)

    active_memberships = ProjectMember.objects.filter(
        project=project, user=sender, member_status=ProjectMember.MemberStatus.ACTIVE
    )

    if project_role_id:
        membership = active_memberships.filter(project_role_id=project_role_id).first()
        if membership is None:
            return None, _error('You do not have an active membership in that role')
    else:
        count = active_memberships.count()
        if count == 0:
            return None, _error('You are not an active member of this project')
        if count > 1:
            return None, _error(
                'You hold multiple active roles on this project — specify project_role_id'
            )
        membership = active_memberships.first()

    role = membership.project_role

    if Ticket.objects.filter(
        sender=sender, project=project, project_role=role,
        ticket_type=Ticket.TicketType.RESIGNATION,
        status=Ticket.Status.PENDING_FEEDBACK,
    ).exists():
        return None, _error('You already have a pending resignation for this role')

    ticket = Ticket.objects.create(
        sender=sender,
        receiver=project.pm,
        project=project,
        project_role=role,
        ticket_type=Ticket.TicketType.RESIGNATION,
        message_text=message_text,
    )
    return ticket, None


def _list_tickets(request):
    tickets = Ticket.objects.filter(
        _sender_or_receiver(request.user)
    ).select_related('project', 'project_role', 'sender', 'receiver')

    type_param = request.GET.get('type')
    if type_param:
        ticket_type = TICKET_TYPE_ALIASES.get(type_param)
        if ticket_type is None:
            return _error("'type' must be one of: application, invitation, resignation")
        tickets = tickets.filter(ticket_type=ticket_type)

    status_param = request.GET.get('status')
    if status_param == 'pending_their_response':
        # I sent it — waiting on the other party to act.
        tickets = tickets.filter(sender=request.user, status=Ticket.Status.PENDING_FEEDBACK)
    elif status_param == 'pending_our_response':
        # It's addressed to me — I need to act.
        tickets = tickets.filter(receiver=request.user, status=Ticket.Status.PENDING_FEEDBACK)
    elif status_param == 'closed':
        tickets = tickets.filter(status__in=CLOSED_STATUSES)
    elif status_param:
        return _error("'status' must be one of: pending_their_response, pending_our_response, closed")

    tickets = tickets.order_by('-created_at')
    return JsonResponse(
        {'tickets': [serialize_ticket(t, request.user) for t in tickets]}
    )


def _sender_or_receiver(user):
    return Q(sender=user) | Q(receiver=user)


# ---------------------------------------------------------------------------
# GET /tickets/:id, DELETE /tickets/:id
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(['GET', 'DELETE'])
def ticket_detail_view(request, ticket_id):
    ticket = get_object_or_404(
        Ticket.objects.select_related('project', 'project_role', 'sender', 'receiver'),
        id=ticket_id,
    )

    if request.user.id not in (ticket.sender_id, ticket.receiver_id):
        return _error('Not found', status=404)  # don't leak existence to uninvolved users

    if request.method == 'GET':
        return JsonResponse(serialize_ticket(ticket, request.user))

    # DELETE — cancel before response
    if ticket.sender_id != request.user.id:
        return _error('Only the sender can cancel a ticket', status=403)
    if ticket.status != Ticket.Status.PENDING_FEEDBACK:
        return _error('Only pending tickets can be cancelled')

    ticket.status = Ticket.Status.CANCELLED
    ticket.save(update_fields=['status', 'updated_at'])
    return JsonResponse(serialize_ticket(ticket, request.user))


# ---------------------------------------------------------------------------
# PATCH /tickets/:id/respond
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(['PATCH'])
def ticket_respond_view(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if ticket.receiver_id != request.user.id:
        return _error('Not found', status=404)

    if ticket.status != Ticket.Status.PENDING_FEEDBACK:
        return _error('This ticket has already been resolved')

    body, err = _parse_json_body(request)
    if err:
        return err

    action = body.get('action')
    if action not in ('approve', 'reject'):
        return _error("'action' must be 'approve' or 'reject'")

    with transaction.atomic():
        if action == 'reject':
            ticket.status = Ticket.Status.CLOSED_REJECTED
        else:
            side_effect_err = _apply_approval_side_effects(ticket)
            if side_effect_err:
                return side_effect_err
            ticket.status = Ticket.Status.CLOSED_ACCEPTED

        ticket.save(update_fields=['status', 'updated_at'])

    return JsonResponse(
        serialize_ticket(ticket, request.user)
    )


def _apply_approval_side_effects(ticket):
    if ticket.ticket_type in (Ticket.TicketType.COLLAB_REQUEST, Ticket.TicketType.INVITATION):
        role = ticket.project_role
        if role is None:
            return _error('Ticket is missing a project role, cannot approve')

        active_count = ProjectMember.objects.filter(
            project_role=role, member_status=ProjectMember.MemberStatus.ACTIVE
        ).count()
        if active_count >= role.capacity:
            return _error('This role has no remaining capacity')

        # COLLAB_REQUEST: sender applied to join. INVITATION: receiver (us,
        # the PM) invited them — but here 'us' IS the receiver responding,
        # so the new member is the ticket's sender either way? No —
        # for an invitation, the applicant is the RECEIVER of the ticket
        # (the PM sent it, the invited user is responding), so the new
        # member is whoever is NOT the project's PM on this ticket.
        new_member_user = (
            ticket.sender if ticket.ticket_type == Ticket.TicketType.COLLAB_REQUEST
            else ticket.receiver
        )

        ProjectMember.objects.update_or_create(
            project=ticket.project,
            user=new_member_user,
            defaults={
                'project_role': role,
                'member_status': ProjectMember.MemberStatus.ACTIVE,
            },
        )

    elif ticket.ticket_type == Ticket.TicketType.RESIGNATION:
        membership = ProjectMember.objects.filter(
            project=ticket.project,
            user=ticket.sender,
            project_role=ticket.project_role,
            member_status=ProjectMember.MemberStatus.ACTIVE,
        ).first()
        if membership is None:
            return _error('Active membership for this resignation was not found')

        membership.member_status = ProjectMember.MemberStatus.RESIGNED
        membership.save(update_fields=['member_status'])

    return None


# ---------------------------------------------------------------------------
# GET /tickets/history
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(['GET'])
def ticket_history_view(request):
    tickets = Ticket.objects.filter(
        _sender_or_receiver(request.user)
    ).select_related('project', 'project_role', 'sender', 'receiver').order_by('-created_at')

    return JsonResponse(
        {'tickets': [serialize_ticket(t, request.user) for t in tickets]}
    )
