"""
Admin configuration for the chat Message model.

Enables staff to browse, filter, and search all messages from
the Django admin interface.
"""

from django.contrib import admin
from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    Admin panel for inspecting chat messages.

    Supports filtering by message type, read status, and timestamp,
    as well as searching by sender/receiver username or message content.
    """

    list_display = ['sender', 'receiver', 'message_type', 'is_read', 'timestamp']
    list_filter = ['message_type', 'is_read', 'timestamp']
    search_fields = ['sender__username', 'receiver__username', 'content']
