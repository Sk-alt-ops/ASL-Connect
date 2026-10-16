"""
Admin Configuration for Support Tickets

Registers SupportTicket with filters by type, status, and date,
plus search fields for user and content lookup.
"""

from django.contrib import admin
from .models import SupportTicket


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    """Support ticket management with inline status and type filters."""
    list_display = (
        'id', 'user', 'ticket_type', 'status', 'created_at', 'responded_at',
    )
    list_filter = ('ticket_type', 'status', 'created_at')
    search_fields = ('user__username', 'user__email', 'issue_description', 'subject')
    readonly_fields = ('created_at', 'updated_at', 'responded_at')
