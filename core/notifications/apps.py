"""
Django App Configuration for the Notifications app.
"""

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """Default configuration for the ``core.notifications`` app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.notifications'
