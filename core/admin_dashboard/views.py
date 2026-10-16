"""
Views -- Admin Dashboard
==========================
API endpoints for the admin panel.

Covers:
  - Dashboard statistics and recent activity
  - User management (list + search)
  - Contact message inbox (list, reply, mark-read)
  - Support tickets (list, respond, change status)
  - Design settings CRUD (global singleton)
  - Page design CRUD (per-page overrides)
  - Section design CRUD (per-section overrides on landing page)

All views are restricted to superusers/staff members via the
:func:`~services.admin_required` decorator.
"""

import json
import os
import uuid

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from core.categories.models import ASLSymbol, Gesture
from core.landing.models import ContactMessage
from core.notifications.views import create_notification
from core.support_system.models import SupportTicket
from core.users.models import User

from .helpers import timesince
from .models import SECTION_DEFAULTS, DesignSettings, PageDesign, SectionDesign
from .services import (
    IMAGE_FIELDS,
    VALID_TICKET_STATUSES,
    admin_required,
    parse_json_body,
    require_post,
    respond_to_asl_ticket,
    respond_to_normal_ticket,
    serialize_design_settings,
    sync_section_to_design_settings,
    update_design_settings_from_data,
    validate_ticket_status,
)


# ===========================================================================
# VIEW: Admin Panel Main Page
# ===========================================================================

@login_required
def admin_panel(request):
    """Render the main admin panel single-page application."""
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect('/')
    return render(request, 'admin_dashboard/admin_panel.html')


# ===========================================================================
# API: Dashboard Statistics
# ===========================================================================

@login_required
@admin_required
def dashboard_stats(request):
    """Return real-time platform statistics for the dashboard overview.

    Aggregates counts for users, gestures, symbols, support tickets,
    and contact messages.  All counts are simple ``COUNT`` queries.
    """
    return JsonResponse({
        'success': True,
        'stats': {
            'total_users': User.objects.count(),
            'asl_users': User.objects.filter(is_asl_user=True).count(),
            'gestures': Gesture.objects.count(),
            'symbols': ASLSymbol.objects.count(),
            'open_tickets': SupportTicket.objects.filter(status='open').count(),
            'contact_messages': ContactMessage.objects.count(),
        },
    })


# ===========================================================================
# API: Dashboard Recent Activity
# ===========================================================================

@login_required
@admin_required
def dashboard_recent_activity(request):
    """Return recent platform activity (users, gestures, messages, tickets).

    Queries the last 5 records from each source, then merges and sorts
    them by recency (limited to 10 total).  Uses ``select_related`` on
    FK relationships to avoid N+1 queries.
    """
    activities = []

    # Recent user registrations (no FK to prefetch)
    for u in User.objects.order_by('-date_joined')[:5]:
        activities.append({
            'type': 'user_registered',
            'description': f'New user registered: {u.username}',
            'icon': 'ti ti-user-plus',
            'color': 'var(--purple)',
            'bg': 'var(--purple-bg)',
            'time': timesince(u.date_joined),
        })

    # Recent gesture uploads (FK -> category)
    for g in Gesture.objects.select_related('category').order_by('-created_at')[:5]:
        activities.append({
            'type': 'gesture_uploaded',
            'description': f'New gesture uploaded: {g.title}',
            'icon': 'ti ti-upload',
            'color': 'var(--green)',
            'bg': 'var(--green-bg)',
            'time': timesince(g.created_at),
        })

    # Recent contact messages (no FK)
    for m in ContactMessage.objects.order_by('-created_at')[:5]:
        activities.append({
            'type': 'contact_message',
            'description': f'Contact message from {m.name}: {m.subject or "(no subject)"}',
            'icon': 'ti ti-mail',
            'color': 'var(--teal)',
            'bg': 'var(--teal-bg)',
            'time': timesince(m.created_at),
        })

    # Recent support tickets (FK -> user)
    for t in SupportTicket.objects.select_related('user').order_by('-created_at')[:5]:
        desc = t.subject or t.issue_description[:50]
        activities.append({
            'type': 'support_ticket',
            'description': f'Support ticket from {t.user.username}: {desc}',
            'icon': 'ti ti-headset',
            'color': 'var(--blue)',
            'bg': 'var(--blue-bg)',
            'time': timesince(t.created_at),
        })

    # Sort by recency (timesince is orderable as "Just now" < "1m ago" < ...)
    # but timesince strings are not truly sortable.  We keep the original
    # query ordering and just limit to 10.
    activities.sort(key=lambda x: x['time'])
    activities = activities[:10]

    return JsonResponse({'success': True, 'activities': activities})


