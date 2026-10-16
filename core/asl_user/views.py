"""
ASL User Dashboard — Views.

Provides the main entry point for ASL (Deaf/Signing) users after login.

The dashboard is rendered as a single-page application (SPA) shell.
All dynamic content — chat messages, friends list, notifications,
settings, profile editing, help tickets — is loaded asynchronously
via JavaScript fetch() calls to REST API endpoints exposed by
sibling apps (core.chat, core.friends, core.notifications, etc.).

ASL User Type Enforcement:
    The @login_required decorator on the dashboard view ensures that
    only authenticated users can access the page. Additional checks
    for is_asl_user are applied at the API level in each sibling app
    to restrict ASL-specific features appropriately.

Design Customization:
    The template receives design_settings from the admin_dashboard
    context processor, enabling dynamic theming (colors, fonts, layout)
    without modifying template or CSS files directly.

ASL Translation Workflow:
    Users can compose messages using:
        1. Text input (standard keyboard)
        2. ASL Alphabet Keyboard (26 letters + 10 numbers with hand-sign
           images fetched from categories/api/asl-symbols/)
        3. ASL Sign Selector (gesture categories with video/image signs
           fetched from categories/api/public/categories/)
    Messages are sent via WebSocket (with HTTP fallback) and stored
    with a message_type field ('text', 'asl', or 'gesture') for
    appropriate rendering on the receiving end.
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required(login_url='/')
def dashboard(request):
    """
    Render the main ASL user dashboard SPA shell template.

    This view returns the base HTML page that bootstraps the entire
    client-side application. The template receives the Django request
    context automatically, including:

        - request.user         : Authenticated User object
        - design_settings      : Dynamic theme variables from the
                                 admin_dashboard context processor

    All content panels (chat, friends, notifications, settings,
    profile, help) are rendered by JavaScript on the client side.
    """
    return render(request, 'asl_user/dashboard.html')
