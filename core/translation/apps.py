"""
Django App Configuration for the Translation app.
"""

from django.apps import AppConfig


class TranslationConfig(AppConfig):
    """Default configuration for the ``core.translation`` app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.translation'