# ===========================================================================
# API: User List (with search)
# ===========================================================================

@login_required
@admin_required
def users_list(request):
    """Return all users, optionally filtered by search query and type.

    Query params:
        search  (str)  -- free-text across username, email, first_name, last_name.
        type    (str)  -- ``all`` | ``asl`` | ``normal`` | ``admin`` (default: all).
    Results are ordered by most-recently-joined.
    """
    search = request.GET.get('search', '').strip()
    user_type = request.GET.get('type', 'all').strip()
    users = User.objects.all().order_by('-date_joined')

    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(id__icontains=search)
        )

    if user_type == 'asl':
        users = users.filter(is_asl_user=True)
    elif user_type == 'normal':
        users = users.filter(is_asl_user=False, is_superuser=False)
    elif user_type == 'admin':
        users = users.filter(is_superuser=True)

    user_data = [
        {
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'full_name': u.get_full_name() or u.username,
            'is_asl_user': u.is_asl_user,
            'is_superuser': u.is_superuser,
            'is_staff': u.is_staff,
            'is_active': u.is_active,
            'date_joined': u.date_joined.strftime('%d/%m/%Y'),
            'date_joined_human': timesince(u.date_joined),
        }
        for u in users
    ]

    return JsonResponse({
        'success': True,
        'users': user_data,
        'total': len(user_data),
    })


@login_required
@admin_required
def user_detail(request, user_id):
    """Return full details for a single user."""
    u = get_object_or_404(User, id=user_id)
    return JsonResponse({
        'success': True,
        'user': {
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'full_name': u.get_full_name() or u.username,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'is_asl_user': u.is_asl_user,
            'is_superuser': u.is_superuser,
            'is_staff': u.is_staff,
            'is_active': u.is_active,
            'date_joined': u.date_joined.strftime('%d/%m/%Y'),
            'date_joined_human': timesince(u.date_joined),
            'profile_picture_url': u.profile_picture.url if u.profile_picture else None,
        },
    })


# ===========================================================================
# API: Contact Messages
# ===========================================================================

@login_required
@admin_required
def contact_messages_list(request):
    """Return contact messages with optional search and status filtering.

    Query params:
        search  (str)  -- free-text across name, email, subject, message.
        status  (str)  -- ``unread`` | ``read`` | ``replied`` (empty = all).
    """
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()

    messages = ContactMessage.objects.all()

    if search:
        messages = messages.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(subject__icontains=search) |
            Q(message__icontains=search)
        )
    if status_filter == 'unread':
        messages = messages.filter(is_read=False)
    elif status_filter == 'read':
        messages = messages.filter(is_read=True)
    elif status_filter == 'replied':
        messages = messages.exclude(replied_at__isnull=True)

    messages = messages[:50]

    return JsonResponse({
        'success': True,
        'messages': [
            {
                'id': m.id,
                'name': m.name,
                'email': m.email,
                'subject': m.subject,
                'message': m.message,
                'is_read': m.is_read,
                'is_replied': m.replied_at is not None,
                'reply_message': m.reply_message or '',
                'replied_at': (
                    m.replied_at.strftime('%Y-%m-%d %H:%M:%S')
                    if m.replied_at else None
                ),
                'created_at': m.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'created_at_human': timesince(m.created_at),
            }
            for m in messages
        ],
        'total': messages.count(),
        'unread': ContactMessage.objects.filter(is_read=False).count(),
    })


@login_required
@admin_required
@csrf_exempt
@require_post
@parse_json_body
def contact_message_reply(request, message_id):
    """Reply to a contact message (admin-only)."""
    message = get_object_or_404(ContactMessage, id=message_id)
    reply = request.json_data.get('reply', '').strip()
    if not reply:
        return JsonResponse(
            {'success': False, 'error': 'Reply message is required.'},
            status=400,
        )

    message.reply_message = reply
    message.replied_at = timezone.now()
    message.is_read = True
    message.save()
    return JsonResponse({'success': True, 'message': 'Reply sent successfully.'})


