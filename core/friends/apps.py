"""
Django App Configuration for the Friends app.
"""

from django.apps import AppConfig


class FriendsConfig(AppConfig):
    """Default configuration for the ``core.friends`` app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.friends'
