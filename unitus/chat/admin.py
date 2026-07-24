from django.contrib import admin
from .models import ChatRoom, ChatParticipant, Message


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ("id", "type", "project", "is_closed")
    list_filter = ("type", "is_closed")
    search_fields = ("project__title",)


@admin.register(ChatParticipant)
class ChatParticipantAdmin(admin.ModelAdmin):
    list_display = ("user", "room", "is_active", "notifications_muted")
    list_filter = ("is_active", "notifications_muted")
    search_fields = ("user__username",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "sender", "room", "sent_at")
    list_filter = ("sent_at",)
    search_fields = ("content", "sender__username")