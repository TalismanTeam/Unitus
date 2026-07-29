from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [
    path('', views.search_page_view, name='search_page'),
    path('ads/', views.search_ads_view, name='search_ads'),
    path('users/', views.search_users_view, name='search_users'),
    path('filters/', views.search_filters_view, name='search_filters'),
]