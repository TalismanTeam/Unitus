# unitus/recommendation/views.py

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from projects.models import JobAd, Project
from accounts.models import User
from skills.models import SkillCategory
from recommendation.models import RecommendationFeedback, RecommendationPreference
from recommendation.serialization import serialize_feedback, serialize_preferences
from recommendation.services import MatchScoreService


class RecommendedAdsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        service = MatchScoreService()
        recommendations = service.recommend_ads_for_user(request.user, top_k=3)

        data = [
            {
                "ad_id": rec["ad"].id,
                "project_id": rec["ad"].project.id,
                "project_role_id": rec["ad"].project_role.id,
                "project_title": rec["ad"].project.title,
                "project_description": rec["ad"].project.short_description,
                "role_title": rec["ad"].project_role.role_title,
                "match_score": rec["score"]
            }
            for rec in recommendations
        ]
        return Response(data, status=status.HTTP_200_OK)


class RecommendedCandidatesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, ad_id):
        try:
            job_ad = JobAd.objects.get(id=ad_id)
        except JobAd.DoesNotExist:
            return Response({"detail": "Job Ad not found."}, status=status.HTTP_404_NOT_FOUND)

        # Checking if requester is PM of the project
        if job_ad.project.pm != request.user:
            return Response({"detail": "Only PM can view candidates for this ad."}, status=status.HTTP_403_FORBIDDEN)

        service = MatchScoreService()
        recommendations = service.recommend_candidates_for_ad(job_ad, request.user, top_k=3)

        data = [
            {
                "user_id": rec["user"].id,
                "username": rec["user"].username,
                "full_name": f"{rec['user'].first_name} {rec['user'].last_name}",
                "match_score": rec["score"]
            }
            for rec in recommendations
        ]
        return Response(data, status=status.HTTP_200_OK)


class RecommendationFeedbackView(APIView):
    """
    POST /recommendations/<id>/feedback/
    body: {"recommendation_type": "AD" | "CANDIDATE", "vote": "UP" | "DOWN"}

    <id> is the id of the thing being reacted to: a JobAd id when
    recommendation_type=AD, or a candidate User id when
    recommendation_type=CANDIDATE. Sending feedback again on the same
    suggestion updates the existing vote rather than creating a duplicate.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        recommendation_type = request.data.get("recommendation_type")
        vote = request.data.get("vote")

        if recommendation_type not in RecommendationFeedback.RecommendationType.values:
            return Response(
                {"detail": "recommendation_type must be one of: AD, CANDIDATE."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if vote not in RecommendationFeedback.Vote.values:
            return Response(
                {"detail": "vote must be one of: UP, DOWN."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if recommendation_type == RecommendationFeedback.RecommendationType.AD:
            target_exists = JobAd.objects.filter(id=id).exists()
        else:
            target_exists = User.objects.filter(id=id).exists()

        if not target_exists:
            return Response({"detail": "Target not found."}, status=status.HTTP_404_NOT_FOUND)

        feedback, _ = RecommendationFeedback.objects.update_or_create(
            user=request.user,
            recommendation_type=recommendation_type,
            target_id=id,
            defaults={"vote": vote},
        )
        return Response(serialize_feedback(feedback), status=status.HTTP_200_OK)


class RecommendationPreferencesView(APIView):
    """
    GET/PATCH /recommendations/preferences/
    PATCH body: {"min_match_score": 0.0-1.0, "excluded_category_ids": [1, 2]}
    Either field is optional on PATCH; only the fields present are updated.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        preferences, _ = RecommendationPreference.objects.get_or_create(user=request.user)
        return Response(serialize_preferences(preferences), status=status.HTTP_200_OK)

    def patch(self, request):
        preferences, _ = RecommendationPreference.objects.get_or_create(user=request.user)
        data = request.data

        if "min_match_score" in data:
            try:
                min_match_score = float(data["min_match_score"])
            except (TypeError, ValueError):
                return Response(
                    {"detail": "min_match_score must be a number between 0 and 1."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not 0.0 <= min_match_score <= 1.0:
                return Response(
                    {"detail": "min_match_score must be between 0 and 1."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            preferences.min_match_score = min_match_score

        if "excluded_category_ids" in data:
            category_ids = data["excluded_category_ids"]
            if not isinstance(category_ids, list):
                return Response(
                    {"detail": "excluded_category_ids must be a list of category ids."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            categories = SkillCategory.objects.filter(id__in=category_ids)
            preferences.excluded_categories.set(categories)

        preferences.save()
        return Response(serialize_preferences(preferences), status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Page views (server-rendered HTML; the JS on each page calls the JSON
# endpoints above via fetch()).
# ---------------------------------------------------------------------------

@login_required
def recommended_projects_page(request):
    """
    GET /recommendations/projects-page/
    "Recommended Projects" entry point from the Projects hub. Renders an
    empty shell — static/js/recommendation.js loads the actual list from
    GET /recommendations/ads/.
    """
    return render(request, 'recommendation/recommended_projects.html')


@login_required
def find_candidates_page(request):
    """
    GET /recommendations/find-candidates-page/
    PM tool: "for which project/role (that I manage) do you want me to find
    a matching user". Only lists the requesting user's own projects and only
    roles that still have an open job ad (still recruiting).

    The role->job-ad mapping is handed to the template as JSON (via
    json_script) so the page's JS can populate the role dropdown and know
    which ad_id to call GET /recommendations/candidates/<ad_id>/ with,
    without extra round-trips.
    """
    projects = Project.objects.filter(pm=request.user).order_by('-created_at').prefetch_related(
        'projectrole_set'
    )

    pm_projects_data = []
    for project in projects:
        roles_data = []
        for role in project.projectrole_set.all():
            job_ad = getattr(role, 'jobad', None)
            if job_ad is not None and job_ad.status == JobAd.Status.OPEN:
                roles_data.append({
                    'role_id': role.id,
                    'role_title': role.role_title,
                    'ad_id': job_ad.id,
                })
        if roles_data:
            pm_projects_data.append({
                'project_id': project.id,
                'project_title': project.title,
                'roles': roles_data,
            })

    return render(request, 'recommendation/find_candidates.html', {
        'pm_projects_data': pm_projects_data,
    })
