from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/chat/room/(?P<room_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'^ws/chat/user/(?P<other_user_id>\d+)/$', consumers.DirectChatConsumer.as_asgi()),
]