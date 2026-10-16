"""
Django App Configuration for the Normal User app.
"""

from django.apps import AppConfig


class NormalUserConfig(AppConfig):
    """Default configuration for the ``core.normal_user`` app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.normal_user'
