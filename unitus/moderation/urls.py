from django.urls import path

from . import views

urlpatterns = [
    path('reports', views.create_report, name='create_report'),
    path('admin/reports', views.list_reports, name='list_reports'),
    path('admin/reports/<int:report_id>', views.resolve_report, name='resolve_report'),
]
