"""
ASL User Dashboard — URL Configuration.

Defines the URL patterns for the ASL user dashboard application.

URL Prefix (configured in config/urls.py):
    /asl/ — All ASL user routes are mounted under this prefix.

Namespace:
    app_name = 'asl_user' — Used for reverse URL resolution.

URL Patterns:
    dashboard/  →  views.dashboard  (name: 'dashboard')
        The main SPA shell page accessible at /asl/dashboard/.
"""

from django.urls import path
from . import views

app_name = 'asl_user'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
]
