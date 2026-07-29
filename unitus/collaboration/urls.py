from django.urls import path

from . import views

app_name = 'collaboration'

urlpatterns = [
    path('', views.ticket_management_view, name='ticket-management'),
    # NOTE: /tickets/history must be registered before /tickets/<id> would
    # only matter if that path used a string converter; since it's <int:...>
    # there's no ambiguity, but it's kept first for readability.
    path('', views.ticket_management_view, name='ticket-management'),
    path('tickets/history', views.ticket_history_view, name='ticket-history'),
    path('tickets', views.tickets_view, name='ticket-list-create'),
    path('tickets/<int:ticket_id>', views.ticket_detail_view, name='ticket-detail'),
    path('tickets/<int:ticket_id>/respond', views.ticket_respond_view, name='ticket-respond'),
]
