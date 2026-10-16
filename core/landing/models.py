"""
Landing Page Models — Contact Forms, Newsletter, User Activity

Provides the data models for:
- ``ContactMessage``: Visitor contact form submissions
- ``NewsletterSubscriber``: Email newsletter opt-in/out management
- ``UserActivity``: Dashboard activity feed (calls, friend requests, chats)
"""

from django.db import models
from django.conf import settings


# ===========================================================================
# CONTACT MESSAGES
# ===========================================================================


class ContactMessage(models.Model):
    """Stores contact form submissions from landing page visitors."""

    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200, blank=True, default='')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    replied_at = models.DateTimeField(null=True, blank=True)
    reply_message = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"Message from {self.name}"
            f" - {self.subject or '(no subject)'}"
        )


# ===========================================================================
# NEWSLETTER
# ===========================================================================


class NewsletterSubscriber(models.Model):
    """Manages email newsletter subscriptions with opt-in/out."""

    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.email


# ===========================================================================
# USER ACTIVITY FEED
# ===========================================================================


class UserActivity(models.Model):
    """Tracks user actions for the dashboard activity feed display."""

    ACTIVITY_TYPES = [
        ('video_call', 'Video Call'),
        ('friend_request_sent', 'Friend Request Sent'),
        ('friend_request_accepted', 'Friend Request Accepted'),
        ('profile_update', 'Profile Update'),
        ('chat_message', 'Chat Message'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}: {self.activity_type}"
