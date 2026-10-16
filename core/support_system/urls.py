"""
Support Ticket API URL Configuration

Provides REST endpoints for creating (text/video), listing, viewing,
and deleting support tickets.
"""

from django.urls import path
from . import views

app_name = 'support_system'

urlpatterns = [
    # --- Ticket Creation ---
    path('create/', views.create_ticket, name='create_ticket'),
    path('create-with-video/', views.create_ticket_with_video, name='create_ticket_with_video'),

    # --- Ticket Management ---
    path('list/', views.list_tickets, name='list_tickets'),
    path('<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('<int:ticket_id>/delete/', views.delete_ticket, name='delete_ticket'),
]
