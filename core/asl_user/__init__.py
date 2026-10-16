"""
ASL Connect — ASL User Dashboard Application.

This Django app provides the main ASL (Deaf/Signing) user dashboard
as a single-page application (SPA). It renders the HTML shell that
bootstraps all client-side functionality including:

    - Real-time chat with WebSocket support
    - ASL alphabet keyboard and gesture sign selector for composing
      messages using American Sign Language symbols
    - Friend management (search, send, accept, reject requests)
    - Notification system (bell dropdown + full-page view)
    - Help & Support ticket system with video recording
    - Profile management and account settings
    - Presence (online/offline) tracking

Architecture:
    The ASL user app is intentionally thin — it owns only the dashboard
    view, template, static files (CSS/JS), and URL routing. All business
    logic and API endpoints live in dedicated sibling apps:

        core.chat          — Messaging and WebSocket consumers
        core.friends       — Friend request CRUD and search
        core.notifications — Read/unread notification management
        core.categories    — ASL symbols, gesture categories, signs
        core.support_system — Help ticket submission and admin replies
        core.users         — Authentication, profile update, password change
        core.translation   — ASL-to-text and text-to-ASL translation

Authentication:
    - The dashboard requires login via @login_required.
    - API views in sibling apps check is_asl_user where appropriate.
    - Client-side navigation enforces ASL user context via the template.
"""
