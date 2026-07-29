import json
import re
from datetime import date

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from accounts.models import User, Avatar, UserPrivacySettings
from skills.models import Skill, UserSkill
from skills.choices import MasteryLevel
from moderation.models import Report

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .forms import RegisterForm, LoginForm
from .models import User


from .serialization import (
    serialize_avatar,
    serialize_me,
    serialize_public_profile,
    serialize_privacy_settings,
    serialize_user_skill,
    serialize_project_summary,
    serialize_report,
)

PRIVACY_PATCHABLE_FIELDS = [
    "show_phone", "show_email", "show_location",
    "show_birth_year", "show_education_background", "show_gender",
]

# E.164-ish: optional leading +, 7-15 digits total. Loose on purpose since
# phone_number has no fixed country format in the model.
PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")

MIN_BIRTH_YEAR = 1900

ME_PATCHABLE_FIELDS = [
    "first_name", "last_name", "gender", "birth_year",
    "phone_number", "location", "education_background", "about_me",
]


def parse_json(request):
    """Returns a dict, or None if the body isn't valid JSON."""
    if not request.body:
        return {}
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def bad_request(detail):
    return JsonResponse({"detail": detail}, status=400)


def get_average_rating(user):
    """
    Average of all ratings on Review rows where `user` is the reviewee.
    Computed on the fly (no stored field) via a DB-side AVG aggregate.
    Returns None if the user has no reviews yet.
    """
    from django.db.models import Avg
    from reviews.models import Review

    result = Review.objects.filter(reviewee=user).aggregate(avg=Avg("rating"))
    avg = result["avg"]
    return round(avg, 1) if avg is not None else None


# ---------------------------------------------------------------------------
# GET/PATCH /users/me
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(["GET", "PATCH"])
def me_view(request):
    user = request.user

    if request.method == "GET":
        data = serialize_me(user)
        data["average_rating"] = get_average_rating(user)
        return JsonResponse(data)

    data = parse_json(request)
    if data is None:
        return bad_request("invalid JSON body")

    if "gender" in data and data["gender"] not in User.Gender.values:
        return bad_request(f"gender must be one of {User.Gender.values}")

    if "birth_year" in data:
        try:
            data["birth_year"] = int(data["birth_year"])
        except (TypeError, ValueError):
            return bad_request("birth_year must be an integer")
        current_year = date.today().year
        if not (MIN_BIRTH_YEAR <= data["birth_year"] <= current_year):
            return bad_request(f"birth_year must be between {MIN_BIRTH_YEAR} and {current_year}")

    if "phone_number" in data:
        phone = data["phone_number"]
        if phone not in (None, ""):
            if not PHONE_RE.match(phone):
                return bad_request("phone_number must contain 7-15 digits, optionally starting with '+'")
        else:
            phone = None
        data["phone_number"] = phone

    for field in ME_PATCHABLE_FIELDS:
        if field in data:
            setattr(user, field, data[field])

    try:
        user.save(update_fields=ME_PATCHABLE_FIELDS)
    except IntegrityError:
        return bad_request("That phone number is already in use by another account.")

    return JsonResponse(serialize_me(user))


# ---------------------------------------------------------------------------
# PATCH /users/me/open-to-work
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(["PATCH"])
def open_to_work_view(request):
    data = parse_json(request)
    if data is None or "is_open_to_work" not in data:
        return bad_request("is_open_to_work (boolean) is required")

    value = data["is_open_to_work"]
    if not isinstance(value, bool):
        return bad_request("is_open_to_work must be a boolean")

    request.user.is_open_to_work = value
    request.user.save(update_fields=["is_open_to_work"])
    return JsonResponse({"is_open_to_work": request.user.is_open_to_work})


# ---------------------------------------------------------------------------
# GET /users/me/avatar-options ,  PATCH /users/me/avatar
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(["GET"])
def avatar_options_view(request):
    """Fixed, admin-defined icon set. No file upload in phase 1."""
    avatars = Avatar.objects.all()
    return JsonResponse([serialize_avatar(a) for a in avatars], safe=False)


@login_required
@require_http_methods(["PATCH"])
def avatar_select_view(request):
    data = parse_json(request)
    if data is None or "avatar_icon" not in data:
        return bad_request("avatar_icon (id or null) is required")

    avatar_id = data["avatar_icon"]
    if avatar_id is None:
        request.user.avatar_icon = None
    else:
        avatar = get_object_or_404(Avatar, pk=avatar_id)
        request.user.avatar_icon = avatar

    request.user.save(update_fields=["avatar_icon"])
    return JsonResponse(serialize_avatar(request.user.avatar_icon))


