# chat/consumers.py
import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.utils import timezone

from . import services
from .serialization import serialize_message, serialize_conversation_summary

User = get_user_model()


class BaseChatConsumer(AsyncWebsocketConsumer):
    """Pushes a JSON payload, built by group_send, straight to the client."""

    async def chat_event(self, event):
        await self.send(text_data=json.dumps(event['payload']))


async def _broadcast_sidebar_updates(channel_layer, room_id):
    """
    After a message is saved, push a personalized conversation-summary
    update to every active participant's personal notification group,
    so their sidebar (on ANY page) reorders/updates live.
    """
    participant_ids = await database_sync_to_async(services.get_active_participant_user_ids)(room_id)
    for uid in participant_ids:
        summary = await database_sync_to_async(services.get_conversation_summary_for_participant)(room_id, uid)
        if summary is None:
            continue
        await channel_layer.group_send(
            f'chat_notify_{uid}',
            {'type': 'chat.event', 'payload': {
                'action': 'conversation_update',
                'conversation': serialize_conversation_summary(summary),
            }},
        )


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

        # The user is actively viewing the room the moment the socket opens.
        await self._mark_read_and_broadcast()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        action = data.get('action')
        if action == 'send_message':
            await self._handle_send_message(data)
        elif action == 'mark_read':
            await self._mark_read_and_broadcast()

    async def _handle_send_message(self, data):
        if await database_sync_to_async(services.is_room_closed)(self.room_id):
            return

        content = (data.get('content') or '').strip()
        if not content:
            return

        message = await database_sync_to_async(services.save_message)(
            self.room_id, self.user.id, content
        )
        message.sender = self.user
        payload = {'action': 'new_message', 'message': serialize_message(message)}
        payload['message']['client_ref'] = data.get('client_ref')

        await self.channel_layer.group_send(
            self.group_name, {'type': 'chat.event', 'payload': payload}
        )

        
        await _broadcast_sidebar_updates(self.channel_layer, self.room_id)

    async def _mark_read_and_broadcast(self):
        await database_sync_to_async(services.mark_room_read)(self.room_id, self.user.id)

        payload = {
            'action': 'read_receipt',
            'user_id': self.user.id,
            'read_at': timezone.now().isoformat(),
        }
        await self.channel_layer.group_send(
            self.group_name, {'type': 'chat.event', 'payload': payload}
        )

        
        summary = await database_sync_to_async(services.get_conversation_summary_for_participant)(
            self.room_id, self.user.id
        )
        if summary:
            await self.channel_layer.group_send(
                f'chat_notify_{self.user.id}',
                {'type': 'chat.event', 'payload': {
                    'action': 'conversation_update',
                    'conversation': serialize_conversation_summary(summary),
                }},
            )


class DirectChatConsumer(BaseChatConsumer):
    """
    Handles a DIRECT chat that might not have a ChatRoom row yet — the
    room is created lazily, exactly when the first message is sent.
    URL: ws/chat/user/<other_user_id>/
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
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        if data.get('action') != 'send_message':
            return

        content = (data.get('content') or '').strip()
        if not content:
            return

        room, message = await database_sync_to_async(services.send_first_or_next_direct_message)(
            self.user.id, self.other_user_id, content
        )
        if message is None:
            return

        message.sender = self.user
        payload = {'action': 'new_message', 'message': serialize_message(message)}
        payload['message']['room_id'] = room.id

        await self.channel_layer.group_send(
            self.group_name, {'type': 'chat.event', 'payload': payload}
        )

        
        await _broadcast_sidebar_updates(self.channel_layer, room.id)


class UserNotificationConsumer(BaseChatConsumer):
    """
    A lightweight, room-agnostic socket used purely to keep the
    conversation sidebar live-updated on any page (inbox, room,
    new-direct-chat). One instance per open tab; joins a personal
    group keyed by user id.
    URL: ws/chat/notify/
    """

    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return

        self.group_name = f'chat_notify_{self.user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)