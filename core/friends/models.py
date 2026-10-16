"""
Friend Request Model for the Social Friendship System

Manages bi-directional friend requests between users with three states:
pending -> accepted (forms a friendship) or rejected.

Unique-together constraint prevents duplicate requests between the same
pair of users.

The friend system powers:
- The friends list in the ASL dashboard sidebar
- Friend search and add functionality
- Chat conversation participants (only friends can chat)
"""

from django.db import models
from django.conf import settings


class FriendRequest(models.Model):
    """
    Represents a friend request between two users.

    A friendship is established when a request from User A to User B
    is accepted. The relationship is bi-directional — either user
    can initiate or remove the friendship.

    Status lifecycle:
    - pending: Request sent, awaiting response
    - accepted: Request approved — users are now friends
    - rejected: Request declined — can be re-sent later
    """

    PENDING = 'pending'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (ACCEPTED, 'Accepted'),
        (REJECTED, 'Rejected'),
    ]

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_friend_requests',
        help_text='The user who sent the friend request.',
        verbose_name='From User',
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_friend_requests',
        help_text='The user who received the friend request.',
        verbose_name='To User',
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=PENDING,
        help_text='Current status: pending (awaiting response), accepted (friends), or rejected.',
        verbose_name='Status',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Timestamp when the request was sent.',
        verbose_name='Created At',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='Timestamp of the last status change.',
        verbose_name='Updated At',
    )

    class Meta:
        ordering = ['-created_at']
        unique_together = ['from_user', 'to_user']
        verbose_name = 'Friend Request'
        verbose_name_plural = 'Friend Requests'

    def __str__(self):
        """Return a readable arrow notation: 'sender -> receiver (status)'."""
        return f'{self.from_user} → {self.to_user} ({self.status})'
