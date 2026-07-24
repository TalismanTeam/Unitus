from django.urls import path

from . import views

app_name = "skills"

urlpatterns = [
    path("categories/", views.categories_view, name="categories"),
    path("custom/", views.create_custom_skill_view, name="create-custom"),
    path("custom/<int:skill_id>/", views.delete_custom_skill_view, name="delete-custom"),
    path("<int:skill_id>/stats/", views.skill_stats_view, name="stats"),
    path("", views.skills_list_view, name="list"),
]
