"""
Admin Configuration for Landing Page Models

Registers ContactMessage, NewsletterSubscriber, and UserActivity
with custom list displays, filters, and search fields.
"""

from django.contrib import admin
from .models import ContactMessage, NewsletterSubscriber, UserActivity


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    """Contact form submissions with read/unread status management."""
    list_display = ('name', 'email', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'message')
    readonly_fields = ('created_at',)
    list_editable = ('is_read',)


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    """Newsletter email subscriptions with active/inactive toggle."""
    list_display = ('email', 'subscribed_at', 'is_active')
    list_filter = ('is_active', 'subscribed_at')
    search_fields = ('email',)


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """User activity log for dashboard feed display."""
    list_display = ('user', 'activity_type', 'description', 'created_at')
    list_filter = ('activity_type', 'created_at')
    search_fields = ('user__username', 'description')
