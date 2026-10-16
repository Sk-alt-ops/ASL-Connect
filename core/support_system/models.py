"""
Support Ticket Model for User Help Requests

ASL and normal users can submit support tickets with text descriptions
and/or recorded ASL videos. Admin/staff users can respond with text
replies or video responses.

The model supports four ticket statuses that track the lifecycle:
open -> in_progress -> resolved -> closed
"""

from django.db import models
from django.conf import settings
from django.utils import timezone


class SupportTicket(models.Model):
    """
    Represents a single support/help ticket submitted by a user.

    Tickets can include:
    - A text description of the issue
    - An optional ASL video recording showing the issue
    - An admin text response
    - An admin video response

    The ticket_type field distinguishes between ASL and normal user
    tickets for routing purposes.
    """

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    TICKET_TYPE_CHOICES = [
        ('asl', 'ASL User'),
        ('normal', 'Normal User'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='support_tickets',
        help_text='The user who submitted this support ticket.',
        verbose_name='Submitter',
    )
    ticket_type = models.CharField(
        max_length=10,
        choices=TICKET_TYPE_CHOICES,
        help_text='Whether this ticket was submitted by an ASL user or a normal (hearing) user.',
        verbose_name='Ticket Type',
    )
    subject = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text='Optional short subject line summarizing the issue.',
        verbose_name='Subject',
    )
    issue_description = models.TextField(
        help_text='Detailed description of the issue or question from the user.',
        verbose_name='Issue Description',
    )
    video = models.FileField(
        upload_to='support_videos/',
        blank=True,
        null=True,
        help_text='Optional ASL video recording showing the issue in sign language.',
        verbose_name='User Video',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open',
        help_text='Current lifecycle state of the ticket.',
        verbose_name='Status',
    )
    admin_response_video = models.FileField(
        upload_to='support_responses/',
        blank=True,
        null=True,
        help_text='Video response from admin/staff (e.g., ASL explanation).',
        verbose_name='Admin Video Response',
    )
    admin_response_text = models.TextField(
        blank=True,
        default='',
        help_text='Text response from admin/staff explaining the resolution.',
        verbose_name='Admin Text Response',
    )
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp when the admin last responded to this ticket.',
        verbose_name='Responded At',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Timestamp when the ticket was first submitted.',
        verbose_name='Created At',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='Timestamp of the last update to this ticket.',
        verbose_name='Updated At',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Support Ticket'
        verbose_name_plural = 'Support Tickets'

    def __str__(self):
        """Return a human-readable summary: [type] ticket #id by username."""
        return f'{self.get_ticket_type_display()} ticket #{self.id} by {self.user.username}'
