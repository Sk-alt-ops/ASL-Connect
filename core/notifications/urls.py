"""
Notification API URL Configuration

Provides REST endpoints for the notification dropdown and full-page view:
list, unread count, mark read (single/all), delete (single/all).
"""

from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # --- Listing ---
    path('', views.NotificationListView.as_view(), name='list'),
    path('unread-count/', views.UnreadNotificationCount.as_view(), name='unread_count'),

    # --- Read Status ---
    path('mark-read/', views.MarkNotificationRead.as_view(), name='mark_read'),
    path('mark-all-read/', views.MarkAllNotificationsRead.as_view(), name='mark_all_read'),

    # --- Deletion ---
    path('delete/', views.DeleteNotification.as_view(), name='delete'),
    path('delete-all/', views.DeleteAllNotifications.as_view(), name='delete_all'),
]
