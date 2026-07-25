# unitus/recommendation/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from projects.models import JobAd
from accounts.models import User
from skills.models import SkillCategory
from recommendation.models import RecommendationFeedback, RecommendationPreference
from recommendation.serialization import serialize_feedback, serialize_preferences
from recommendation.services import MatchScoreService


class RecommendedAdsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        service = MatchScoreService()
        recommendations = service.recommend_ads_for_user(request.user, top_k=10)

        data = [
            {
                "ad_id": rec["ad"].id,
                "project_title": rec["ad"].project.title,
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
        recommendations = service.recommend_candidates_for_ad(job_ad, request.user, top_k=10)

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
