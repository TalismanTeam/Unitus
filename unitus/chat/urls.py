from django.urls import path

from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.inbox_view, name='inbox'),
    path('room/<int:room_id>/', views.room_view, name='room'),
    path('room/<int:room_id>/messages/', views.messages_history_api, name='room_messages'),
    path('room/<int:room_id>/delete/', views.delete_conversation_view, name='delete_conversation'),
    path('start/<int:user_id>/', views.start_direct_chat_view, name='start_direct_chat'),
]