"""
ASL Connect — Root URL Configuration

Maps URL patterns to Django apps. Each app defines its own urlpatterns
in core/<app_name>/urls.py.

In development, user-uploaded media files are served directly via
Django's static() helper. In production, media should be served
by a reverse proxy (e.g., Nginx).
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# ===========================================================================
# URL PATTERNS
# ===========================================================================
# Each entry delegates routing to the corresponding app's urls.py module.

urlpatterns = [
    # --- Admin & Dashboard ---
    path('admin/', admin.site.urls),                            # Django admin interface
    path('admin-panel/', include('core.admin_dashboard.urls')), # Custom admin dashboard

    # --- Landing & Authentication ---
    path('', include('core.landing.urls')),                     # Landing / home page
    path('', include('core.users.urls')),                       # Authentication (login, register, etc.)

    # --- User Dashboards ---
    path('asl/', include('core.asl_user.urls')),                # Deaf (ASL) user dashboard
    path('normal/', include('core.normal_user.urls')),          # Hearing user dashboard

    # --- Social Features ---
    path('friends/', include('core.friends.urls')),             # Friends / follow system
    path('notifications/', include('core.notifications.urls')), # In-app notifications

    # --- ASL Content ---
    path('categories/', include('core.categories.urls')),       # ASL categories, gestures, symbols

    # --- Support ---
    path('support/', include('core.support_system.urls')),      # Support / ticketing system

    # --- Communication ---
    path('chat/', include('core.chat.urls')),                   # Real-time chat messaging
    path('translation/', include('core.translation.urls')),     # ASL-to-text and text-to-ASL translation

    # --- Frontend ---
    path('frontend/', include('core.frontend.urls')),           # Frontend rendering views
]

# ===========================================================================
# DEVELOPMENT MEDIA SERVING
# ===========================================================================
# In DEBUG mode, serve media files (user uploads) directly from the
# MEDIA_ROOT directory. In production, a reverse proxy (Nginx, CDN)
# should handle media file serving instead.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
