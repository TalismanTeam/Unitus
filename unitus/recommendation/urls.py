# unitus/recommendation/urls.py

from django.urls import path
from recommendation.views import RecommendedAdsView, RecommendedCandidatesView

urlpatterns = [
    path('ads/', RecommendedAdsView.as_view(), name='recommend-ads'),
    path('candidates/<int:ad_id>/', RecommendedCandidatesView.as_view(), name='recommend-candidates'),
]