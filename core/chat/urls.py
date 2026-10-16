"""
Chat REST API URL Configuration.

Maps URL paths to chat view classes for all messaging endpoints.
All paths are under the ``/chat/`` namespace.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('api/send/', views.SendMessage.as_view(), name='chat-send'),
    path('api/messages/', views.GetMessages.as_view(), name='chat-messages'),
    path('api/delete/', views.DeleteMessage.as_view(), name='chat-delete'),
    path('api/copy/', views.CopyMessage.as_view(), name='chat-copy'),
    path('api/mark-read/', views.MarkAsRead.as_view(), name='chat-mark-read'),
    path('api/chat-list/', views.GetChatList.as_view(), name='chat-list'),
    path('api/unread-counts/', views.GetUnreadCounts.as_view(), name='chat-unread-counts'),
]
