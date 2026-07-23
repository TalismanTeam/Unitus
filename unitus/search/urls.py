from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [
    path('ads/', views.search_ads_view, name='search_ads'),
    path('users/', views.search_users_view, name='search_users'),
]