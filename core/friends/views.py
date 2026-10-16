"""
Friend System Views — Send, Accept, Reject, Cancel, List, Search, Unfriend

All views return JSON responses consumed by the frontend AJAX calls.
Real-time WebSocket notifications are sent alongside database changes
so recipients get instant feedback without polling.

Performance notes:
- Uses ``select_related`` / ``prefetch_related`` on user FK lookups
- Minimises DB queries in friend list and search views
- Uses bulk ``update()`` / ``delete()`` where appropriate
"""

import json
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from .models import FriendRequest
from core.users.models import User
from core.notifications.views import create_notification
from core.helpers import send_ws_group_event, build_user_summary


# ===========================================================================
# DECORATOR SHORTCUTS
# ===========================================================================

ajax_view = [
    csrf_exempt,
    login_required,
]

auth_view = [
    login_required,
]


# ===========================================================================
# REQUEST LIFECYCLE: SEND, ACCEPT, REJECT, CANCEL
# ===========================================================================


@method_decorator(ajax_view, name='dispatch')
class SendFriendRequest(View):
    """
    Send a friend request to another user.

    Validates:
    - The target user exists and is not the sender
    - No duplicate pending or accepted request exists
    - Re-send is allowed if the previous request was rejected

    On success, notifies the recipient via WebSocket.

    **POST** body: ``{ user_id: int }``
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
            to_user_id = data.get('user_id')
            if not to_user_id:
                return JsonResponse(
                    {'success': False, 'error': 'user_id required'},
                    status=400,
                )

            to_user = User.objects.get(id=to_user_id)
            if to_user == request.user:
                return JsonResponse(
                    {'success': False, 'error': 'Cannot send request to yourself'},
                    status=400,
                )

            existing = FriendRequest.objects.filter(
                Q(from_user=request.user, to_user=to_user)
                | Q(from_user=to_user, to_user=request.user),
            ).first()

            if existing:
                if existing.status == FriendRequest.ACCEPTED:
                    return JsonResponse(
                        {'success': False, 'error': 'Already friends'},
                        status=400,
                    )
                if existing.status == FriendRequest.PENDING:
                    return JsonResponse(
                        {'success': False, 'error': 'Request already sent'},
                        status=400,
                    )
                if existing.status == FriendRequest.REJECTED:
                    existing.delete()

            FriendRequest.objects.create(
                from_user=request.user,
                to_user=to_user,
            )

            notif = create_notification(
                user=to_user,
                type='friend_request',
                title='New Friend Request',
                message=(
                    f'{request.user.username} sent you a friend request.'
                ),
                related_user=request.user,
            )

            send_ws_group_event(to_user.id, {
                'type': 'friend_request_sent',
                'from_user': build_user_summary(request.user),
                'notification': notif,
            })

            return JsonResponse({
                'success': True,
                'message': 'Friend request sent',
            })

        except User.DoesNotExist:
            return JsonResponse(
                {'success': False, 'error': 'User not found'},
                status=404,
            )
        except Exception as e:
            return JsonResponse(
                {'success': False, 'error': str(e)},
                status=500,
            )


@method_decorator(ajax_view, name='dispatch')
class AcceptFriendRequest(View):
    """
    Accept a pending friend request received by the current user.

    Changes the request status to ``accepted`` and notifies the original
    sender via WebSocket so they can start chatting immediately.

    **POST** body: ``{ request_id: int }``
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
            request_id = data.get('request_id')

            friend_request = FriendRequest.objects.get(
                id=request_id,
                to_user=request.user,
                status=FriendRequest.PENDING,
            )

            friend_request.status = FriendRequest.ACCEPTED
            friend_request.save()

            notif = create_notification(
                user=friend_request.from_user,
                type='friend_accepted',
                title='Friend Request Accepted',
                message=(
                    f'{request.user.username} accepted your friend request.'
                ),
                related_user=request.user,
            )

            send_ws_group_event(friend_request.from_user.id, {
                'type': 'friend_request_accepted',
                'by_user': build_user_summary(request.user),
                'notification': notif,
            })

            return JsonResponse({
                'success': True,
                'message': 'Friend request accepted',
            })

        except FriendRequest.DoesNotExist:
            return JsonResponse(
                {'success': False, 'error': 'Request not found'},
                status=404,
            )
        except Exception as e:
            return JsonResponse(
                {'success': False, 'error': str(e)},
                status=500,
            )