@login_required
@admin_required
@csrf_exempt
@require_post
def contact_message_mark_read(request, message_id):
    """Mark a contact message as read."""
    message = get_object_or_404(ContactMessage, id=message_id)
    message.is_read = True
    message.save()
    return JsonResponse({'success': True})


# ===========================================================================
# API: Global Design Settings
# ===========================================================================

@login_required
@admin_required
def design_settings_get(request):
    """Return all global design settings as a flat JSON object."""
    ds = DesignSettings.get_settings()
    return JsonResponse({
        'success': True,
        'settings': serialize_design_settings(ds),
    })


@login_required
@admin_required
@csrf_exempt
@require_post
def design_settings_update(request):
    """Update global design settings.

    Accepts both:
      - ``multipart/form-data`` (for file uploads)
      - ``application/json``   (for text/json fields only)
    """
    ds = DesignSettings.get_settings()

    # Handle multipart form data (file uploads).
    content_type = request.content_type or ''
    if 'multipart/form-data' in content_type:
        data = request.POST.dict()
        # Include uploaded files.
        for img_field in IMAGE_FIELDS:
            if img_field in request.FILES:
                data[img_field] = request.FILES[img_field]
        update_design_settings_from_data(ds, data)
        ds.save()
        return JsonResponse({
            'success': True,
            'message': 'Design settings updated!',
        })

    # Handle JSON body.
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {'success': False, 'error': 'Invalid JSON'}, status=400
        )

    update_design_settings_from_data(ds, data)
    ds.save()
    return JsonResponse({
        'success': True,
        'message': 'Design settings updated!',
    })


# ===========================================================================
# API: Support Tickets
# ===========================================================================

@login_required
@admin_required
def support_tickets_list(request):
    """Return support tickets with optional search/status/type filtering.

    Uses ``select_related('user')`` to avoid N+1 on the user FK.
    """
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    type_filter = request.GET.get('type', '').strip()

    tickets = SupportTicket.objects.select_related('user').order_by('-created_at')

    if search:
        tickets = tickets.filter(
            Q(issue_description__icontains=search) |
            Q(subject__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search)
        )
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if type_filter:
        tickets = tickets.filter(ticket_type=type_filter)

    return JsonResponse({
        'success': True,
        'tickets': [
            {
                'id': t.id,
                'user': {
                    'id': t.user.id,
                    'username': t.user.username,
                    'email': t.user.email,
                    'full_name': t.user.get_full_name() or t.user.username,
                    'is_asl_user': t.user.is_asl_user,
                },
                'ticket_type': t.ticket_type,
                'subject': t.subject,
                'issue_description': t.issue_description,
                'video_url': t.video.url if t.video else None,
                'status': t.status,
                'admin_response_text': t.admin_response_text or '',
                'admin_response_video_url': (
                    t.admin_response_video.url if t.admin_response_video else None
                ),
                'responded_at': (
                    t.responded_at.isoformat() if t.responded_at else None
                ),
                'created_at': t.created_at.isoformat(),
                'created_at_human': timesince(t.created_at),
            }
            for t in tickets
        ],
        'total': tickets.count(),
        'stats': {
            'open': SupportTicket.objects.filter(status='open').count(),
            'in_progress': SupportTicket.objects.filter(
                status='in_progress'
            ).count(),
            'resolved': SupportTicket.objects.filter(status='resolved').count(),
            'closed': SupportTicket.objects.filter(status='closed').count(),
            'asl': SupportTicket.objects.filter(ticket_type='asl').count(),
            'normal': SupportTicket.objects.filter(ticket_type='normal').count(),
        },
    })


