"""
Custom User Model for ASL Connect

Extends Django's AbstractUser with fields specific to the ASL Connect platform:
- is_asl_user: Flags whether a user is deaf/ASL-signing or hearing
- profile_picture: Optional avatar image for the user profile

This model is referenced project-wide via settings.AUTH_USER_MODEL
and is the central user model for all app relationships.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model supporting two user types for the ASL Connect platform:

    - ASL User (is_asl_user=True):
        Deaf or hard-of-hearing users who communicate primarily in ASL.
        These users see the ASL dashboard with gesture keyboards,
        ASL symbol translation, and gesture-based messaging.

    - Normal User (is_asl_user=False):
        Hearing users who communicate primarily in written/spoken language.
        These users see the normal dashboard with standard text messaging.

    The user type determines which dashboard is shown, how messages are
    translated, and what features are available.
    """
    is_asl_user = models.BooleanField(
        default=False,
        help_text=(
            'Designates whether this user is an ASL (sign language) user. '
            'ASL users see gesture-based keyboards, symbol translation, '
            'and the ASL dashboard. Normal users see text-based interfaces.'
        ),
        verbose_name='ASL User',
    )
    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        blank=True,
        null=True,
        help_text='Optional profile photo displayed in chat avatars and the user sidebar.',
        verbose_name='Profile Picture',
    )

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        """
        Return the user's email or username as their display identifier.
        Email is preferred since login uses email; falls back to username.
        """
        return self.email or self.username
