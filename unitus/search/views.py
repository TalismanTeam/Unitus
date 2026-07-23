from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from accounts.models import User
from accounts.services import get_public_user_fields
from projects.models import JobAd
from skills.choices import MasteryLevel
from skills.models import Skill

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
    return paginator.get_page(page_number)


# ---------------------------------------------------------
# GET /search/ads/
# ---------------------------------------------------------

def search_ads_view(request):
    q = request.GET.get('q', '').strip()
    skill_id = _parse_int(request.GET.get('skill'))
    min_level = request.GET.get('min_level', '').strip()
    duration_min = _parse_int(request.GET.get('duration_min'))
    duration_max = _parse_int(request.GET.get('duration_max'))

    
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

    if duration_min is not None:
        ads = ads.filter(project__duration_days__gte=duration_min)
    if duration_max is not None:
        ads = ads.filter(project__duration_days__lte=duration_max)

    ads = ads.distinct().order_by('-created_at')

    page_obj = _paginate(request, ads)

    context = {
        'page_obj': page_obj,
        'query': q,
        'skills': Skill.objects.all().order_by('name'),
        'mastery_levels': MasteryLevel.choices,
        'selected_skill': skill_id,
        'selected_min_level': min_level,
        'duration_min': duration_min,
        'duration_max': duration_max,
    }
    return render(request, 'search/search_ads.html', context)


# ---------------------------------------------------------
# GET /search/users/
# ---------------------------------------------------------

@login_required
def search_users_view(request):
    q = request.GET.get('q', '').strip()
    open_to_work_only = request.GET.get('open_to_work') == '1'
    skill_id = _parse_int(request.GET.get('skill'))
    level = request.GET.get('level', '').strip()
    location = request.GET.get('location', '').strip()

    users = User.objects.filter(
        is_active=True,
        account_status='ACTIVE',
    ).select_related('userprivacysettings')

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

    if location:
        users = users.filter(location__icontains=location)

    users = users.distinct().order_by('username')

    page_obj = _paginate(request, users)

   
    results = [get_public_user_fields(u) for u in page_obj.object_list]

    context = {
        'page_obj': page_obj,
        'results': results,
        'query': q,
        'skills': Skill.objects.all().order_by('name'),
        'mastery_levels': MasteryLevel.choices,
        'selected_skill': skill_id,
        'selected_level': level,
        'open_to_work_only': open_to_work_only,
        'location': location,
    }
    return render(request, 'search/search_users.html', context)