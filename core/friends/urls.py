"""
Friend System URL Configuration

Provides AJAX API endpoints for the full social friendship lifecycle:
send, accept, reject, cancel, list friends, unfriend, search users,
and view pending/sent requests.
"""

from django.urls import path
from . import views

app_name = 'friends'

urlpatterns = [
    # --- Request Lifecycle ---
    path('send/', views.SendFriendRequest.as_view(), name='send'),
    path('accept/', views.AcceptFriendRequest.as_view(), name='accept'),
    path('reject/', views.RejectFriendRequest.as_view(), name='reject'),
    path('cancel/', views.CancelFriendRequest.as_view(), name='cancel'),

    # --- Friend Management ---
    path('list/', views.FriendListView.as_view(), name='list'),
    path('unfriend/', views.UnfriendUser.as_view(), name='unfriend'),
    path('search/', views.SearchUsers.as_view(), name='search'),

    # --- Request Listings ---
    path('pending/', views.PendingRequests.as_view(), name='pending'),
    path('sent/', views.SentRequests.as_view(), name='sent'),
]
