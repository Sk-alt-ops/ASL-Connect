"""
Django App Configuration for the Landing app.
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Default configuration for the ``core.landing`` app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.landing'
    verbose_name = 'Landing Page'
