"""
Authentication Views — Register, Login, Logout, Profile, Password

Handles all user account management via AJAX JSON endpoints consumed
by the landing page auth modal.

All views accept and return JSON, making them compatible with the
single-page application architecture.

Redirect logic after login/register:
- Staff/Superusers → ``/admin-panel/``
- ASL Users → ``/asl/dashboard/``
- Normal Users → ``/normal/dashboard/``
"""

import json
from django.shortcuts import redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import (
    authenticate, login, logout, update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from .models import User


# ===========================================================================
# HELPERS
# ===========================================================================


def _get_redirect_url(user):
    """
    Determine the post-login/register redirect URL based on user role.

    - Staff/superusers go to the admin panel
    - ASL users go to the ASL dashboard
    - Normal (hearing) users go to the normal dashboard
    """
    if user.is_superuser or user.is_staff:
        return '/admin-panel/'
    elif user.is_asl_user:
        return '/asl/dashboard/'
    return '/normal/dashboard/'


def _user_response_data(user):
    """Return a standardised user summary dict for JSON responses."""
    return {
        'name': user.get_full_name() or user.username,
        'username': user.username,
        'email': user.email,
        'is_asl_user': user.is_asl_user,
    }


# ===========================================================================
# REGISTRATION
# ===========================================================================


@csrf_exempt
def register(request):
    """
    Handle new user registration via AJAX POST.

    Validates all required fields, checks for duplicate username/email,
    creates the account, logs the user in, and returns a redirect URL.

    **POST** body: ``{ name, username, email, password, disability_status }``
    """
    if request.method != 'POST':
        return JsonResponse(
            {'success': False, 'error': 'POST required'},
            status=405,
        )

    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        disability_status = data.get('disability_status', False)

        if not all([name, username, email, password]):
            return JsonResponse(
                {'success': False, 'error': 'All fields are required'},
                status=400,
            )

        if User.objects.filter(username=username).exists():
            return JsonResponse(
                {'success': False, 'error': 'Username already taken'},
                status=400,
            )

        if User.objects.filter(email=email).exists():
            return JsonResponse(
                {'success': False, 'error': 'Email already registered'},
                status=400,
            )

        is_asl = (
            disability_status is True
            or str(disability_status).lower() == 'true'
        )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=name,
            is_asl_user=is_asl,
        )

        login(request, user)

        return JsonResponse({
            'success': True,
            'message': 'Account created successfully!',
            'redirect_url': _get_redirect_url(user),
            'user': _user_response_data(user),
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
# LOGIN
# ===========================================================================


@csrf_exempt
def login_view(request):
    """
    Authenticate users via username or email via AJAX POST.

    Supports both username and email login. Falls back to email
    lookup if username authentication fails.

    **POST** body: ``{ username, password }``
    """
    if request.method != 'POST':
        return JsonResponse(
            {'success': False, 'error': 'POST required'},
            status=405,
        )

    try:
        data = json.loads(request.body)
        username_or_email = data.get('username', '').strip()
        password = data.get('password', '').strip()

        if not all([username_or_email, password]):
            return JsonResponse(
                {'success': False, 'error': 'All fields are required'},
                status=400,
            )

        user = authenticate(
            request, username=username_or_email, password=password,
        )

        # Fallback: try email lookup if username auth fails
        if user is None:
            try:
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(
                    request,
                    username=user_obj.username,
                    password=password,
                )
            except User.DoesNotExist:
                pass

        if user is not None:
            login(request, user)
            return JsonResponse({
                'success': True,
                'message': 'Login successful!',
                'redirect_url': _get_redirect_url(user),
                'user': _user_response_data(user),
            })
        else:
            return JsonResponse(
                {'success': False, 'error': 'Invalid credentials'},
                status=401,
            )

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


def logout_view(request):
    """Log out the current user and redirect to the landing page."""
    logout(request)
    return redirect('/')


# ===========================================================================
# PROFILE MANAGEMENT
# ===========================================================================


@login_required
@csrf_exempt
def update_profile(request):
    """
    Update the authenticated user's profile (name, username, email, avatar).

    Accepts both multipart/form-data (with file uploads) and JSON payloads.
    Validates uniqueness of username and email before saving changes.

    **POST** (multipart): ``full_name, username, email, profile_picture``
    **POST** (JSON): ``{ full_name, username, email }``
    """
    if request.method != 'POST':
        return JsonResponse(
            {'success': False, 'error': 'POST required'},
            status=405,
        )

    try:
        user = request.user
        content_type = request.content_type or ''

        # Parse input based on content type
        if 'multipart/form-data' in content_type:
            first_name = request.POST.get('full_name', '').strip()
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip()
            profile_picture = request.FILES.get('profile_picture')
        else:
            data = json.loads(request.body)
            first_name = data.get('full_name', '').strip()
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            profile_picture = None

        if username and username != user.username:
            if User.objects.filter(username=username).exclude(
                pk=user.pk,
            ).exists():
                return JsonResponse(
                    {'success': False, 'error': 'Username already taken'},
                    status=400,
                )
            user.username = username

        if email and email != user.email:
            if User.objects.filter(email=email).exclude(
                pk=user.pk,
            ).exists():
                return JsonResponse(
                    {'success': False, 'error': 'Email already registered'},
                    status=400,
                )
            user.email = email

        if first_name:
            user.first_name = first_name

        if profile_picture:
            user.profile_picture = profile_picture

        user.save()

        return JsonResponse({
            'success': True,
            'message': 'Profile updated successfully!',
            'user': {
                'name': user.get_full_name() or user.username,
                'username': user.username,
                'email': user.email,
                'profile_picture_url': (
                    user.profile_picture.url if user.profile_picture else None
                ),
            },
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


@login_required
@csrf_exempt
def change_password(request):
    """
    Change the current user's password with validation.

    Validates current password, ensures new passwords match,
    enforces minimum length (8 chars), and updates the session
    auth hash to prevent logout after password change.

    **POST** body: ``{ current_password, new_password, confirm_password }``
    """
    if request.method != 'POST':
        return JsonResponse(
            {'success': False, 'error': 'POST required'},
            status=405,
        )

    try:
        data = json.loads(request.body)
        user = request.user

        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        confirm_password = data.get('confirm_password', '')

        if not all([current_password, new_password, confirm_password]):
            return JsonResponse({
                'success': False,
                'error': 'All password fields are required.',
            }, status=400)

        if not user.check_password(current_password):
            return JsonResponse({
                'success': False,
                'error': 'Current password is incorrect.',
            }, status=400)

        if new_password != confirm_password:
            return JsonResponse({
                'success': False,
                'error': 'New passwords do not match.',
            }, status=400)

        if len(new_password) < 8:
            return JsonResponse({
                'success': False,
                'error': 'Password must be at least 8 characters.',
            }, status=400)

        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)

        return JsonResponse({
            'success': True,
            'message': 'Password changed successfully!',
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
