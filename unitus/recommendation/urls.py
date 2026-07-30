# unitus/recommendation/urls.py

from django.urls import path
from recommendation.views import (
    RecommendedAdsView,
    RecommendedCandidatesView,
    RecommendationFeedbackView,
    RecommendationPreferencesView,
    recommended_projects_page,
    find_candidates_page,
)

app_name = 'recommendation'

urlpatterns = [
    path('ads/', RecommendedAdsView.as_view(), name='recommend-ads'),
    path('candidates/<int:ad_id>/', RecommendedCandidatesView.as_view(), name='recommend-candidates'),
    path('preferences/', RecommendationPreferencesView.as_view(), name='recommend-preferences'),
    path('<int:id>/feedback/', RecommendationFeedbackView.as_view(), name='recommend-feedback'),

    # Page views (server-rendered; JS on the page calls the JSON endpoints above)
    path('projects-page/', recommended_projects_page, name='recommend-projects-page'),
    path('find-candidates-page/', find_candidates_page, name='find-candidates-page'),
]
