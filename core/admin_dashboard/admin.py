"""
Admin Registration -- Admin Dashboard
========================================
Registers ``DesignSettings`` with Django's built-in admin interface so
that superusers can manually tweak configuration if needed.

``PageDesign`` and ``SectionDesign`` are managed through the custom
admin panel views rather than via Django admin.
"""

from django.contrib import admin

from .models import DesignSettings


@admin.register(DesignSettings)
class DesignSettingsAdmin(admin.ModelAdmin):
    """Admin configuration for the global DesignSettings singleton.

    Only the single ``pk=1`` instance exists, so listing/editing
    is straightforward.
    """
    list_display = ('site_title', 'updated_at')
    readonly_fields = ('updated_at',)
