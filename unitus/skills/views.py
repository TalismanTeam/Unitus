import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from .models import Skill, SkillCategory, UserSkill
from .serialization import serialize_skill, serialize_skill_category


def bad_request(detail):
    return JsonResponse({"detail": detail}, status=400)


def forbidden(detail):
    return JsonResponse({"detail": detail}, status=403)


def parse_json(request):
    """Returns a dict, or None if the body isn't valid JSON."""
    if not request.body:
        return {}
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


# ---------------------------------------------------------------------------
# GET /skills/categories/ - full category list, for populating a picker
# ---------------------------------------------------------------------------

@require_http_methods(["GET"])
def categories_view(request):
    categories = SkillCategory.objects.order_by("category_name")
    return JsonResponse([serialize_skill_category(c) for c in categories], safe=False)


# ---------------------------------------------------------------------------
# GET /skills/?category=<id>&q=<search>&include_pending=1 - browsable catalog
# ---------------------------------------------------------------------------

@require_http_methods(["GET"])
def skills_list_view(request):
    skills = Skill.objects.select_related("category").order_by("category__category_name", "name")

    # Unapproved custom suggestions are hidden from the public catalog by
    # default. Staff can pass ?include_pending=1 to review them.
    include_pending = request.GET.get("include_pending") == "1"
    if not (include_pending and request.user.is_authenticated and request.user.is_staff):
        skills = skills.filter(is_approved=True)

    category_id = request.GET.get("category")
    if category_id:
        skills = skills.filter(category_id=category_id)

    query = request.GET.get("q", "").strip()
    if query:
        skills = skills.filter(name__icontains=query)

    return JsonResponse([serialize_skill(s) for s in skills], safe=False)


# ---------------------------------------------------------------------------
# GET /skills/<id>/stats/ - usage stats for a skill
# ---------------------------------------------------------------------------

@require_http_methods(["GET"])
def skill_stats_view(request, skill_id):
    from projects.models import ProjectRoleSkill

    skill = get_object_or_404(Skill, pk=skill_id)
    return JsonResponse({
        "skill": skill.id,
        "skill_name": skill.name,
        "user_count": UserSkill.objects.filter(skill=skill).count(),
        "project_role_count": ProjectRoleSkill.objects.filter(skill=skill).count(),
    })


# ---------------------------------------------------------------------------
# POST /skills/custom/ - suggest a skill that isn't in the seeded catalog yet
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(["POST"])
def create_custom_skill_view(request):
    data = parse_json(request)
    if data is None:
        return bad_request("invalid JSON body")

    category_id = data.get("category")
    name = (data.get("name") or "").strip()

    if not category_id or not name:
        return bad_request("category (id) and name are required")

    category = get_object_or_404(SkillCategory, pk=category_id)

    if Skill.objects.filter(category=category, name__iexact=name).exists():
        return bad_request("This skill already exists in that category - use it instead of suggesting a duplicate.")

    skill = Skill.objects.create(
        category=category, name=name, is_custom=True, created_by=request.user, is_approved=False,
    )
    return JsonResponse(serialize_skill(skill), status=201)


# ---------------------------------------------------------------------------
# DELETE /skills/custom/<id>/ - withdraw your own pending suggestion
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(["DELETE"])
def delete_custom_skill_view(request, skill_id):
    skill = get_object_or_404(Skill, pk=skill_id)

    if not skill.is_custom:
        return bad_request("Only custom-suggested skills can be deleted this way.")

    is_owner = skill.created_by_id == request.user.id
    if not (is_owner or request.user.is_staff):
        return forbidden("You can only delete your own pending suggestions.")

    if skill.is_approved and not request.user.is_staff:
        return bad_request("This suggestion was already approved and is now in the shared catalog - contact an admin to remove it.")

    if UserSkill.objects.filter(skill=skill).exists():
        return bad_request("This skill is already in use by at least one user and can't be deleted.")

    skill.delete()
    return JsonResponse({"deleted": True, "id": skill_id})
