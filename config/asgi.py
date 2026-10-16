"""
ASL Connect — ASGI Configuration

Entry point for the ASGI server (Daphne / Uvicorn).
Routes HTTP requests to Django's WSGI handler and WebSocket
connections through Django Channels' authentication middleware
to the chat application's consumers.
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from core.chat.routing import websocket_urlpatterns

# ---------------------------------------------------------------------------
# Environment setup
# ---------------------------------------------------------------------------
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# ---------------------------------------------------------------------------
# ASGI application — protocol router
# ---------------------------------------------------------------------------
# ProtocolTypeRouter inspects the incoming connection type:
#   - HTTP traffic     -> standard Django WSGI handler (get_asgi_application)
#   - WebSocket traffic -> authenticated via AuthMiddlewareStack, then routed
#                          to chat app consumers via core.chat.routing
application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