# ---------------------------------------------------------------------------
# GET/POST /users/me/skills ,  PATCH/DELETE /users/me/skills/:skillId
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(["GET", "POST"])
def my_skills_view(request):
    if request.method == "GET":
        skills = request.user.userskill_set.select_related("skill", "skill__category").all()
        return JsonResponse([serialize_user_skill(s) for s in skills], safe=False)

    data = parse_json(request)
    if data is None:
        return bad_request("invalid JSON body")

    skill_id = data.get("skill")
    mastery_level = data.get("mastery_level")

    if not skill_id or not mastery_level:
        return bad_request("skill (id) and mastery_level are required")
    if mastery_level not in MasteryLevel.values:
        return bad_request(f"mastery_level must be one of {MasteryLevel.values}")

    skill = get_object_or_404(Skill, pk=skill_id)

    if UserSkill.objects.filter(user=request.user, skill=skill).exists():
        return bad_request("You already have this skill on your profile.")

    user_skill = UserSkill.objects.create(
        user=request.user, skill=skill, mastery_level=mastery_level
    )
    return JsonResponse(serialize_user_skill(user_skill), status=201)


@login_required
@require_http_methods(["PATCH", "DELETE"])
def my_skill_detail_view(request, skill_id):
    # skill_id here is the UserSkill row's pk, scoped to request.user so
    # nobody can edit or delete someone else's skill entry.
    user_skill = get_object_or_404(UserSkill, pk=skill_id, user=request.user)

    if request.method == "DELETE":
        user_skill.delete()
        return HttpResponse(status=204)

    data = parse_json(request)
    if data is None or "mastery_level" not in data:
        return bad_request("mastery_level is required")
    if data["mastery_level"] not in MasteryLevel.values:
        return bad_request(f"mastery_level must be one of {MasteryLevel.values}")

    user_skill.mastery_level = data["mastery_level"]
    user_skill.save(update_fields=["mastery_level"])
    return JsonResponse(serialize_user_skill(user_skill))


# ---------------------------------------------------------------------------
# PATCH /users/me/work-preferences
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(["PATCH"])
def work_preferences_view(request):
    """
    STUB: no matching table exists yet in any of the shared models.py files.
    The SRS only defines the is_open_to_work boolean (see open_to_work_view).
    Confirm whether this needs its own model before implementing for real.
    """
    return JsonResponse(
        {"detail": "work-preferences is not yet backed by a model — see README."},
        status=501,
    )


# ---------------------------------------------------------------------------
# GET/PATCH /users/me/privacy-settings
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(["GET", "PATCH"])
def privacy_settings_view(request):
    settings_obj, _ = UserPrivacySettings.objects.get_or_create(user=request.user)

    if request.method == "GET":
        return JsonResponse(serialize_privacy_settings(settings_obj))

    data = parse_json(request)
    if data is None:
        return bad_request("invalid JSON body")

    for field in PRIVACY_PATCHABLE_FIELDS:
        if field in data and not isinstance(data[field], bool):
            return bad_request(f"{field} must be a boolean")

    for field in PRIVACY_PATCHABLE_FIELDS:
        if field in data:
            setattr(settings_obj, field, data[field])

    settings_obj.save(update_fields=PRIVACY_PATCHABLE_FIELDS)
    return JsonResponse(serialize_privacy_settings(settings_obj))


# ---------------------------------------------------------------------------
# GET /users/:id — public profile
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(["GET"])
def public_profile_view(request, id):
    user = get_object_or_404(
        User.objects.select_related("avatar_icon", "userprivacysettings"),
        pk=id,
    )
    data = serialize_public_profile(user)
    data["average_rating"] = get_average_rating(user)
    return JsonResponse(data)


# ---------------------------------------------------------------------------
# GET /users/:id/active-projects-count
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(["GET"])
def active_projects_count_view(request, id):
    from projects.models import ProjectMember

    user = get_object_or_404(User, pk=id)
    count = ProjectMember.objects.filter(
        user=user, member_status="ACTIVE"
    ).exclude(project__state="TERMINATED").count()
    return JsonResponse({"active_projects_count": count})


