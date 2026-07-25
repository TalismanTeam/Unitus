import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from accounts.models import User
from .models import Report
from .serialization import serialize_report


def _parse_json_body(request):
    if not request.body:
        return {}, None
    try:
        return json.loads(request.body), None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, _error('Invalid JSON body.', 400)


def _error(message, status):
    return JsonResponse({'error': message}, status=status)


def _require_admin(request):
    if request.user.system_role != User.SystemRole.ADMIN:
        return _error('Admin access required.', 403)
    return None


@login_required
@require_http_methods(['POST'])
def create_report(request):
    """
    POST /moderation/reports
    Body: {"reported_user_id": <int>, "reason": "INACTIVITY"|"INSULTING"|
           "FAKE_PROJECT"|"OTHER", "description": <str, optional>}

    Any logged-in user can report any other user. Goes straight to admins
    (not the Ticket module) — see SRS "Distinct from Ticket module."
    """
    body, error = _parse_json_body(request)
    if error:
        return error

    raw_reported_user_id = body.get('reported_user_id')
    reason = body.get('reason')
    description = body.get('description')

    if raw_reported_user_id is None:
        return _error('reported_user_id is required.', 400)
    try:
        reported_user_id = int(raw_reported_user_id)
    except (TypeError, ValueError):
        return _error('reported_user_id must be an integer.', 400)

    if reason not in Report.Reason.values:
        return _error(
            'reason must be one of: %s' % ', '.join(Report.Reason.values), 400
        )

    if reported_user_id == request.user.id:
        return _error('You cannot report yourself.', 400)

    try:
        reported_user = User.objects.get(pk=reported_user_id)
    except User.DoesNotExist:
        return _error('reported_user not found.', 404)

    report = Report.objects.create(
        reporter=request.user,
        reported_user=reported_user,
        reason=reason,
        description=description or None,
    )
    return JsonResponse(serialize_report(report), status=201)


@login_required
@require_http_methods(['GET'])
def list_reports(request):
    """
    GET /moderation/admin/reports?status=<optional>
    Admin only.
    """
    error = _require_admin(request)
    if error:
        return error

    reports = (
        Report.objects
        .select_related('reporter', 'reported_user', 'reviewed_by_admin')
        .order_by('-created_at')
    )

    status = request.GET.get('status')
    if status:
        if status not in Report.Status.values:
            return _error(
                'status must be one of: %s' % ', '.join(Report.Status.values), 400
            )
        reports = reports.filter(status=status)

    data = [serialize_report(r, for_admin=True) for r in reports]
    return JsonResponse({'reports': data})


@login_required
@require_http_methods(['PATCH'])
def resolve_report(request, report_id):
    """
    PATCH /moderation/admin/reports/:id
    Body: {"action": "resolve"|"dismiss"}
    Admin only. Only valid while status is still PENDING_REVIEW.
    """
    error = _require_admin(request)
    if error:
        return error

    try:
        report = (
            Report.objects
            .select_related('reporter', 'reported_user', 'reviewed_by_admin')
            .get(pk=report_id)
        )
    except Report.DoesNotExist:
        return _error('Report not found.', 404)

    body, error = _parse_json_body(request)
    if error:
        return error

    action = body.get('action')
    if action not in ('resolve', 'dismiss'):
        return _error('action must be "resolve" or "dismiss".', 400)

    if report.status != Report.Status.PENDING_REVIEW:
        return _error('This report has already been reviewed.', 400)

    report.status = Report.Status.RESOLVED if action == 'resolve' else Report.Status.DISMISSED
    report.reviewed_by_admin = request.user
    report.save(update_fields=['status', 'reviewed_by_admin'])

    return JsonResponse(serialize_report(report, for_admin=True))
