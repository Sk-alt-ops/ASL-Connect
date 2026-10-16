"""
Chat REST API Views — Send, Fetch, Delete, Copy, Mark Read, Chat List

Provides JSON API endpoints for all chat functionality:

- ``SendMessage``:     Create a new message (text / ASL / gesture)
- ``GetMessages``:     Retrieve full message history with a friend
- ``DeleteMessage``:   Soft-delete one of your own messages
- ``CopyMessage``:     Fetch a message's raw content (must be participant)
- ``MarkAsRead``:      Mark all unread messages from a sender as read
- ``GetChatList``:     Build a sorted conversation list with previews
- ``GetUnreadCounts``: Per-sender unread counts for badge display

Every view requires an authenticated user.
"""

import json

from django.db.models import Q, OuterRef, Subquery, Count, IntegerField
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone

from .models import Message
from core.users.models import User
from core.friends.models import FriendRequest

# =============================================================================
# Decorator presets for readability
# =============================================================================

ajax_view = [
    csrf_exempt,
    login_required,
]

auth_view = [
    login_required,
]


# =============================================================================
# SendMessage — Create a new chat message
# =============================================================================

@method_decorator(ajax_view, name='dispatch')
class SendMessage(View):
    """
    POST /chat/api/send/

    Create a new message addressed to another user.

    Request body:
        receiver_id  (int)   — Required. Target user's ID.
        content      (str)   — Text body (required for text-type messages).
        message_type (str)   — One of ``text``, ``asl``, ``gesture``.
        asl_content  (list)  — ASL symbol array for asl-type messages.
        gesture_id   (int)   — Gesture FK for gesture-type messages.

    Response:
        201 — ``{success: true, msg: {...}}``
        400 — Missing receiver_id
        404 — Receiver not found
        500 — Unexpected error
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
            receiver_id = data.get('receiver_id')
            content = data.get('content', '')
            message_type = data.get('message_type', 'text')
            asl_content = data.get('asl_content')
            gesture_id = data.get('gesture_id')

            if not receiver_id:
                return JsonResponse(
                    {'success': False, 'error': 'receiver_id required'}, status=400
                )

            if message_type == 'text' and not content and not asl_content and not gesture_id:
                return JsonResponse(
                    {'success': False, 'error': 'content required'}, status=400
                )

            try:
                receiver = User.objects.get(id=receiver_id)
            except User.DoesNotExist:
                return JsonResponse(
                    {'success': False, 'error': 'Receiver not found'}, status=404
                )

            msg = Message.objects.create(
                sender=request.user,
                receiver=receiver,
                content=content,
                message_type=message_type,
                asl_content=asl_content,
                gesture_id=gesture_id,
            )

            return JsonResponse({
                'success': True,
                'message': 'Message sent',
                'msg': msg.to_dict(request.user),
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =============================================================================
# GetMessages — Retrieve full conversation history with a friend
# =============================================================================

@method_decorator(auth_view, name='dispatch')
class GetMessages(View):
    """
    GET /chat/api/messages/?friend_id=<id>

    Return all messages exchanged between the current user and a friend,
    ordered chronologically.

    Query parameters:
        friend_id (int) — Required. The other participant's user ID.

    Response:
        200 — ``{success: true, messages: [...]}``
        400 — Missing friend_id
    """

    def get(self, request):
        friend_id = request.GET.get('friend_id')
        if not friend_id:
            return JsonResponse(
                {'success': False, 'error': 'friend_id required'}, status=400
            )

        messages = Message.objects.filter(
            Q(sender=request.user, receiver_id=friend_id) |
            Q(sender_id=friend_id, receiver=request.user)
        ).select_related('sender', 'receiver', 'gesture')

        return JsonResponse({
            'success': True,
            'messages': [msg.to_dict(request.user) for msg in messages],
        })


# =============================================================================
# DeleteMessage — Remove one of your own messages
# =============================================================================

@method_decorator(ajax_view, name='dispatch')
class DeleteMessage(View):
    """
    POST /chat/api/delete/

    Permanently delete a message that the current user sent.

    Request body:
        message_id (int) — The message to delete.

    Response:
        200 — ``{success: true}``
        404 — Message not found or not owned by user
        500 — Unexpected error
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
            message_id = data.get('message_id')

            msg = Message.objects.get(id=message_id, sender=request.user)
            msg.delete()

            return JsonResponse({'success': True, 'message': 'Message deleted'})

        except Message.DoesNotExist:
            return JsonResponse(
                {'success': False, 'error': 'Message not found'}, status=404
            )
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =============================================================================
# CopyMessage — Retrieve raw message content (for clipboard copy)
# =============================================================================