@login_required
@admin_required
@csrf_exempt
def support_ticket_respond(request, ticket_id):
    """Respond to a support ticket.

    - ASL tickets    : require a video response (multipart).
    - Normal tickets : accept a text response (JSON).
    """
    ticket = get_object_or_404(SupportTicket, id=ticket_id)

    if ticket.ticket_type == 'asl':
        ticket, error = respond_to_asl_ticket(
            ticket, request.FILES, request.POST
        )
        if error:
            return JsonResponse(
                {'success': False, 'error': error}, status=400
            )
        create_notification(
            user=ticket.user,
            type='support_response',
            title='Admin Responded to Your Request',
            message='Admin replied with a video to your support request.',
            link='/support/list/',
        )
        return JsonResponse({
            'success': True,
            'message': 'Video response sent successfully.',
            'ticket': {
                'id': ticket.id,
                'status': ticket.status,
                'admin_response_video_url': (
                    ticket.admin_response_video.url
                    if ticket.admin_response_video else None
                ),
            },
        })

    # Normal ticket: expect JSON with response_text.
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {'success': False, 'error': 'Invalid JSON'}, status=400
        )

    response_text = data.get('response_text', '').strip()
    ticket, error = respond_to_normal_ticket(
        ticket, response_text, data.get('status', 'in_progress')
    )
    if error:
        return JsonResponse(
            {'success': False, 'error': error}, status=400
        )

    create_notification(
        user=ticket.user,
        type='support_response',
        title='Admin Responded to Your Request',
        message='Admin replied to your support request.',
        link='/support/list/',
    )
    return JsonResponse({
        'success': True,
        'message': 'Response sent successfully.',
        'ticket': {'id': ticket.id, 'status': ticket.status},
    })


@login_required
@admin_required
@csrf_exempt
@require_post
@parse_json_body
def support_ticket_status(request, ticket_id):
    """Update a support ticket's status (open/in_progress/resolved/closed)."""
    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    new_status = request.json_data.get('status', '').strip()

    if not validate_ticket_status(new_status):
        valid = ', '.join(VALID_TICKET_STATUSES)
        return JsonResponse({
            'success': False,
            'error': f'Invalid status. Must be one of: {valid}',
        }, status=400)

    ticket.status = new_status
    ticket.save()
    return JsonResponse({
        'success': True,
        'message': f'Ticket status updated to {new_status}.',
    })


# ===========================================================================
# API: Page Design Management
# ===========================================================================

@login_required
@admin_required
def page_design_list(request):
    """Return all page designs with their publish/global status."""
    PageDesign.get_or_create_defaults()
    pages = PageDesign.objects.all()
    return JsonResponse({
        'success': True,
        'pages': [
            {
                'page_name': p.page_name,
                'label': p.label,
                'is_published': p.is_published,
                'apply_globally': p.apply_globally,
                'is_default': p.is_default,
                'updated_at': p.updated_at.isoformat(),
            }
            for p in pages
        ],
    })


@login_required
@admin_required
def page_design_get(request, page_name):
    """Return a single page design with its merged settings."""
    PageDesign.get_or_create_defaults()
    page = get_object_or_404(PageDesign, page_name=page_name)
    return JsonResponse({
        'success': True,
        'page': {
            'page_name': page.page_name,
            'label': page.label,
            'settings': page.get_settings(),
            'apply_globally': page.apply_globally,
            'is_published': page.is_published,
            'is_default': page.is_default,
            'updated_at': page.updated_at.isoformat(),
        },
    })


@login_required
@admin_required
@csrf_exempt
@require_post
def page_design_save(request, page_name):
    """Save a page design's settings.

    If ``apply_globally`` is ``True``, the settings are copied to every
    other page design.
    """
    PageDesign.get_or_create_defaults()
    page = get_object_or_404(PageDesign, page_name=page_name)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {'success': False, 'error': 'Invalid JSON'}, status=400
        )

    if 'settings' in data:
        page.settings = data['settings']
    if 'apply_globally' in data:
        page.apply_globally = data['apply_globally']
    page.save()

    # Propagate to all other pages when global apply is on.
    if page.apply_globally:
        for other in PageDesign.objects.exclude(page_name=page_name):
            other.settings = page.settings
            other.save()

    return JsonResponse({
        'success': True,
        'message': 'Design settings saved!',
    })


@login_required
@admin_required
@csrf_exempt
@require_post
def page_design_publish(request, page_name):
    """Publish (make live) a page design."""
    page = get_object_or_404(PageDesign, page_name=page_name)
    page.is_published = True
    page.save()
    return JsonResponse({
        'success': True,
        'message': 'Design published!',
    })


