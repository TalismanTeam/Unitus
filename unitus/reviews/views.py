import json
from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from accounts.models import User
from projects.models import Project, ProjectMember

from .models import Review, Tag, ReviewTag, UserHonor
from .serialization import serialize_review, serialize_tag, serialize_badge

BADGE_THRESHOLD = 5


def _parse_json_body(request):
    try:
        return json.loads(request.body or '{}'), None
    except json.JSONDecodeError:
        return None, JsonResponse({'error': 'Invalid JSON body'}, status=400)


def _error(message, status=400):
    return JsonResponse({'error': message}, status=status)


# ---------------------------------------------------------------------------
# POST /reviews
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(['POST'])
def create_review_view(request):
    body, err = _parse_json_body(request)
    if err:
        return err

    project_id = body.get('project_id')
    reviewee_id = body.get('reviewee_id')
    rating = body.get('rating')
    tag_ids = body.get('tag_ids', [])

    if not project_id or not reviewee_id or rating is None:
        return _error("'project_id', 'reviewee_id' and 'rating' are required")

    if not isinstance(tag_ids, list):
        return _error("'tag_ids' must be a list")

    try:
        rating = int(rating)
    except (TypeError, ValueError):
        return _error("'rating' must be an integer")
    if not (1 <= rating <= 5):
        return _error("'rating' must be between 1 and 5")

    if int(reviewee_id) == request.user.id:
        return _error('You cannot review yourself')

    project = Project.objects.filter(id=project_id).first()
    if project is None:
        return _error('Project not found', status=404)

    if project.state != Project.State.TERMINATED or project.termination_reason != Project.TerminationReason.SUCCESS:
        return _error('Reviews can only be submitted for successfully completed projects')

    reviewee = User.objects.filter(id=reviewee_id).first()
    if reviewee is None:
        return _error('Reviewee not found', status=404)

    if not ProjectMember.objects.filter(project=project, user=request.user).exists():
        return _error('You were not part of this project', status=403)

    if not ProjectMember.objects.filter(project=project, user=reviewee).exists():
        return _error('That user was not part of this project')

    if Review.objects.filter(reviewer=request.user, reviewee=reviewee, project=project).exists():
        return _error('You have already reviewed this teammate for this project')

    unique_tag_ids = set(tag_ids)
    tags = list(Tag.objects.filter(id__in=unique_tag_ids))
    if len(tags) != len(unique_tag_ids):
        return _error('One or more tag_ids are invalid')

    with transaction.atomic():
        review = Review.objects.create(
            reviewer=request.user, reviewee=reviewee, project=project, rating=rating
        )
        ReviewTag.objects.bulk_create([ReviewTag(review=review, tag=tag) for tag in tags])

        for tag in tags:
            if tag.tag_type == Tag.TagType.POSITIVE:
                _maybe_award_badge(reviewee, tag)

    return JsonResponse(serialize_review(review, tags), status=201)


def _maybe_award_badge(user, tag):
    positive_count = ReviewTag.objects.filter(tag=tag, review__reviewee=user).count()
    if positive_count >= BADGE_THRESHOLD:
        UserHonor.objects.get_or_create(user=user, tag=tag)


# ---------------------------------------------------------------------------
# GET /reviews/tags
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(['GET'])
def tags_view(request):
    tags = Tag.objects.all().order_by('tag_type', 'name')
    return JsonResponse({'tags': [serialize_tag(t) for t in tags]})


# ---------------------------------------------------------------------------
# GET /users/:id/reviews
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(['GET'])
def user_reviews_view(request, user_id):
    user = get_object_or_404(User, id=user_id)

    reviews = list(
        Review.objects.filter(reviewee=user)
        .select_related('reviewer', 'reviewee', 'project')
        .order_by('-created_at')
    )

    tags_by_review = defaultdict(list)
    review_tags = ReviewTag.objects.filter(review__in=reviews).select_related('tag')
    for rt in review_tags:
        tags_by_review[rt.review_id].append(rt.tag)

    return JsonResponse({
        'reviews': [serialize_review(r, tags_by_review.get(r.id, [])) for r in reviews]
    })


# ---------------------------------------------------------------------------
# GET /users/:id/badges
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(['GET'])
def user_badges_view(request, user_id):
    user = get_object_or_404(User, id=user_id)
    honors = UserHonor.objects.filter(user=user).select_related('tag').order_by('-earned_at')
    return JsonResponse({'badges': [serialize_badge(h) for h in honors]})
