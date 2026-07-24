# unitus/recommendation/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from projects.models import JobAd
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
        recommendations = service.recommend_candidates_for_ad(job_ad, top_k=10)

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