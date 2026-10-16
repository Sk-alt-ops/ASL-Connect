"""
Application configuration for the ASL User Dashboard.

Registers 'core.asl_user' as a Django app and sets the default
auto-generated primary key field type to BigAutoField.
"""

from django.apps import AppConfig


class AslUserConfig(AppConfig):
    """Django AppConfig for the ASL user dashboard application."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.asl_user'
    verbose_name = 'ASL User Dashboard'
