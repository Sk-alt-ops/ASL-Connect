"""
ASL Connect — WSGI Configuration

Entry point for the WSGI server (Gunicorn / uWSGI / runserver).
Exposes the WSGI callable as a module-level variable named `application`.

For more information, see:
    https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# ---------------------------------------------------------------------------
# Environment setup
# ---------------------------------------------------------------------------
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# ---------------------------------------------------------------------------
# WSGI application
# ---------------------------------------------------------------------------
application = get_wsgi_application()