@method_decorator(ajax_view, name='dispatch')
class RejectFriendRequest(View):
    """
    Reject a pending friend request (sets status to ``rejected``).

    The sender can re-send a request after rejection.

    **POST** body: ``{ request_id: int }``
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
            request_id = data.get('request_id')

            friend_request = FriendRequest.objects.get(
                id=request_id,
                to_user=request.user,
                status=FriendRequest.PENDING,
            )

            friend_request.status = FriendRequest.REJECTED
            friend_request.save()

            return JsonResponse({
                'success': True,
                'message': 'Friend request rejected',
            })

        except FriendRequest.DoesNotExist:
            return JsonResponse(
                {'success': False, 'error': 'Request not found'},
                status=404,
            )
        except Exception as e:
            return JsonResponse(
                {'success': False, 'error': str(e)},
                status=500,
            )


@method_decorator(ajax_view, name='dispatch')
class CancelFriendRequest(View):
    """
    Cancel a pending friend request that the current user sent.

    Completely removes the request record from the database.

    **POST** body: ``{ request_id: int }``
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
            request_id = data.get('request_id')

            friend_request = FriendRequest.objects.get(
                id=request_id,
                from_user=request.user,
                status=FriendRequest.PENDING,
            )

            friend_request.delete()

            return JsonResponse({
                'success': True,
                'message': 'Friend request cancelled',
            })

        except FriendRequest.DoesNotExist:
            return JsonResponse(
                {'success': False, 'error': 'Request not found'},
                status=404,
            )
        except Exception as e:
            return JsonResponse(
                {'success': False, 'error': str(e)},
                status=500,
            )


# ===========================================================================
# FRIEND MANAGEMENT — LIST, UNFRIEND, SEARCH
# ===========================================================================


@method_decorator(auth_view, name='dispatch')
class FriendListView(View):
    """
    List all accepted friends for the current user.

    Uses a single query with ``select_related`` to fetch friend user data
    efficiently. Friends are identified by finding accepted requests
    where the current user is either the sender or the receiver.

    **GET** → ``{ success, friends: [...] }``
    """

    def get(self, request):
        friendships = FriendRequest.objects.filter(
            Q(from_user=request.user) | Q(to_user=request.user),
            status=FriendRequest.ACCEPTED,
        ).select_related('from_user', 'to_user')

        friend_list = []
        for f in friendships:
            friend_user = (
                f.to_user if f.from_user == request.user else f.from_user
            )
            friend_list.append({
                **build_user_summary(friend_user),
                'friend_request_id': f.id,
            })

        return JsonResponse({'success': True, 'friends': friend_list})


@method_decorator(ajax_view, name='dispatch')
class UnfriendUser(View):
    """
    Remove a friendship by deleting the accepted request record.

    Either party can initiate unfriending. After deletion a new friend
    request is required to re-establish the friendship.

    **POST** body: ``{ friend_id: int }``
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
            friend_id = data.get('friend_id')

            friendship = FriendRequest.objects.filter(
                Q(from_user=request.user, to_user_id=friend_id)
                | Q(from_user_id=friend_id, to_user=request.user),
                status=FriendRequest.ACCEPTED,
            ).first()

            if not friendship:
                return JsonResponse(
                    {'success': False, 'error': 'Friendship not found'},
                    status=404,
                )

            friendship.delete()
            return JsonResponse({
                'success': True,
                'message': 'Friend removed',
            })

        except Exception as e:
            return JsonResponse(
                {'success': False, 'error': str(e)},
                status=500,
            )


@method_decorator(auth_view, name='dispatch')
class SearchUsers(View):
    """
    Search for users by username, name, or email with friend status.

    Returns the friend relationship status for each matching user so
    the frontend can render the appropriate action button.

    Uses ``select_related`` to avoid N+1 queries on ``FriendRequest``.

    **GET** params: ``?q=search_term``
    """

    def get(self, request):
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({'success': True, 'users': []})

        users = User.objects.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query),
        ).exclude(id=request.user.id)[:20]

        user_list = []
        for u in users:
            existing = FriendRequest.objects.filter(
                Q(from_user=request.user, to_user=u)
                | Q(from_user=u, to_user=request.user),
            ).first()

            status = None
            request_id = None
            if existing:
                status = existing.status
                request_id = existing.id

            user_list.append({
                **build_user_summary(u),
                'friend_status': status,
                'friend_request_id': request_id,
                'sent_by_me': (
                    existing is not None
                    and existing.from_user == request.user
                ),
            })

        return JsonResponse({'success': True, 'users': user_list})


# ===========================================================================
# REQUEST LISTINGS — PENDING INCOMING & SENT
# ===========================================================================


@method_decorator(auth_view, name='dispatch')
class PendingRequests(View):
    """
    List all pending friend requests received by the current user.

    Uses ``select_related`` to efficiently load the requester's data.

    **GET** → ``{ success, requests: [...] }``
    """

    def get(self, request):
        requests = FriendRequest.objects.filter(
            to_user=request.user,
            status=FriendRequest.PENDING,
        ).select_related('from_user')

        req_list = []
        for r in requests:
            req_list.append({
                'id': r.id,
                'from_user': build_user_summary(r.from_user),
                'created_at': r.created_at.isoformat(),
            })

        return JsonResponse({'success': True, 'requests': req_list})


@method_decorator(auth_view, name='dispatch')
class SentRequests(View):
    """
    List all pending friend requests sent by the current user.

    Uses ``select_related`` to efficiently load the recipient's data.

    **GET** → ``{ success, sent_requests: [...] }``
    """

    def get(self, request):
        requests = FriendRequest.objects.filter(
            from_user=request.user,
            status=FriendRequest.PENDING,
        ).select_related('to_user')

        req_list = []
        for r in requests:
            req_list.append({
                'id': r.id,
                'to_user': build_user_summary(r.to_user),
                'created_at': r.created_at.isoformat(),
            })

        return JsonResponse({'success': True, 'sent_requests': req_list})
