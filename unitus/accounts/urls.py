from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("users/me", views.me_view, name="me"),
    path("users/me/open-to-work", views.open_to_work_view, name="open-to-work"),
    path("users/me/avatar-options", views.avatar_options_view, name="avatar-options"),
    path("users/me/avatar", views.avatar_select_view, name="avatar-select"),
    path("users/me/skills", views.my_skills_view, name="my-skills"),
    path("users/me/skills/<int:skill_id>", views.my_skill_detail_view, name="my-skill-detail"),
    path("users/me/work-preferences", views.work_preferences_view, name="work-preferences"),
    path("users/me/dashboard/projects", views.dashboard_projects_view, name="dashboard-projects"),
    path("users/<int:id>", views.public_profile_view, name="public-profile"),
    path("users/<int:id>/active-projects-count", views.active_projects_count_view, name="active-projects-count"),
    path("users/<int:id>/report", views.report_user_view, name="report-user"),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_page_view, name='profile-page'),
    path('profile/edit/', views.profile_edit_view, name='profile-edit'),
    path('profile/<int:id>/', views.profile_page_view, name='profile-page-detail'),
]
