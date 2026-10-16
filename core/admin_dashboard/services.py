"""
Services -- Admin Dashboard
============================
Reusable business logic extracted from views to reduce code duplication.

Contains:
  - admin_required decorator (authentication + authorization)
  - DesignSettings serialization helpers
  - Section-to-DesignSettings sync logic
  - Support ticket response logic
  - Contact message handling helpers
"""

import json
from functools import wraps

from django.http import JsonResponse
from django.utils import timezone

from .models import DesignSettings


# ===========================================================================
# DECORATOR: Admin-Only Access
# ===========================================================================

def admin_required(view_func):
    """Decorator that restricts a view to superusers and staff members only.

    Returns a 403 JSON error if the user lacks admin privileges.
    Usage::

        @login_required
        @admin_required
        def my_view(request):
            ...
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.is_staff):
            return JsonResponse(
                {'success': False, 'error': 'Unauthorized'}, status=403
            )
        return view_func(request, *args, **kwargs)
    return _wrapped


# ===========================================================================
# DECORATOR: Require POST Method
# ===========================================================================

def require_post(view_func):
    """Decorator that ensures the request method is POST.

    Returns a 405 JSON error otherwise.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if request.method != 'POST':
            return JsonResponse(
                {'success': False, 'error': 'POST required'}, status=405
            )
        return view_func(request, *args, **kwargs)
    return _wrapped


# ===========================================================================
# DECORATOR: Parse JSON Body
# ===========================================================================

