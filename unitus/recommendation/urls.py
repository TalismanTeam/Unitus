# unitus/recommendation/urls.py

from django.urls import path
from recommendation.views import (
    RecommendedAdsView,
    RecommendedCandidatesView,
    RecommendationFeedbackView,
    RecommendationPreferencesView,
)

app_name = 'recommendation'

urlpatterns = [
    path('ads/', RecommendedAdsView.as_view(), name='recommend-ads'),
    path('candidates/<int:ad_id>/', RecommendedCandidatesView.as_view(), name='recommend-candidates'),
    path('preferences/', RecommendationPreferencesView.as_view(), name='recommend-preferences'),
    path('<int:id>/feedback/', RecommendationFeedbackView.as_view(), name='recommend-feedback'),
]
