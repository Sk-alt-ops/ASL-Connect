"""
WebSocket URL Routing — Chat & Presence

Maps WebSocket URL patterns to their corresponding consumer classes.
These routes are imported by the ASGI application (``config/asgi.py``)
and wrapped in Django Channels' AuthMiddlewareStack.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/presence/$', consumers.PresenceConsumer.as_asgi()),
]
