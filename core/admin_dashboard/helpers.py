"""
Helpers -- Admin Dashboard
============================
Small, pure utility functions used across the admin_dashboard app.
Kept here so views and services stay focused on business logic.
"""

from django.utils import timezone


def timesince(dt):
    """Return a human-readable relative time string for a datetime.

    Examples::

        >>> timesince(now - timedelta(seconds=30))
        'Just now'
        >>> timesince(now - timedelta(hours=2))
        '2h ago'
        >>> timesince(now - timedelta(days=3))
        '3d ago'
        >>> timesince(now - timedelta(weeks=3))
        '3w ago'
    """
    now = timezone.now()
    diff = now - dt

    if diff.days == 0:
        if diff.seconds < 60:
            return 'Just now'
        elif diff.seconds < 3600:
            return f'{diff.seconds // 60}m ago'
        else:
            return f'{diff.seconds // 3600}h ago'
    elif diff.days == 1:
        return 'Yesterday'
    elif diff.days < 7:
        return f'{diff.days}d ago'
    elif diff.days < 56:
        return f'{diff.days // 7}w ago'
    elif diff.days < 365:
        return f'{diff.days // 30}mo ago'
    else:
        return f'{diff.days // 365}y ago'