@login_required
@admin_required
@csrf_exempt
@require_post
def page_design_reset(request, page_name):
    """Reset a page design back to default settings."""
    page = get_object_or_404(PageDesign, page_name=page_name)
    page.settings = {}
    page.is_published = False
    page.save()
    return JsonResponse({
        'success': True,
        'message': 'Design reset to defaults!',
    })


# ===========================================================================
# API: Section Design Management
# ===========================================================================

@login_required
@admin_required
def section_design_list(request):
    """Return all sections for a given page with visibility status."""
    page = request.GET.get('page', 'landing')
    SectionDesign.get_or_create_defaults(page)
    sections = SectionDesign.objects.filter(page_name=page)
    return JsonResponse({
        'success': True,
        'sections': [
            {
                'section_name': s.section_name,
                'label': s.label,
                'is_visible': s.is_visible,
                'updated_at': s.updated_at.isoformat(),
            }
            for s in sections
        ],
    })


@login_required
@admin_required
def section_design_get(request, section_name):
    """Return a single section design with merged settings and defaults."""
    page = request.GET.get('page', 'landing')
    SectionDesign.get_or_create_defaults(page)
    section = get_object_or_404(
        SectionDesign, page_name=page, section_name=section_name
    )
    return JsonResponse({
        'success': True,
        'section': {
            'section_name': section.section_name,
            'label': section.label,
            'is_visible': section.is_visible,
            'settings': section.get_settings(),
            'defaults': (
                SECTION_DEFAULTS.get(section_name, {}).get('settings', {})
            ),
            'updated_at': section.updated_at.isoformat(),
        },
    })


@login_required
@admin_required
@csrf_exempt
@require_post
def section_design_save(request, section_name):
    """Save a section design's settings (supports JSON + multipart)."""
    page = request.GET.get('page', 'landing')
    SectionDesign.get_or_create_defaults(page)
    section = get_object_or_404(
        SectionDesign, page_name=page, section_name=section_name
    )

    # Handle multipart form data (file uploads for section images/videos).
    content_type = request.content_type or ''
    if 'multipart/form-data' in content_type:
        try:
            settings = json.loads(request.POST.get('settings', '{}'))
        except json.JSONDecodeError:
            settings = {}

        for key in request.FILES:
            settings[key] = '__upload__'
            section.save_upload(request.FILES[key], key)

        section.settings = settings
        if 'is_visible' in request.POST:
            section.is_visible = request.POST['is_visible'] == 'true'
        section.save()
        sync_section_to_design_settings(page, section_name, settings)
        return JsonResponse({
            'success': True,
            'message': 'Section settings saved!',
        })

    # Handle JSON body.
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {'success': False, 'error': 'Invalid JSON'}, status=400
        )

    if 'settings' in data:
        current = section.get_settings()
        current.update(data['settings'])
        section.settings = current
    if 'is_visible' in data:
        section.is_visible = data['is_visible']
    section.save()
    sync_section_to_design_settings(page, section_name, section.settings)
    return JsonResponse({
        'success': True,
        'message': 'Section settings saved!',
    })


@login_required
@admin_required
@csrf_exempt
@require_post
def section_design_reset(request, section_name):
    """Reset a section's design back to default settings."""
    page = request.GET.get('page', 'landing')
    section = get_object_or_404(
        SectionDesign, page_name=page, section_name=section_name
    )
    section.settings = {}
    section.is_visible = True
    section.save()
    return JsonResponse({
        'success': True,
        'message': 'Section reset to defaults!',
    })


# ===========================================================================
# API: File Upload for Sections
# ===========================================================================

@login_required
@admin_required
@csrf_exempt
def section_upload_file(request):
    """Upload a file (image/video) for a section design setting.

    Expects ``multipart/form-data`` with a ``file`` field.
    Returns the URL of the saved file.
    """
    if request.method != 'POST' or 'file' not in request.FILES:
        return JsonResponse({
            'success': False,
            'error': 'No file uploaded',
        }, status=400)

    file = request.FILES['file']
    ext = os.path.splitext(file.name)[1] if '.' in file.name else ''
    filename = f'section_{uuid.uuid4().hex[:12]}{ext}'
    path = default_storage.save(f'design/{filename}', file)
    url = settings.MEDIA_URL + path
    return JsonResponse({
        'success': True,
        'url': url,
        'filename': filename,
    })
