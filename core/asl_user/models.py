"""
ASL User — Database Models.

This app does not define any custom models. The user model is defined
centrally in core.users.models.User and reused across the project.

The ASL user dashboard relies on models from sibling apps:

    core.chat.models.Message
    core.friends.models.FriendRequest
    core.notifications.models.Notification
    core.support_system.models.SupportTicket
    core.categories.models.AslSymbol, GestureCategory, Gesture

These models are queried via REST API calls from the JavaScript
frontend rather than through direct server-side rendering.
"""

# If the app ever needs its own models, define them here.
# For now, the User model from core/users/models.py is used
# with the is_asl_user flag differentiating user types.
