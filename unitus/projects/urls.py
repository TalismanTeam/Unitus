from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('new/', views.project_create, name='project_create'),
    path('<int:pk>/add-role/', views.project_add_role, name='project_add_role'),
    path('<int:pk>/workspace/', views.project_workspace, name='project_workspace'),
    path('<int:pk>/state/', views.project_state_change, name='project_state_change'),
    path('<int:pk>/members/<int:member_id>/remove/', views.project_remove_member, name='project_remove_member'),
    path('<int:pk>/transfer-ownership/', views.project_transfer_ownership, name='project_transfer_ownership'),
    path('jobads/<int:pk>/', views.jobad_detail, name='jobad_detail'),

    # Added routes
    path('<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('<int:pk>/delete/', views.project_delete, name='project_delete'),
    path('<int:pk>/roles/<int:role_id>/edit/', views.project_edit_role, name='project_edit_role'),
    path('<int:pk>/roles/<int:role_id>/delete/', views.project_delete_role, name='project_delete_role'),
    path('<int:pk>/resign/', views.project_resign, name='project_resign'),
]