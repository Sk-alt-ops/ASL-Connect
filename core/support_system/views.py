"""
Support Ticket Views — Create (Text/Video), List, Detail, Delete

Provides AJAX endpoints for the ASL and normal user dashboards to
manage help/support tickets.

Key workflows:
1. Text ticket: User describes the issue in text
2. Video ticket: User records an ASL video explaining the issue
3. Staff respond via ``admin_dashboard`` (text and/or video)
4. Users view ticket status and responses in real-time

Staff notifications are automatically sent on ticket creation.
"""

import json
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from .models import SupportTicket
from core.notifications.views import notify_staff_users, create_notification
from core.helpers import timesince


# ===========================================================================
# TICKET CREATION
# ===========================================================================


@login_required
@csrf_exempt
def create_ticket(request):
    """
    Create a text-based support ticket and notify staff.

    Automatically determines ticket type (asl/normal) from the user's
    ``is_asl_user`` flag.

    **POST** body: ``{ issue_description, subject? }``
    """
    if request.method != 'POST':
        return JsonResponse(
            {'success': False, 'error': 'POST required'},
            status=405,
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        try:
            data = request.POST.dict()
        except Exception:
            return JsonResponse(
                {'success': False, 'error': 'Invalid request'},
                status=400,
            )

    issue_description = data.get('issue_description', '').strip()
    if not issue_description:
        return JsonResponse(
            {'success': False, 'error': 'Issue description is required.'},
            status=400,
        )

    subject = data.get('subject', '').strip()
    is_asl = request.user.is_asl_user

    ticket = SupportTicket.objects.create(
        user=request.user,
        ticket_type='asl' if is_asl else 'normal',
        subject=subject,
        issue_description=issue_description,
        status='open',
    )

    notify_staff_users(
        type='support_request',
        title='New Support Request',
        message=(
            f'{request.user.username} has submitted a support request: '
            f'{subject or "No subject"}'
        ),
        link=f'/admin-panel/api/support-tickets/{ticket.id}/',
    )

    return JsonResponse({
        'success': True,
        'ticket': {
            'id': ticket.id,
            'ticket_type': ticket.ticket_type,
            'subject': ticket.subject,
            'issue_description': ticket.issue_description,
            'status': ticket.status,
            'created_at': ticket.created_at.isoformat(),
        },
    })


@login_required
@csrf_exempt
def create_ticket_with_video(request):
    """
    Create a support ticket with an attached ASL video recording.

    Used by ASL users who prefer to explain their issue in sign language.
    The video file is uploaded as multipart form data.

    **POST** (multipart): ``video`` (file), ``subject?``,
    ``issue_description?``
    """
    if request.method != 'POST':
        return JsonResponse(
            {'success': False, 'error': 'POST required'},
            status=405,
        )

    video = request.FILES.get('video')
    subject = request.POST.get('subject', '').strip()
    issue_description = (
        request.POST.get('issue_description', '').strip()
        or subject
        or ''
    )

    if not issue_description and not video:
        return JsonResponse({
            'success': False,
            'error': 'Please provide a description or record a video.',
        }, status=400)

    ticket = SupportTicket.objects.create(
        user=request.user,
        ticket_type='asl',
        subject=subject,
        issue_description=issue_description or 'Video help request',
        video=video,
        status='open',
    )

    notify_staff_users(
        type='support_request',
        title='New Support Request with Video',
        message=(
            f'{request.user.username} has submitted a video support '
            f'request: {subject or "No subject"}'
        ),
        link=f'/admin-panel/api/support-tickets/{ticket.id}/',
    )

    return JsonResponse({
        'success': True,
        'ticket': {
            'id': ticket.id,
            'ticket_type': ticket.ticket_type,
            'subject': ticket.subject,
            'issue_description': ticket.issue_description,
            'video_url': ticket.video.url if ticket.video else None,
            'status': ticket.status,
            'created_at': ticket.created_at.isoformat(),
        },
    })


# ===========================================================================
# TICKET LISTING & DETAIL
# ===========================================================================


@login_required
def list_tickets(request):
    """
    List all support tickets for the current user, most recent first.

    Returns ticket data including admin responses and video URLs
    for rendering in the Help & Support page.
    """
    tickets = SupportTicket.objects.filter(
        user=request.user,
    ).order_by('-created_at')

    return JsonResponse({
        'success': True,
        'tickets': [
            {
                'id': t.id,
                'ticket_type': t.ticket_type,
                'subject': t.subject,
                'issue_description': t.issue_description,
                'video_url': t.video.url if t.video else None,
                'status': t.status,
                'admin_response_text': t.admin_response_text or '',
                'admin_response_video_url': (
                    t.admin_response_video.url
                    if t.admin_response_video else None
                ),
                'responded_at': (
                    t.responded_at.isoformat()
                    if t.responded_at else None
                ),
                'created_at': t.created_at.isoformat(),
                'created_at_human': timesince(t.created_at),
            }
            for t in tickets
        ],
    })


@login_required
def ticket_detail(request, ticket_id):
    """
    Get full details of a specific support ticket (owner-only access).

    Uses ``user=request.user`` to ensure users can only view their own tickets.
    """
    ticket = get_object_or_404(
        SupportTicket, id=ticket_id, user=request.user,
    )
    return JsonResponse({
        'success': True,
        'ticket': {
            'id': ticket.id,
            'ticket_type': ticket.ticket_type,
            'subject': ticket.subject,
            'issue_description': ticket.issue_description,
            'video_url': ticket.video.url if ticket.video else None,
            'status': ticket.status,
            'admin_response_text': ticket.admin_response_text or '',
            'admin_response_video_url': (
                ticket.admin_response_video.url
                if ticket.admin_response_video else None
            ),
            'responded_at': (
                ticket.responded_at.isoformat()
                if ticket.responded_at else None
            ),
            'created_at': ticket.created_at.isoformat(),
            'created_at_human': timesince(ticket.created_at),
        },
    })


# ===========================================================================
# TICKET DELETION
# ===========================================================================


@login_required
@csrf_exempt
def delete_ticket(request, ticket_id):
    """
    Delete a support ticket and its associated video files (owner-only).

    Cleans up uploaded video files before deleting the database record
    to prevent orphaned media.
    """
    if request.method != 'POST':
        return JsonResponse(
            {'success': False, 'error': 'POST required'},
            status=405,
        )

    ticket = get_object_or_404(
        SupportTicket, id=ticket_id, user=request.user,
    )

    if ticket.video:
        ticket.video.delete(save=False)
    if ticket.admin_response_video:
        ticket.admin_response_video.delete(save=False)

    ticket.delete()

    return JsonResponse({
        'success': True,
        'message': 'Ticket deleted.',
    })
