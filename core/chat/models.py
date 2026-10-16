"""
Chat Message Model for Real-Time Messaging

Supports three message types that enable communication between ASL
users and hearing users:

- text: Plain text messages (used by hearing users)
- asl: ASL symbol sequences (typed via the ASL alphabet keyboard)
- gesture: Pre-recorded gesture videos (selected from categories)

Messages are stored with both sender and receiver so that the
translation engine can determine what each participant sees based
on their user type (ASL user vs hearing user).

The `asl_content` JSONField stores the array of ASL symbol references
for reconstruction in the chat UI. The `gesture` FK links to the
specific Gesture model instance.
"""

from django.db import models
from core.users.models import User
from core.categories.models import Gesture
from core.translation.utils import translate_message


class Message(models.Model):
    """
    Represents a single chat message between two users.

    A message can be one of three types:
    1. 'text' — Standard text message
    2. 'asl' — ASL symbol keyboard input (stored as JSON array in asl_content)
    3. 'gesture' — A pre-recorded ASL gesture video (FK to Gesture model)

    The translation engine (translation.utils.translate_message) reads
    the sender and receiver user types to determine how to display each
    message in a format appropriate for the viewer.
    """

    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('asl', 'ASL Symbols'),
        ('gesture', 'Gesture'),
    ]

    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        help_text='The user who sent this message.',
        verbose_name='Sender',
    )
    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_messages',
        help_text='The user who receives this message.',
        verbose_name='Receiver',
    )
    content = models.TextField(
        blank=True,
        default='',
        help_text='Text content of the message. Empty for gesture-type messages.',
        verbose_name='Content',
    )
    asl_content = models.JSONField(
        null=True,
        blank=True,
        help_text='Array of ASL symbol objects for asl-type messages. Each object has char, image_url, and id.',
        verbose_name='ASL Content',
    )
    gesture = models.ForeignKey(
        Gesture,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='The gesture video sent with this message (gesture-type messages only).',
        verbose_name='Gesture',
    )
    message_type = models.CharField(
        max_length=10,
        choices=MESSAGE_TYPES,
        default='text',
        help_text='The type of content: text, asl (symbols), or gesture (video).',
        verbose_name='Message Type',
    )
    is_read = models.BooleanField(
        default=False,
        help_text='Whether the receiver has read this message.',
        verbose_name='Is Read',
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='When the message was sent. Indexed for efficient chat list queries.',
        verbose_name='Timestamp',
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the receiver read this message. Null if unread.',
        verbose_name='Read At',
    )

    class Meta:
        ordering = ['timestamp']
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'

    def __str__(self):
        """Return a preview: 'sender -> receiver: content (truncated to 50 chars)'."""
        return f'{self.sender} → {self.receiver}: {self.content[:50]}'

    def to_dict(self, current_user):
        """
        Serialize this message to a dictionary with translated display fields.

        The translation engine determines how content appears for each
        participant based on their user type (ASL vs hearing). This method
        produces a single dict with the perspective of *current_user*.

        Parameters:
            current_user: The User object requesting the serialization
                          (determines is_mine and display_* fields).

        Returns:
            dict with all message fields, display translations, and
            (if applicable) gesture metadata.
        """
        translation = translate_message(
            sender_is_asl=self.sender.is_asl_user,
            receiver_is_asl=self.receiver.is_asl_user,
            content=self.content,
            message_type=self.message_type,
            asl_content=self.asl_content,
            gesture_id=self.gesture_id,
        )

        is_mine = self.sender == current_user

        display_fields = {
            'display_content': translation['sender_display_content'] if is_mine else translation['display_content'],
            'display_type': translation['sender_display_type'] if is_mine else translation['display_type'],
            'display_asl': translation['sender_display_asl'] if is_mine else translation['display_asl'],
            'display_gesture': translation['sender_display_gesture'] if is_mine else translation['display_gesture'],
        }

        d = {
            'id': self.id,
            'sender_id': self.sender.id,
            'sender_name': self.sender.get_full_name() or self.sender.username,
            'sender_is_asl': self.sender.is_asl_user,
            'receiver_id': self.receiver.id,
            'receiver_name': self.receiver.get_full_name() or self.receiver.username,
            'receiver_is_asl': self.receiver.is_asl_user,
            'content': self.content,
            'message_type': self.message_type,
            'asl_content': self.asl_content,
            'is_read': self.is_read,
            'is_mine': is_mine,
            'timestamp': self.timestamp.isoformat(),
            'read_at': self.read_at.isoformat() if self.read_at else None,
            **display_fields,
        }

        if self.gesture:
            d['gesture'] = {
                'id': self.gesture.id,
                'title': self.gesture.title,
                'translation': self.gesture.translation,
                'video_url': self.gesture.video.url if self.gesture.video else None,
            }

        return d
