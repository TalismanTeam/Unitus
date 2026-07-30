from django.urls import path

from . import views
from reviews import views as review_views

app_name = "accounts"

urlpatterns = [
    path("users/me", views.me_view, name="me"),
    path("users/me/open-to-work", views.open_to_work_view, name="open-to-work"),
    path("users/me/avatar-options", views.avatar_options_view, name="avatar-options"),
    path("users/me/avatar", views.avatar_select_view, name="avatar-select"),
    path("users/me/skills", views.my_skills_view, name="my-skills"),
    path("users/me/skills/<int:skill_id>", views.my_skill_detail_view, name="my-skill-detail"),
    path("users/me/work-preferences", views.work_preferences_view, name="work-preferences"),
    path("users/me/privacy-settings", views.privacy_settings_view, name="privacy-settings"),
    path("users/me/dashboard/projects", views.dashboard_projects_view, name="dashboard-projects"),
    # Job Ads Edit popup on the profile page: GET current state / PATCH
    # visible_on_profile for one of your own ProjectMember rows.
    path("users/me/memberships/<int:member_id>/visibility", views.membership_visibility_view, name="membership-visibility"),
    # New: PATCH /users/me/password — change the logged-in user's password
    # (old_password / new_password / confirm_password). See
    # views.change_password_view.
    path("users/me/password", views.change_password_view, name="change-password"),
    path("users/<int:id>", views.public_profile_view, name="public-profile"),
    path("users/<int:id>/active-projects-count", views.active_projects_count_view, name="active-projects-count"),
    path("users/<int:id>/report", views.report_user_view, name="report-user"),

    path("users/<int:user_id>/badges/", review_views.user_badges_view, name="user-badges"),

    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Was 'dashboard/' -> now lives conceptually under "Projects > My Projects".
    # URL path/name changed so it's no longer reachable as a standalone
    # top-level nav item; it's now only linked to from the Projects hub page.
    # NOTE: dashboard_projects_view (the JSON API dashboard.js calls) is
    # untouched — its URL, name, and response shape are all unchanged.
    path('my-projects/', views.my_projects_view, name='my-projects'),

    path('profile/', views.profile_page_view, name='profile-page'),
    path('profile/edit/', views.profile_edit_view, name='profile-edit'),
    path('profile/<int:id>/', views.profile_page_view, name='profile-page-detail'),

    # ------------------------------------------------------------------
    # NEW: Admin panel — reports themselves come from moderation.urls,
    # this is just the page + user-management endpoints the admin panel
    # needs. Every view below checks request.user.system_role == ADMIN.
    # ------------------------------------------------------------------
    path('panel/', views.admin_dashboard_view, name='admin-dashboard'),
    path('panel/users', views.admin_list_users_view, name='admin-users'),
    path('panel/users/<int:id>', views.admin_user_detail_view, name='admin-user-detail'),
    path('panel/users/<int:id>/status', views.admin_user_status_view, name='admin-user-status'),
]
