"""
Notification Views — List, Create, Mark Read, Delete with Real-Time Push

Provides AJAX endpoints for the notification system with real-time
WebSocket push via Django Channels.

Key workflows:
- Notifications are created by ``create_notification()`` and pushed to
  the recipient's WebSocket group immediately
- Staff receive support/contact-form notifications via ``notify_staff_users()``
- The dropdown and full-page views use the same CRUD endpoints

Security note: All querysets are scoped to ``user=request.user`` to
prevent data leakage (multi-tenant safety).
"""

import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from .models import Notification
from core.helpers import send_ws_group_event, build_user_summary

User = get_user_model()


# ===========================================================================
# NOTIFICATION CREATION HELPERS
# ===========================================================================


def send_realtime_notification(user_id, notification_data):
    """
    Push a notification to a specific user's WebSocket group.

    The frontend receives the ``notification_event`` message type and
    updates the notification dropdown and badge without a page refresh.
    """
    send_ws_group_event(user_id, {
        'type': 'notification_event',
        'notification': notification_data,
    })


def _serialize_notification(notif):
    """
    Convert a Notification model instance to a standardised dictionary
    for JSON API responses and WebSocket payloads.
    """
    return {
        'id': notif.id,
        'type': notif.type,
        'title': notif.title,
        'message': notif.message,
        'link': notif.link,
        'related_user_id': notif.related_user_id,
        'related_username': (
            notif.related_user.username if notif.related_user else None
        ),
        'is_read': notif.is_read,
        'icon': notif.icon,
        'created_at': notif.created_at.isoformat(),
    }


def create_notification(
    user, type, title, message, link='', related_user=None, icon='',
):
    """
    Create a notification for a single user and deliver it via WebSocket.

    This is the primary helper used across all apps to send notifications.
    It persists to the database and sends a real-time event to the
    recipient's WebSocket connection.

    Returns the created ``Notification`` instance.
    """
    notif = Notification.objects.create(
        user=user,
        type=type,
        title=title,
        message=message,
        link=link,
        related_user=related_user,
        icon=icon,
    )
    send_realtime_notification(user.id, _serialize_notification(notif))
    return notif


def notify_staff_users(
    type, title, message, link='', related_user=None, icon='',
):
    """
    Create and deliver a notification to all staff and superuser accounts.

    Used for support ticket submissions, contact form messages, and other
    events requiring admin attention.

    Returns a list of created ``Notification`` instances.
    """
    staff_users = User.objects.filter(
        Q(is_staff=True) | Q(is_superuser=True),
    ).distinct()
    created = []
    for user in staff_users:
        notif = Notification.objects.create(
            user=user,
            type=type,
            title=title,
            message=message,
            link=link,
            related_user=related_user,
            icon=icon,
        )
        send_realtime_notification(user.id, _serialize_notification(notif))
        created.append(notif)
    return created


# ===========================================================================
# LIST & COUNT VIEWS
# ===========================================================================


@method_decorator(login_required, name='dispatch')
class NotificationListView(View):
    """
    List the current user's notifications with optional search/type filtering.

    **GET** params:
    - ``limit`` — max results (default: all)
    - ``search`` — filter by title/message (case-insensitive)
    - ``type`` — filter by category (supports grouped: ``gesture``,
      ``friend``, ``support``, ``system``, ``messages``)

    Returns notifications ordered by most recent first.
    """

    def get(self, request):
        limit = request.GET.get('limit')
        search = request.GET.get('search', '')
        type_filter = request.GET.get('type', '')
        notifications = Notification.objects.filter(user=request.user)

        if search:
            notifications = notifications.filter(
                Q(title__icontains=search)
                | Q(message__icontains=search),
            )
        if type_filter:
            notifications = self._apply_type_filter(
                notifications, type_filter,
            )

        if limit:
            try:
                notifications = notifications[:int(limit)]
            except (ValueError, TypeError):
                pass

        data = [_serialize_notification(n) for n in notifications]
        return JsonResponse({'success': True, 'notifications': data})

    def _apply_type_filter(self, queryset, type_filter):
        """Apply grouped or single type filter to the notification queryset."""
        group_filters = {
            'gesture': ['new_gesture', 'new_gesture_category'],
            'friend': [
                'friend_request', 'friend_accepted', 'friend_rejected',
            ],
            'support': [
                'support_request', 'support_response',
                'support_video_response',
            ],
            'system': [
                'system', 'system_announcement', 'feature_announcement',
                'maintenance', 'profile_update', 'password_change',
            ],
            'messages': ['message'],
        }
        if type_filter in group_filters:
            return queryset.filter(type__in=group_filters[type_filter])
        return queryset.filter(type=type_filter)


@method_decorator(login_required, name='dispatch')
class UnreadNotificationCount(View):
    """
    Return the count of unread notifications for bell badge display.

    Called by the frontend on page load and after each polling interval.
    """

    def get(self, request):
        count = Notification.objects.filter(
            user=request.user,
            is_read=False,
        ).count()
        return JsonResponse({'success': True, 'count': count})


# ===========================================================================
# MARK AS READ VIEWS
# ===========================================================================


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class MarkNotificationRead(View):
    """
    Mark a specific notification (or all unread) as read.

    **POST** body:
    - With ``notification_id``: marks that single notification
    - Without ``notification_id``: marks ALL unread notifications
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
            notif_id = data.get('notification_id')
            if notif_id:
                Notification.objects.filter(
                    id=notif_id, user=request.user,
                ).update(is_read=True)
            else:
                Notification.objects.filter(
                    user=request.user, is_read=False,
                ).update(is_read=True)
            return JsonResponse({
                'success': True,
                'message': 'Marked as read',
            })
        except Exception as e:
            return JsonResponse(
                {'success': False, 'error': str(e)},
                status=500,
            )


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class MarkAllNotificationsRead(View):
    """
    Mark every unread notification as read for the current user.

    Convenience endpoint for the "Mark All Read" button in the
    notification dropdown header and notifications page.
    """

    def post(self, request):
        try:
            count = Notification.objects.filter(
                user=request.user, is_read=False,
            ).update(is_read=True)
            return JsonResponse({
                'success': True,
                'message': f'{count} notifications marked as read',
                'count': count,
            })
        except Exception as e:
            return JsonResponse(
                {'success': False, 'error': str(e)},
                status=500,
            )


# ===========================================================================
# DELETE VIEWS
# ===========================================================================


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class DeleteNotification(View):
    """
    Delete a single notification by ID (scoped to the current user).

    **POST** body: ``{ notification_id: 123 }``
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
            notif_id = data.get('notification_id')
            if notif_id:
                Notification.objects.filter(
                    id=notif_id, user=request.user,
                ).delete()
            return JsonResponse({
                'success': True,
                'message': 'Notification deleted',
            })
        except Exception as e:
            return JsonResponse(
                {'success': False, 'error': str(e)},
                status=500,
            )


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class DeleteAllNotifications(View):
    """
    Delete all notifications for the current user.

    Returns the count of deleted notifications for confirmation.
    """

    def post(self, request):
        try:
            count = Notification.objects.filter(
                user=request.user,
            ).count()
            Notification.objects.filter(user=request.user).delete()
            return JsonResponse({
                'success': True,
                'message': f'{count} notifications deleted',
            })
        except Exception as e:
            return JsonResponse(
                {'success': False, 'error': str(e)},
                status=500,
            )