def parse_json_body(view_func):
    """Decorator that parses ``request.body`` as JSON and injects
    ``request.json_data``.  Returns a 400 error on invalid JSON."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        try:
            request.json_data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {'success': False, 'error': 'Invalid JSON'}, status=400
            )
        return view_func(request, *args, **kwargs)
    return _wrapped


# ===========================================================================
# DESIGN SETTINGS — Serialization
# ===========================================================================

def serialize_design_settings(ds):
    """Convert a ``DesignSettings`` instance into a flat dict for API responses.

    Handles image/file fields by returning their URL or ``None``, and
    ensures JSON fields default to ``{}``.
    """
    return {
        # -- Landing Page Colors --
        'landing_primary_color': ds.landing_primary_color,
        'landing_primary_dark': ds.landing_primary_dark,
        'landing_primary_light': ds.landing_primary_light,
        'landing_text_dark': ds.landing_text_dark,
        'landing_text_gray': ds.landing_text_gray,
        'landing_bg_light': ds.landing_bg_light,
        'landing_bg_white': ds.landing_bg_white,
        'landing_font_family': ds.landing_font_family,
        'landing_logo_text': ds.landing_logo_text,
        'landing_logo_icon_bg': ds.landing_logo_icon_bg,
        'landing_nav_bg': ds.landing_nav_bg,

        # -- Landing Page Gradients --
        'landing_hero_gradient_start': ds.landing_hero_gradient_start,
        'landing_hero_gradient_end': ds.landing_hero_gradient_end,
        'landing_cta_gradient_start': ds.landing_cta_gradient_start,
        'landing_cta_gradient_end': ds.landing_cta_gradient_end,
        'landing_stats_gradient_start': ds.landing_stats_gradient_start,
        'landing_stats_gradient_end': ds.landing_stats_gradient_end,

        # -- Images (nullable) --
        'landing_logo_image': ds.landing_logo_image.url if ds.landing_logo_image else None,
        'landing_hero_image': ds.landing_hero_image.url if ds.landing_hero_image else None,
        'landing_hero_video': ds.landing_hero_video.url if ds.landing_hero_video else None,
        'landing_about_image': ds.landing_about_image.url if ds.landing_about_image else None,
        'landing_favicon': ds.landing_favicon.url if ds.landing_favicon else None,

        # -- Dashboard Colors --
        'dashboard_sidebar_bg': ds.dashboard_sidebar_bg,
        'dashboard_sidebar_text': ds.dashboard_sidebar_text,
        'dashboard_sidebar_accent': ds.dashboard_sidebar_accent,
        'dashboard_sidebar_logo_bg': ds.dashboard_sidebar_logo_bg,
        'dashboard_chat_bg': ds.dashboard_chat_bg,
        'dashboard_card_bg': ds.dashboard_card_bg,
        'dashboard_card_border': ds.dashboard_card_border,
        'dashboard_text_primary': ds.dashboard_text_primary,
        'dashboard_text_secondary': ds.dashboard_text_secondary,
        'dashboard_font_family': ds.dashboard_font_family,
        'dashboard_header_gradient_start': ds.dashboard_header_gradient_start,
        'dashboard_header_gradient_end': ds.dashboard_header_gradient_end,

        # -- Branding --
        'site_title': ds.site_title,
        'footer_text': ds.footer_text,
        'copyright_text': ds.copyright_text or '',

        # -- JSON fields --
        'landing_texts': ds.landing_texts or {},
        'landing_layout': ds.landing_layout or {},
    }


# ===========================================================================
# DESIGN SETTINGS — Text-field whitelists
# ===========================================================================

#: CharField / text-based settings that can be bulk-updated via POST.
TEXT_FIELDS = [
    'landing_primary_color', 'landing_primary_dark', 'landing_primary_light',
    'landing_text_dark', 'landing_text_gray', 'landing_bg_light',
    'landing_bg_white', 'landing_font_family', 'landing_logo_text',
    'landing_logo_icon_bg', 'landing_nav_bg',
    'landing_hero_gradient_start', 'landing_hero_gradient_end',
    'landing_cta_gradient_start', 'landing_cta_gradient_end',
    'landing_stats_gradient_start', 'landing_stats_gradient_end',
    'dashboard_sidebar_bg', 'dashboard_sidebar_text',
    'dashboard_sidebar_accent', 'dashboard_sidebar_logo_bg',
    'dashboard_chat_bg', 'dashboard_card_bg', 'dashboard_card_border',
    'dashboard_text_primary', 'dashboard_text_secondary',
    'dashboard_font_family', 'dashboard_header_gradient_start',
    'dashboard_header_gradient_end', 'site_title', 'footer_text',
]

#: JSON fields that can be bulk-updated.
JSON_FIELDS = ['landing_texts', 'landing_layout']

#: Image/file upload fields.
IMAGE_FIELDS = [
    'landing_logo_image', 'landing_hero_image', 'landing_hero_video',
    'landing_about_image', 'landing_favicon',
]


def update_design_settings_from_data(ds, data):
    """Update a ``DesignSettings`` instance from a flat dict, filtering to
    only recognised field names.  Also accepts file objects (multipart)."""
    for field in TEXT_FIELDS:
        if field in data:
            setattr(ds, field, data[field])
    for field in JSON_FIELDS:
        if field in data:
            val = data[field]
            if isinstance(val, str):
                try:
                    val = json.loads(val)
                except json.JSONDecodeError:
                    continue
            setattr(ds, field, val)
    for field in IMAGE_FIELDS:
        if field in data:
            setattr(ds, field, data[field])


# ===========================================================================
# SECTION-DESIGN / DESIGN-SETTINGS SYNC
# ===========================================================================

#: Maps section names to (section_key -> text_key) for syncing section
#: text settings into the ``DesignSettings.landing_texts`` JSON field.
SECTION_TO_TEXT_MAP = {
    'hero': {
        'text_heading': 'hero_heading',
        'text_description': 'hero_description',
        'text_badge': 'hero_badge',
        'text_primary_btn': 'hero_primary_btn',
        'text_secondary_btn': 'hero_secondary_btn',
    },
    'features': {
        'text_heading': 'features_heading',
        'text_description': 'features_description',
    },
    'statistics': {
        'text_heading': 'stats_heading',
        'text_description': 'stats_description',
    },
    'about': {
        'text_heading': 'about_heading',
        'text_description': 'about_description',
        'text_badge': 'about_badge',
    },
    'how_it_works': {
        'text_heading': 'how_it_works_heading',
        'text_description': 'how_it_works_description',
    },
    'testimonials': {
        'text_heading': 'testimonials_heading',
        'text_description': 'testimonials_description',
    },
    'cta': {
        'text_heading': 'cta_heading',
        'text_description': 'cta_description',
    },
    'contact': {
        'text_heading': 'contact_heading',
        'text_description': 'contact_description',
    },
    'footer': {
        'text_description': 'footer_text',
        'text_logo_text': 'footer_logo_text',
        'text_copyright': 'copyright_text',
    },
}


def sync_section_to_design_settings(page, section_name, settings):
    """Copy section-level text/visibility settings into
    ``DesignSettings.landing_texts`` and ``landing_layout`` for backward
    compatibility with older templates that read from the singleton.

    Only applies when *page* is ``'landing'``.
    """
    if page != 'landing':
        return
    try:
        ds = DesignSettings.get_settings()
        texts = dict(ds.landing_texts or {})
        layout = dict(ds.landing_layout or {})
        changed = False

        # Store the full settings blob keyed by section name.
        texts[f'section_{section_name}_settings'] = settings

        # Map section-level text keys to top-level text keys.
        key_map = SECTION_TO_TEXT_MAP.get(section_name, {})
        for section_key, text_key in key_map.items():
            if section_key in settings:
                texts[text_key] = settings[section_key]
                changed = True

        if changed or f'section_{section_name}_settings' in texts:
            ds.landing_texts = texts
            layout[f'section_{section_name}'] = settings.get(
                'is_visible', True
            )
            ds.landing_layout = layout
            ds.save()
    except Exception:
        # Swallow errors during sync so the primary save never breaks.
        pass


# ===========================================================================
# SUPPORT TICKET — Helpers
# ===========================================================================

VALID_TICKET_STATUSES = ['open', 'in_progress', 'resolved', 'closed']


def validate_ticket_status(status):
    """Check whether *status* is one of the valid ticket statuses."""
    return status in VALID_TICKET_STATUSES


def respond_to_asl_ticket(ticket, files, post_data):
    """Handle an admin video/text response to an ASL-user support ticket."""
    if not files.get('response_video'):
        return None, 'Video response is required for ASL user tickets.'

    ticket.admin_response_video = files['response_video']
    ticket.admin_response_text = post_data.get('response_text', '')
    ticket.status = post_data.get('status', 'in_progress')
    ticket.responded_at = timezone.now()
    ticket.save()
    return ticket, None


def respond_to_normal_ticket(ticket, response_text, new_status='in_progress'):
    """Handle an admin text response to a normal-user support ticket."""
    if not response_text:
        return None, 'Text response is required for normal user tickets.'

    ticket.admin_response_text = response_text
    ticket.status = new_status
    ticket.responded_at = timezone.now()
    ticket.save()
    return ticket, None
