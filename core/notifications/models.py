"""
Notification Model for In-App Real-Time Notifications

Supports 16 notification types with read tracking, real-time WebSocket
push via Django Channels, and user-specific targeting.

Types include:
- Social: friend_request, friend_accepted, friend_rejected
- Messaging: message
- Support: support_request, support_response, support_video_response
- System: system, system_announcement, feature_announcement, maintenance
- Account: profile_update, password_change
- Content: new_gesture, new_gesture_category, contact_form
"""

from django.db import models
from django.conf import settings


class Notification(models.Model):
    """
    Represents a single in-app notification delivered to a user.

    Notifications are created programmatically via the create_notification
    helper in core.notifications.views and pushed to the recipient in
    real-time over a WebSocket connection.

    Each notification type maps to a specific icon and determines the
    click-behavior in the frontend notification dropdown.
    """

    NOTIFICATION_TYPES = [
        ('friend_request', 'Friend Request'),
        ('friend_accepted', 'Friend Accepted'),
        ('friend_rejected', 'Friend Rejected'),
        ('message', 'New Message'),
        ('contact_form', 'Contact Form'),
        ('support_request', 'Support Request'),
        ('support_response', 'Support Response'),
        ('support_video_response', 'Support Video Response'),
        ('system_announcement', 'System Announcement'),
        ('system', 'System'),
        ('profile_update', 'Profile Update'),
        ('password_change', 'Password Change'),
        ('feature_announcement', 'Feature Announcement'),
        ('maintenance', 'Maintenance Notice'),
        ('new_gesture_category', 'New Gesture Category'),
        ('new_gesture', 'New Gesture Uploaded'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text='The user who receives this notification.',
        verbose_name='Recipient',
    )
    type = models.CharField(
        max_length=25,
        choices=NOTIFICATION_TYPES,
        help_text='The notification category, which determines the icon and click behavior.',
        verbose_name='Notification Type',
    )
    title = models.CharField(
        max_length=200,
        help_text='Short headline displayed in the notification dropdown and page.',
        verbose_name='Title',
    )
    message = models.TextField(
        help_text='Detailed body text explaining the notification event.',
        verbose_name='Message',
    )
    link = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='Optional URL the notification links to when clicked.',
        verbose_name='Link',
    )
    related_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_notifications',
        help_text='The other user involved in this event (e.g., friend request sender).',
        verbose_name='Related User',
    )
    is_read = models.BooleanField(
        default=False,
        help_text='Whether the user has opened or clicked this notification.',
        verbose_name='Is Read',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Timestamp when the notification was created.',
        verbose_name='Created At',
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text='Custom Font Awesome icon class. Falls back to type-based default if empty.',
        verbose_name='Icon Class',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        """Return a human-readable summary: title — recipient username."""
        return f'{self.title} — {self.user.username}'
