"""
Django App Configuration for the Frontend app.
"""

from django.apps import AppConfig


class FrontendConfig(AppConfig):
    """Default configuration for the ``core.frontend`` app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.frontend'
