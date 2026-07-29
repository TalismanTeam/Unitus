from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse

from accounts.models import User
from accounts.services import get_public_user_fields
from projects.models import JobAd
from skills.choices import MasteryLevel
from skills.models import Skill, SkillCategory, UserSkill

from .serialization import serialize_job_ad, serialize_user_result

from django.shortcuts import render

RESULTS_PER_PAGE = 12


def _parse_int(value, default=None):
    if value is None or value == '':
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _paginate(request, queryset):
    page_number = _parse_int(request.GET.get('page'), default=1)
    paginator = Paginator(queryset, RESULTS_PER_PAGE)
    page_obj = paginator.get_page(page_number)
    pagination = {
        'page': page_obj.number,
        'num_pages': paginator.num_pages,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'total_count': paginator.count,
    }
    return page_obj, pagination


# ---------------------------------------------------------
# GET /search/filters/  — skill catalog for building the filter UI
# ---------------------------------------------------------

def search_filters_view(request):
    categories = []
    for category in SkillCategory.objects.all().order_by('category_name'):
        skills = list(
            Skill.objects.filter(category=category, is_approved=True)
            .order_by('name')
            .values('id', 'name')
        )
        if skills:
            categories.append({
                'id': category.id,
                'name': category.category_name,
                'skills': skills,
            })

    return JsonResponse({
        'categories': categories,
        'mastery_levels': [{'value': v, 'label': l} for v, l in MasteryLevel.choices],
    })


# ---------------------------------------------------------
# GET /search/ads/
# ---------------------------------------------------------

def search_ads_view(request):
    q = request.GET.get('q', '').strip()
    skill_id = _parse_int(request.GET.get('skill'))
    category_id = _parse_int(request.GET.get('category'))
    min_level = request.GET.get('min_level', '').strip()
    duration_min = _parse_int(request.GET.get('duration_min'))
    duration_max = _parse_int(request.GET.get('duration_max'))
    sort = request.GET.get('sort', 'newest')

    ads = JobAd.objects.filter(
        status='OPEN',
        project__state='RECRUITING',
    ).select_related('project', 'project_role')

    if q:
        ads = ads.filter(
            Q(project__title__icontains=q) |
            Q(project__short_description__icontains=q) |
            Q(project_role__role_title__icontains=q)
        )

    if skill_id:
        ads = ads.filter(project_role__projectroleskill__skill_id=skill_id)
        if min_level in MasteryLevel.values:
            ads = ads.filter(project_role__projectroleskill__min_required_level=min_level)
    elif category_id:
        ads = ads.filter(project_role__projectroleskill__skill__category_id=category_id)

    if duration_min is not None:
        ads = ads.filter(project__duration_days__gte=duration_min)
    if duration_max is not None:
        ads = ads.filter(project__duration_days__lte=duration_max)

    ads = ads.distinct()
    ads = ads.order_by('created_at' if sort == 'oldest' else '-created_at')

    page_obj, pagination = _paginate(request, ads)

    return JsonResponse({
        'results': [serialize_job_ad(ad) for ad in page_obj.object_list],
        'pagination': pagination,
    })


# ---------------------------------------------------------
# GET /search/users/
# ---------------------------------------------------------

def search_users_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication required.'}, status=401)

    q = request.GET.get('q', '').strip()
    open_to_work_only = request.GET.get('open_to_work') == '1'
    skill_id = _parse_int(request.GET.get('skill'))
    category_id = _parse_int(request.GET.get('category'))
    level = request.GET.get('level', '').strip()
    location = request.GET.get('location', '').strip()
    sort = request.GET.get('sort', 'name_asc')

    users = User.objects.filter(
        is_active=True,
        account_status='ACTIVE',
    ).select_related('userprivacysettings', 'avatar_icon')

    if q:
        users = users.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q)
        )

    if open_to_work_only:
        users = users.filter(is_open_to_work=True)

    if skill_id:
        users = users.filter(userskill__skill_id=skill_id)
        if level in MasteryLevel.values:
            users = users.filter(userskill__mastery_level=level)
    elif category_id:
        users = users.filter(userskill__skill__category_id=category_id)

    if location:
        users = users.filter(location__icontains=location)

    users = users.distinct()
    users = users.order_by('-username' if sort == 'name_desc' else 'username')

    page_obj, pagination = _paginate(request, users)

    results = []
    for user in page_obj.object_list:
        public_fields = get_public_user_fields(user)
        skills_qs = UserSkill.objects.filter(user=user).select_related('skill')
        results.append(serialize_user_result(user, public_fields, skills_qs))

    return JsonResponse({
        'results': results,
        'pagination': pagination,
    })


# ---------------------------------------------------------
# GET /search/ — Render Search Page
# ---------------------------------------------------------
def search_page_view(request):
    return render(request, 'search.html')