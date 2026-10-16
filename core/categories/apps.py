"""
Django application configuration for the ``core.categories`` app.

Registers the app with :attr:`~CategoriesConfig.verbose_name` metadata
displayed in the admin interface.
"""

from django.apps import AppConfig


class CategoriesConfig(AppConfig):
    """Configuration for the ASL Categories application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "core.categories"
    verbose_name = "ASL Content — Categories, Gestures & Symbols"
