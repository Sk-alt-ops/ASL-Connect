"""
Landing Page Views — Home Page, Contact Form, Dashboard Data API

Provides:
- ``index``: Renders the ASL Connect landing/home page
- ``contact_submit``: Handles AJAX contact form submissions with validation
- ``get_dashboard_data``: API endpoint returning user info and recent activity
"""

import json
import re
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import ContactMessage, UserActivity
from core.notifications.views import notify_staff_users
from core.helpers import timesince, sanitize_input


# ===========================================================================
# LANDING PAGE
# ===========================================================================


def index(request):
    """Render the ASL Connect landing page with user context."""
    context = {
        'title': 'ASL Connect — AI-Powered ASL Communication',
        'is_authenticated': request.user.is_authenticated,
    }
    if request.user.is_authenticated:
        user_name = request.user.get_full_name() or request.user.username
        context['user_name'] = user_name
        context['user_initials'] = user_name[0].upper()
    return render(request, 'landing.html', context)


# ===========================================================================
# CONTACT FORM
# ===========================================================================


@csrf_exempt
def contact_submit(request):
    """
    Handle contact form submission via AJAX.

    Validates name, email, subject, and message fields with
    server-side validation. On success, notifies all staff users
    via the notification system.

    **POST** body: ``{ name, email, subject, message }``
    """
    if request.method != 'POST':
        return JsonResponse(
            {'success': False, 'error': 'POST required'},
            status=405,
        )

    try:
        data = json.loads(request.body)
        name = sanitize_input(data.get('name', ''))
        email = data.get('email', '').strip()
        subject = sanitize_input(data.get('subject', ''))
        message = sanitize_input(data.get('message', ''))

        errors = {}

        # --- Name validation ---
        if not name:
            errors['name'] = 'Name is required.'
        elif len(name) < 2:
            errors['name'] = 'Name must be at least 2 characters.'
        elif not re.match(r'^[A-Za-z\s\-\'\.]+$', name):
            errors['name'] = 'Name contains invalid characters.'

        # --- Email validation ---
        if not email:
            errors['email'] = 'Email is required.'
        elif not re.match(
            r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$',
            email,
        ):
            errors['email'] = 'Please enter a valid email address.'

        # --- Subject validation ---
        if not subject:
            errors['subject'] = 'Subject is required.'

        # --- Message validation ---
        if not message:
            errors['message'] = 'Message is required.'
        elif len(message) < 10:
            errors['message'] = 'Message must be at least 10 characters.'
        elif len(message) > 5000:
            errors['message'] = 'Message must not exceed 5000 characters.'

        if errors:
            return JsonResponse(
                {'success': False, 'errors': errors},
                status=400,
            )

        contact_message = ContactMessage.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message,
        )

        notify_staff_users(
            type='contact_form',
            title='New Contact Form Submission',
            message=(
                f'{name} has submitted a contact form message: {subject}'
            ),
            link=(
                f'/admin-panel/api/contact-messages/'
                f'{contact_message.id}/'
            ),
        )

        return JsonResponse({
            'success': True,
            'message': (
                'Your message has been sent successfully. '
                'We will contact you via email soon.'
            ),
        })

    except json.JSONDecodeError:
        return JsonResponse(
            {'success': False, 'error': 'Invalid JSON'},
            status=400,
        )
    except Exception as e:
        return JsonResponse(
            {'success': False, 'error': str(e)},
            status=500,
        )


# ===========================================================================
# DASHBOARD DATA API
# ===========================================================================


@login_required
def get_dashboard_data(request):
    """API endpoint returning user info and recent activity for the dashboard."""
    user = request.user
    activities = UserActivity.objects.filter(user=user)[:5]

    return JsonResponse({
        'success': True,
        'user': {
            'name': user.get_full_name() or user.username,
            'username': user.username,
            'email': user.email,
            'joined_date': user.date_joined.strftime('%b %Y'),
            'last_active': 'Just now',
        },
        'activities': [
            {
                'type': a.activity_type,
                'description': a.description,
                'time': timesince(a.created_at),
            }
            for a in activities
        ],
    })