# ---------------------------------------------------------------------------
# GET /users/me/dashboard/projects?tab=in_progress|suspended|completed|managed|all
#
# UNCHANGED: this is the JSON API dashboard.js calls to populate the
# "My Projects" tabs. Only the page that embeds dashboard.js moved
# (dashboard.html -> reached via accounts:my-projects instead of a
# top-level nav link); the endpoint itself, its URL, and its response
# shape are untouched.
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(["GET"])
def dashboard_projects_view(request):
    from projects.models import Project

    STATE_MAP = {
        "in_progress": "IN_PROGRESS",
        "suspended": "SUSPENDED",
        "completed": "TERMINATED",
    }

    tab = request.GET.get("tab", "all")
    user = request.user

    member_rows = user.projectmember_set.filter(
        member_status="ACTIVE"
    ).select_related("project_role")
    member_project_ids = member_rows.values_list("project_id", flat=True)
    role_title_by_project_id = {
        row.project_id: (row.project_role.role_title if row.project_role else None)
        for row in member_rows
    }

    if tab == "managed":
        qs = Project.objects.filter(pm=user).exclude(state="TERMINATED")
    elif tab == "all":
        qs = (Project.objects.filter(pm=user) |
              Project.objects.filter(id__in=member_project_ids)).distinct()
    elif tab in STATE_MAP:
        state = STATE_MAP[tab]
        qs = (Project.objects.filter(pm=user, state=state) |
              Project.objects.filter(id__in=member_project_ids, state=state)).distinct()
    else:
        return bad_request(f"invalid tab '{tab}'")

    return JsonResponse(
        [
            serialize_project_summary(
                p, user, role_title=role_title_by_project_id.get(p.id)
            )
            for p in qs
        ],
        safe=False,
    )


# ---------------------------------------------------------------------------
# POST /users/:id/report
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(["POST"])
def report_user_view(request, id):
    reported_user = get_object_or_404(User, pk=id)
    if reported_user.pk == request.user.pk:
        return bad_request("You can't report yourself.")

    data = parse_json(request)
    if data is None:
        return bad_request("invalid JSON body")

    reason = data.get("reason")
    if reason not in Report.Reason.values:
        return bad_request(f"reason must be one of {Report.Reason.values}")

    report = Report.objects.create(
        reporter=request.user,
        reported_user=reported_user,
        reason=reason,
        description=data.get("description"),
        status=Report.Status.PENDING_REVIEW,
    )
    return JsonResponse(serialize_report(report), status=201)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:profile-page')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registration completed successfully. You can now sign in.")
            return redirect('accounts:login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:profile-page')

    next_url = request.GET.get('next') or request.POST.get('next')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['identifier'].strip()
            password = form.cleaned_data['password']

            
            username_to_check = identifier
            if '@' in identifier:
            
                try:
                    matched_user = User.objects.get(email__iexact=identifier)
                    username_to_check = matched_user.username
                except User.DoesNotExist:
                    username_to_check = identifier 

            user = authenticate(request, username=username_to_check, password=password)

            if user is None:
                messages.error(request, "Invalid username/email or password.")
            elif user.account_status == User.AccountStatus.BANNED:
                messages.error(request, "This account has been blocked.")
            elif user.account_status == User.AccountStatus.SUSPENDED:
                messages.error(request, "This account has been temporarily suspended.")
            else:
                login(request, user)
                # After login, go to the user's own public profile page
                # instead of the old dashboard. `next` (e.g. a login-wall
                # redirect from some other page) still takes priority.
                return redirect(next_url or 'accounts:profile-page')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form, 'next': next_url})


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('accounts:login')


@login_required
def my_projects_view(request):
    """
    Renders the same tabbed project list dashboard.html always had
    (In Progress / Suspended / Completed / Managed / All), populated by
    dashboard.js hitting dashboard_projects_view above. Only reachable
    now via Projects hub -> "My Projects" (no longer a top-level nav link).
    """
    return render(request, 'dashboard.html')


 
@login_required
def profile_page_view(request, id=None):
    """
    /auth/profile/       -> id is None      -> renders your own profile page
    /auth/profile/<id>/   -> id is given     -> renders someone else's profile page
 
    Passes `profile_id` into the template so its inline script can set
    PROFILE_ID and main.js knows whether to hit /auth/users/me or
    /auth/users/<id>.
    """
    return render(request, 'userprofile.html', {'profile_id': id})


@login_required
def profile_edit_view(request):
    """
    /auth/profile/edit/ -> renders the standalone "Edit Profile" page for the
    logged-in user. There's no id param here on purpose: editing someone
    else's profile isn't possible (no PATCH endpoint exists for anyone but
    request.user), so this page only ever edits your own profile.
    """
    return render(request, 'profile_edit.html')
