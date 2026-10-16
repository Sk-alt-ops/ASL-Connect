# App Configuration -- Admin Dashboard
# ---------------------------------------------------------------------------
# Registers this Django app under the label 'core.admin_dashboard'.
from django.apps import AppConfig


class AdminDashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.admin_dashboard'
