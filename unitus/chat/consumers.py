import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model

from . import services
from .serialization import serialize_message

User = get_user_model()


class BaseChatConsumer(AsyncWebsocketConsumer):
    """Shared handler for broadcasting a saved message to everyone in the group."""

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event['message']))


class ChatConsumer(BaseChatConsumer):
    """
    Handles an EXISTING chat room (GROUP chats, and DIRECT chats after
    the room has already been created).
    URL: ws/chat/room/<room_id>/
    """

    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return

        self.room_id = int(self.scope['url_route']['kwargs']['room_id'])

        is_member = await database_sync_to_async(services.is_active_participant)(
            self.room_id, self.user.id
        )
        if not is_member:
            await self.close()
            return

        self.group_name = f'chat_room_{self.room_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await database_sync_to_async(services.mark_room_read)(self.room_id, self.user.id)

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        content = (data.get('content') or '').strip()
        if not content:
            return

        message = await database_sync_to_async(services.save_message)(
            self.room_id, self.user.id, content
        )
        payload = serialize_message(message)

        await self.channel_layer.group_send(
            self.group_name,
            {'type': 'chat.message', 'message': payload},
        )


class DirectChatConsumer(BaseChatConsumer):
    """
    Handles a DIRECT chat that might not have a ChatRoom row yet — the
    room is created lazily, exactly when the first message is sent.
    URL: ws/chat/user/<other_user_id>/

    Both sides join a channel group keyed by their sorted user-id pair
    (not by room_id), since the room might not exist when they connect.
    """

    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return

        self.other_user_id = int(self.scope['url_route']['kwargs']['other_user_id'])
        if self.other_user_id == self.user.id:
            await self.close()
            return

        other_exists = await database_sync_to_async(
            lambda: User.objects.filter(id=self.other_user_id, is_active=True).exists()
        )()
        if not other_exists:
            await self.close()
            return

        pair = sorted([self.user.id, self.other_user_id])
        self.group_name = f'chat_direct_{pair[0]}_{pair[1]}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        content = (data.get('content') or '').strip()
        if not content:
            return

        room, message = await database_sync_to_async(services.send_first_or_next_direct_message)(
            self.user.id, self.other_user_id, content
        )
        if message is None:
            return  # room turned out to be closed

        payload = serialize_message(message)
        payload['room_id'] = room.id  # lets the frontend switch to ws/chat/room/<id>/ afterwards

        await self.channel_layer.group_send(
            self.group_name,
            {'type': 'chat.message', 'message': payload},
        )