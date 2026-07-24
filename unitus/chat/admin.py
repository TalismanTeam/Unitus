from django.contrib import admin

from .models import ChatParticipant, ChatRoom, Message


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'project', 'is_closed')
    list_filter = ('type', 'is_closed')


@admin.register(ChatParticipant)
class ChatParticipantAdmin(admin.ModelAdmin):
    list_display = ('room', 'user', 'is_active', 'last_read_at')
    list_filter = ('is_active',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'room', 'sender', 'sent_at')