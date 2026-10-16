"""
ASL Connect — Shared Utility Helpers

Provides reusable utility functions used across multiple apps:
- ``timesince()``: Human-readable relative time strings for JSON API responses
- ``sanitize_input()``: Strip HTML tags and trim whitespace (XSS prevention)
- ``build_user_summary()``: Serialize a user object into a consistent summary dict
- ``send_ws_group_event()``: Send a WebSocket event to a user's channel group

These helpers avoid code duplication and keep view logic focused on
request/response handling.
"""

import re
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


# ===========================================================================
# TIME HELPERS
# ===========================================================================


def timesince(dt):
    """
    Convert a datetime to a human-readable relative time string.

    Provides a lightweight alternative to Django's ``timesince`` template tag
    that works within JSON API responses.

    Examples:
        - Few seconds ago  → ``'Just now'``
        - 5 minutes ago    → ``'5m ago'``
        - 3 hours ago      → ``'3h ago'``
        - 1 day ago        → ``'Yesterday'``
        - 4 days ago       → ``'4d ago'``
        - 2 weeks ago      → ``'2w ago'``
        - 3 months ago     → ``'3mo ago'``
        - 1 year ago       → ``'1y ago'``
    """
    now = timezone.now()
    diff = now - dt

    if diff.days == 0:
        if diff.seconds < 60:
            return 'Just now'
        elif diff.seconds < 3600:
            return f'{diff.seconds // 60}m ago'
        else:
            return f'{diff.seconds // 3600}h ago'
    elif diff.days == 1:
        return 'Yesterday'
    elif diff.days < 7:
        return f'{diff.days}d ago'
    elif diff.days < 30:
        return f'{diff.days // 7}w ago'
    elif diff.days < 365:
        return f'{diff.days // 30}mo ago'
    else:
        return f'{diff.days // 365}y ago'


# ===========================================================================
# INPUT SANITIZATION
# ===========================================================================


def sanitize_input(value):
    """
    Strip HTML tags and trim surrounding whitespace.

    Prevents XSS attacks by removing any HTML markup from user-supplied
    text before storing or displaying it.
    """
    if not value:
        return ''
    value = re.sub(r'<[^>]*>', '', value)
    return value.strip()


# ===========================================================================
# USER SERIALIZATION
# ===========================================================================


def build_user_summary(user):
    """
    Return a consistent dictionary summary of a user object.

    Used across views to avoid repeating the same field mapping logic
    for friend lists, notifications, chat participants, etc.
    """
    return {
        'id': user.id,
        'username': user.username,
        'full_name': user.get_full_name() or user.username,
        'is_asl_user': user.is_asl_user,
    }


# ===========================================================================
# WEBSOCKET HELPERS
# ===========================================================================


def send_ws_group_event(user_id, event_data):
    """
    Send a real-time WebSocket event to a specific user's personal group.

    The frontend listens on the ``user_{user_id}`` channel group for
    events and updates the UI without requiring a page refresh.
    """
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f'user_{user_id}',
            event_data,
        )
