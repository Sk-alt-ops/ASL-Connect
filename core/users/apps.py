"""
Django App Configuration for the Users app.
"""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Default configuration for the ``core.users`` app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.users'