@method_decorator(ajax_view, name='dispatch')
class CopyMessage(View):
    """
    POST /chat/api/copy/

    Fetch the raw content of a message.  Both the sender and the receiver
    are allowed to copy.

    Request body:
        message_id (int) — The message whose content to retrieve.

    Response:
        200 — ``{success: true, content: '...', message_type: 'text'}``
        403 — Current user is not a participant
        404 — Message not found
        500 — Unexpected error
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
            message_id = data.get('message_id')

            msg = Message.objects.get(id=message_id)
            if msg.sender != request.user and msg.receiver != request.user:
                return JsonResponse(
                    {'success': False, 'error': 'Unauthorized'}, status=403
                )

            return JsonResponse({
                'success': True,
                'content': msg.content,
                'message_type': msg.message_type,
            })

        except Message.DoesNotExist:
            return JsonResponse(
                {'success': False, 'error': 'Message not found'}, status=404
            )
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =============================================================================
# MarkAsRead — Mark all messages from a sender as read
# =============================================================================

@method_decorator(ajax_view, name='dispatch')
class MarkAsRead(View):
    """
    POST /chat/api/mark-read/

    Mark all unread messages from a specific sender as read, recording
    the timestamp.

    Request body:
        sender_id (int) — The user whose messages to mark read.

    Response:
        200 — ``{success: true, count: <int>}``
        400 — Missing sender_id
        500 — Unexpected error
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
            sender_id = data.get('sender_id')

            if not sender_id:
                return JsonResponse(
                    {'success': False, 'error': 'sender_id required'}, status=400
                )

            messages = Message.objects.filter(
                sender_id=sender_id,
                receiver=request.user,
                is_read=False,
            )

            count = messages.count()
            messages.update(is_read=True, read_at=timezone.now())

            return JsonResponse({
                'success': True,
                'message': f'{count} messages marked as read',
                'count': count,
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =============================================================================
# GetChatList — Build sorted conversation list with last-message preview
# =============================================================================

@method_decorator(auth_view, name='dispatch')
class GetChatList(View):
    """
    GET /chat/api/chat-list/

    Return all conversations the current user is part of, sorted by
    most-recent activity.  Each entry includes the last message preview
    and the unread count for that conversation.

    Response:
        200 — ``{success: true, chats: [...]}``
    """

    def get(self, request):
        # --- Latest message between current user and each candidate ---
        last_message = Message.objects.filter(
            Q(sender=request.user, receiver=OuterRef('id')) |
            Q(receiver=request.user, sender=OuterRef('id'))
        ).order_by('-timestamp')

        # --- Accepted friends ---
        friend_relations = FriendRequest.objects.filter(
            Q(from_user=request.user) | Q(to_user=request.user),
            status=FriendRequest.ACCEPTED,
        )
        friend_ids = set()
        for fr in friend_relations:
            friend_ids.add(fr.from_user_id)
            friend_ids.add(fr.to_user_id)
        friend_ids.discard(request.user.id)

        # --- Unread count subquery (avoids N+1 in the loop below) ---
        unread_subquery = Message.objects.filter(
            sender=OuterRef('id'),
            receiver=request.user,
            is_read=False,
        ).order_by().values('sender_id').annotate(
            count=Count('id'),
        ).values('count')

        friends = User.objects.filter(
            Q(id__in=friend_ids) |
            Q(sent_messages__receiver=request.user) |
            Q(received_messages__sender=request.user)
        ).distinct().annotate(
            last_msg_content=Subquery(last_message.values('content')[:1]),
            last_msg_time=Subquery(last_message.values('timestamp')[:1]),
            last_msg_type=Subquery(last_message.values('message_type')[:1]),
            last_msg_sender=Subquery(last_message.values('sender_id')[:1]),
            last_msg_is_read=Subquery(last_message.values('is_read')[:1]),
            unread_count=Subquery(unread_subquery, output_field=IntegerField()),
        )

        chat_list = []
        for f in friends:
            chat_list.append({
                'id': f.id,
                'username': f.username,
                'full_name': f.get_full_name() or f.username,
                'is_asl_user': f.is_asl_user,
                'profile_picture_url': (
                    f.profile_picture.url if f.profile_picture else None
                ),
                'last_message': {
                    'content': f.last_msg_content or '',
                    'type': f.last_msg_type or '',
                    'time': f.last_msg_time.isoformat() if f.last_msg_time else None,
                    'is_mine': f.last_msg_sender == request.user.id,
                    'is_read': (
                        f.last_msg_is_read
                        if f.last_msg_sender != request.user.id
                        else True
                    ),
                } if f.last_msg_time else None,
                'unread_count': f.unread_count or 0,
            })

        # Sort: conversations without messages last, then by time desc
        chat_list.sort(key=lambda x: (
            x['last_message'] is None,
            x['last_message']['time'] if x['last_message'] else '',
        ), reverse=True)

        return JsonResponse({'success': True, 'chats': chat_list})


# =============================================================================
# GetUnreadCounts — Per-sender unread counts for badge display
# =============================================================================

@method_decorator(auth_view, name='dispatch')
class GetUnreadCounts(View):
    """
    GET /chat/api/unread-counts/

    Return a map of ``{sender_id: count}`` for every user who has sent
    unread messages to the current user.  Used by the UI to display
    notification badges.

    Response:
        200 — ``{success: true, counts: {'1': 3, '5': 0}}``
    """

    def get(self, request):
        counts_qs = (
            Message.objects
            .filter(receiver=request.user, is_read=False)
            .values('sender_id')
            .annotate(count=Count('id'))
            .values('sender_id', 'count')
        )

        counts = {str(item['sender_id']): item['count'] for item in counts_qs}
        return JsonResponse({'success': True, 'counts': counts})
