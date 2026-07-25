from django.urls import path

from . import views

app_name = 'reviews'

urlpatterns = [
    path('reviews', views.create_review_view, name='review-create'),
    path('reviews/tags', views.tags_view, name='review-tags'),
    path('users/<int:user_id>/reviews', views.user_reviews_view, name='user-reviews'),
    path('users/<int:user_id>/badges', views.user_badges_view, name='user-badges'),
]
