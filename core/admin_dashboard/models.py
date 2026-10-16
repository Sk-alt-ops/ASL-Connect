"""
Models -- Admin Dashboard
===========================
Design management models for the ASL Connect platform.

Three levels of design customisation:

1. **DesignSettings**  -- Global design singleton (colours, fonts, images).
2. **PageDesign**      -- Per-page design overrides (landing, auth, dashboards).
3. **SectionDesign**   -- Per-section overrides for the landing page.

Each level inherits sensible defaults and can be independently published.
"""

import copy
import json

from django.db import models


# ===========================================================================
# CONSTANTS & DEFAULTS
# ===========================================================================

# -------------------------------------------------------------------
# DEFAULT_PAGE_SETTINGS
# CSS-variable defaults used by PageDesign.get_settings().
# Keys map directly to CSS custom-property names in the front-end.
# -------------------------------------------------------------------
DEFAULT_PAGE_SETTINGS = {
    # -- Colors --
    'primary_color': '#2563eb',
    'primary_dark': '#1d4ed8',
    'primary_light': '#dbeafe',
    'secondary_color': '#7c3aed',
    'secondary_dark': '#6d28d9',
    'secondary_light': '#f5f3ff',
    'background_color': '#ffffff',
    'background_secondary': '#f8fafc',
    'text_primary': '#111827',
    'text_secondary': '#6b7280',
    'text_muted': '#9ca3af',
    'success_color': '#059669',
    'warning_color': '#d97706',
    'error_color': '#dc2626',
    'info_color': '#2563eb',

    # -- Fonts --
    'font_family': 'Inter, sans-serif',
    'heading_font': 'Inter, sans-serif',
    'font_size_base': '16px',
    'font_size_heading': '32px',
    'font_size_small': '13px',
    'font_weight_normal': '400',
    'font_weight_bold': '700',
    'line_height': '1.5',

    # -- Button Styles --
    'button_border_radius': '8px',
    'button_padding_x': '18px',
    'button_padding_y': '9px',
    'button_font_weight': '700',
    'button_primary_bg': '#2563eb',
    'button_primary_text': '#ffffff',
    'button_primary_hover': '#1d4ed8',
    'button_outline_border': '#e5e7ef',
    'button_outline_text': '#1a1d2e',
    'button_font_size': '13px',

    # -- Card Styles --
    'card_border_radius': '14px',
    'card_background': '#ffffff',
    'card_border': '#e5e7ef',
    'card_shadow': '0 1px 4px rgba(0,0,0,0.06)',
    'card_shadow_hover': '0 4px 16px rgba(0,0,0,0.1)',
    'card_padding': '22px',

    # -- Border Radius --
    'border_radius_sm': '8px',
    'border_radius_md': '12px',
    'border_radius_lg': '16px',
    'border_radius_full': '9999px',

    # -- Spacing & Layout --
    'spacing_xs': '4px',
    'spacing_sm': '8px',
    'spacing_md': '16px',
    'spacing_lg': '24px',
    'spacing_xl': '32px',
    'spacing_xxl': '48px',
    'section_padding': '80px',
    'container_max_width': '1200px',
    'content_gap': '20px',
    'grid_gap': '20px',

    # -- Navbar --
    'nav_background': 'rgba(255,255,255,0.95)',
    'nav_text': '#111827',
    'nav_height': '64px',
    'nav_shadow': '0 1px 3px rgba(0,0,0,0.08)',

    # -- Icons --
    'icon_size': '20px',
    'icon_color': '#6b7280',
    'icon_accent_color': '#2563eb',

    # -- Light/Dark Mode --
    'mode': 'light',
    'dark_primary': '#60a5fa',
    'dark_background': '#0f172a',
    'dark_background_secondary': '#1e293b',
    'dark_text_primary': '#f1f5f9',
    'dark_text_secondary': '#94a3b8',
    'dark_card_background': '#1e293b',
    'dark_card_border': '#334155',
    'dark_nav_background': '#1e293b',
    'dark_nav_text': '#f1f5f9',
}

# -------------------------------------------------------------------
# PAGE_CHOICES -- page names used by the PageDesign model.
# -------------------------------------------------------------------
PAGE_CHOICES = [
    ('landing', 'Home (Landing Page)'),
    ('asl_dashboard', 'ASL Dashboard'),
    ('normal_dashboard', 'Normal Dashboard'),
    ('auth', 'Auth Pages'),
]

# -------------------------------------------------------------------
# DEFAULT_LANDING_TEXTS
# Full set of landing-page textual content used as fallback when
# DesignSettings.landing_texts is empty.
# -------------------------------------------------------------------
DEFAULT_LANDING_TEXTS = {
    # -- Hero Section --
    'hero_badge': 'AI-Powered ASL Communication',
    'hero_heading': 'Bridge the Communication Gap with <span>ASL</span>',
    'hero_description': (
        'Break down communication barriers with AI-powered real-time ASL '
        'translation. Our platform bridges the gap between ASL and hearing '
        'users through smart camera-based sign detection and instant '
        'translation \u2014 making every conversation seamless, natural, and '
        'accessible.'
    ),

    # -- How It Works Section --
    'how_it_works_heading': 'How It Works',
    'how_it_works_description': (
        'Three simple steps to start communicating across the '
        'ASL-hearing divide'
    ),

    # -- Features Section --
    'features_heading': 'Powerful Features',
    'features_description': (
        'Everything you need for seamless ASL communication, built with '
        'accessibility at its core'
    ),

    # -- About Section --
    'about_heading': 'Making Communication Accessible for Everyone',
    'about_description': (
        'ASL Connect is a camera-based AI communication platform designed '
        'to bridge the gap between ASL users and hearing users. Using '
        'camera-based ASL detection with MediaPipe Hands, the platform '
        'recognises real-time hand signs and translates them into text.'
    ),
    'about_badge': 'About ASL Connect',

    # -- CTA Section --
    'cta_heading': 'Ready to Bridge the Gap?',
    'cta_description': (
        'Join ASL Connect today and start communicating with ASL users '
        'instantly. Camera-based sign detection with instant translation.'
    ),

    # -- Testimonials Section --
    'testimonials_heading': 'What Our Users Say',
    'testimonials_description': (
        'Hear from the people who use ASL Connect to communicate every day'
    ),

    # -- Contact Section --
    'contact_heading': 'Contact Us',
    'contact_description': (
        'Have questions or need support? We\'re here to help.'
    ),
    'contact_info_heading': 'Let\'s Connect',
    'contact_info_text': (
        'ASL Connect is a camera-based AI communication platform bridging '
        'the gap between ASL users and hearing users. Whether you have '
        'feedback, need technical support, or want to learn more about our '
        'platform, reach out to us.'
    ),

    # -- Footer --
    'footer_text': 'Making communication accessible for everyone.',
    'copyright_text': '',

    # -- Structured JSON Data --
    'features_items': json.dumps([
        {'icon': '\U0001f4f7', 'title': 'Camera-Based ASL Detection',
         'description': 'Real-time hand sign detection using MediaPipe.'},
        {'icon': '\u26a1', 'title': 'Real-Time Chat',
         'description': 'Instant messaging with WebSocket-powered communication.'},
        {'icon': '\U0001f50d', 'title': 'ASL Alphabet Symbols',
         'description': 'Every letter A-Z has its own ASL symbol image.'},
        {'icon': '\U0001f465', 'title': 'Friend System',
         'description': 'Send friend requests and start chats with one click.'},
        {'icon': '\U0001f3ac', 'title': 'Video Messaging',
         'description': 'Record and send video messages to each other.'},
        {'icon': '\U0001f4ac', 'title': 'Help & Support',
         'description': 'Get help from admins and track your requests.'},
    ]),
    'how_it_works_steps': json.dumps([
        {'icon': '\U0001f4f7', 'title': 'ASL User Opens Camera',
         'description': 'ASL user activates their webcam. MediaPipe detects hand landmarks.'},
        {'icon': '\U0001f9f0', 'title': 'AI Detects Letters',
         'description': 'Rule-based finger logic recognises ASL alphabet letters.'},
        {'icon': '\U0001f4ac', 'title': 'Auto-Translation Happens',
         'description': 'Normal users see text, ASL users see symbol images.'},
    ]),
    'about_cards': json.dumps([
        {'icon': '\U0001f4f7', 'title': 'Camera-Based',
         'description': 'Real-time hand detection via webcam.'},
        {'icon': '\U0001f465', 'title': 'Dual User Modes',
         'description': 'ASL users sign, hearing users type. Auto-translates.'},
        {'icon': '\u26a1', 'title': 'Smart Matching',
         'description': 'Fuzzy search and phrase suggestions.'},
        {'icon': '\U0001f496', 'title': 'Real-Time Chat',
         'description': 'WebSocket-powered instant messaging.'},
    ]),
    'testimonials': json.dumps([
        {'name': 'Sarah Rodriguez', 'role': 'ASL User \u00b7 Teacher',
         'avatar': '#3b82f6', 'initials': 'SR',
         'text': '"ASL Connect changed how I communicate."'},
        {'name': 'Michael Johnson', 'role': 'Normal User \u00b7 Engineer',
         'avatar': '#8b5cf6', 'initials': 'MJ',
         'text': '"As a hearing person, I always wanted to talk with my deaf neighbour."'},
        {'name': 'Aisha Patel', 'role': 'Admin \u00b7 Platform Manager',
         'avatar': '#ef4444', 'initials': 'AP',
         'text': '"The admin dashboard makes it so easy to manage ASL content."'},
        {'name': 'Dr. David Lee', 'role': 'Normal User \u00b7 Healthcare',
         'avatar': '#f59e0b', 'initials': 'DL',
         'text': '"I work at a hospital and we use ASL Connect."'},
        {'name': 'Emma Williams', 'role': 'ASL User \u00b7 Student',
         'avatar': '#10b981', 'initials': 'EW',
         'text': '"As a deaf student, I struggled to communicate."'},
        {'name': 'James Thompson', 'role': 'ASL User \u00b7 Designer',
         'avatar': '#06b6d4', 'initials': 'JT',
         'text': '"The community here is amazing."'},
    ]),
    'stats': json.dumps([
        {'value': '500+', 'label': 'ASL Signs'},
        {'value': '6', 'label': 'Categories'},
        {'value': '1K+', 'label': 'Active Users'},
        {'value': '99.9%', 'label': 'Uptime'},
    ]),
}

# -------------------------------------------------------------------
# DEFAULT_LANDING_LAYOUT
# Boolean toggles controlling which sections are visible on landing.
# -------------------------------------------------------------------
DEFAULT_LANDING_LAYOUT = {
    'section_hero': True,
    'section_how_it_works': True,
    'section_features': True,
    'section_about': True,
    'section_message_flow': True,
    'section_testimonials': True,
    'section_stats': True,
    'section_contact': True,
    'section_cta': True,
    'hero_centered': False,
    'hero_fullscreen': False,
}

# -------------------------------------------------------------------
# SECTION_DEFAULTS
# Per-section default settings (text, colours, fonts, layout) used
# as fallback when a SectionDesign record has no custom settings.
# -------------------------------------------------------------------
SECTION_DEFAULTS = {
    'hero': {
        'label': 'Hero Section',
        'settings': {
            'text_badge': 'AI-Powered ASL Communication',
            'text_heading': 'Bridge the Communication Gap with <span>ASL</span>',
            'text_description': 'Break down communication barriers with AI-powered real-time ASL translation.',
            'text_primary_btn': 'Get Started',
            'text_secondary_btn': 'Explore Features',
            'color_overlay': 'rgba(0,0,0,0.5)',
            'color_text': '#ffffff',
            'color_accent': '#3b82f6',
            'font_heading': 'Inter, sans-serif',
            'font_body': 'Inter, sans-serif',
            'font_heading_size': '48px',
            'image_background': None,
            'video_background': None,
            'icon_type': 'none',
            'button_primary_style': 'fill',
            'button_secondary_style': 'outline',
            'button_border_radius': '8px',
            'layout_fullscreen': False,
            'layout_centered': False,
            'layout_padding': '80px',
            'layout_container_width': '1200px',
            'stats_display': 'inline',
        },
    },
    'features': {
        'label': 'Features Section',
        'settings': {
            'text_heading': 'Powerful Features',
            'text_description': 'Everything you need for seamless ASL communication',
            'color_background': '#f8fafc',
            'color_text': '#111827',
            'color_card_bg': '#ffffff',
            'color_card_border': '#e5e7ef',
            'color_accent': '#3b82f6',
            'font_heading': 'Inter, sans-serif',
            'font_body': 'Inter, sans-serif',
            'font_heading_size': '32px',
            'layout_columns': '3',
            'layout_padding': '80px',
            'layout_container_width': '1200px',
        },
    },
    'statistics': {
        'label': 'Statistics Section',
        'settings': {
            'text_heading': 'Our Impact',
            'text_description': 'Making communication accessible for everyone',
            'color_gradient_start': '#1e40af',
            'color_gradient_end': '#2563eb',
            'color_text': '#ffffff',
            'color_value': '#ffffff',
            'font_heading': 'Inter, sans-serif',
            'font_body': 'Inter, sans-serif',
            'font_heading_size': '28px',
            'font_value_size': '36px',
            'layout_padding': '60px',
            'layout_container_width': '1200px',
        },
    },
    'about': {
        'label': 'About Section',
        'settings': {
            'text_badge': 'About ASL Connect',
            'text_heading': 'Making Communication Accessible for Everyone',
            'text_description': 'ASL Connect bridges the gap between ASL users and hearing users.',
            'color_background': '#ffffff',
            'color_text': '#111827',
            'color_card_bg': '#f8fafc',
            'color_accent': '#3b82f6',
            'font_heading': 'Inter, sans-serif',
            'font_body': 'Inter, sans-serif',
            'font_heading_size': '32px',
            'image_about': None,
            'layout_columns': '2',
            'layout_padding': '80px',
            'layout_container_width': '1200px',
        },
    },
    'testimonials': {
        'label': 'Testimonials Section',
        'settings': {
            'text_heading': 'What Our Users Say',
            'text_description': 'Hear from the people who use ASL Connect',
            'color_background': '#f8fafc',
            'color_text': '#111827',
            'color_card_bg': '#ffffff',
            'color_accent': '#3b82f6',
            'font_heading': 'Inter, sans-serif',
            'font_body': 'Inter, sans-serif',
            'font_heading_size': '32px',
            'layout_columns': '3',
            'layout_padding': '80px',
            'layout_container_width': '1200px',
        },
    },
    'cta': {
        'label': 'CTA Section',
        'settings': {
            'text_heading': 'Ready to Bridge the Gap?',
            'text_description': 'Join ASL Connect today and start communicating instantly.',
            'text_button': 'Get Started Free',
            'color_gradient_start': '#1e40af',
            'color_gradient_end': '#2563eb',
            'color_text': '#ffffff',
            'color_button_bg': '#ffffff',
            'color_button_text': '#1e40af',
            'font_heading': 'Inter, sans-serif',
            'font_body': 'Inter, sans-serif',
            'font_heading_size': '36px',
            'button_border_radius': '8px',
            'layout_padding': '80px',
            'layout_container_width': '1200px',
        },
    },
    'footer': {
        'label': 'Footer Section',
        'settings': {
            'text_logo_text': 'ASL Connect',
            'text_description': 'Making communication accessible for everyone.',
            'text_copyright': 'ASL Connect',
            'color_background': '#111827',
            'color_text': '#f9fafb',
            'color_link': '#9ca3af',
            'color_link_hover': '#ffffff',
            'color_divider': '#374151',
            'font_heading': 'Inter, sans-serif',
            'font_body': 'Inter, sans-serif',
            'image_logo': None,
            'layout_padding': '60px',
            'layout_container_width': '1200px',
        },
    },
    'how_it_works': {
        'label': 'How It Works Section',
        'settings': {
            'text_heading': 'How It Works',
            'text_description': 'Three simple steps to start communicating across the ASL-hearing divide',
            'color_background': '#ffffff',
            'color_text': '#111827',
            'color_card_bg': '#f8fafc',
            'color_accent': '#3b82f6',
            'font_heading': 'Inter, sans-serif',
            'font_body': 'Inter, sans-serif',
            'font_heading_size': '32px',
            'layout_columns': '3',
            'layout_padding': '80px',
            'layout_container_width': '1200px',
        },
    },
    'contact': {
        'label': 'Contact Section',
        'settings': {
            'text_heading': 'Contact Us',
            'text_description': 'Have questions or need support? We\'re here to help.',
            'text_info_heading': 'Let\'s Connect',
            'text_info_text': 'ASL Connect bridges the gap between ASL users and hearing users.',
            'color_background': '#f8fafc',
            'color_text': '#111827',
            'color_card_bg': '#ffffff',
            'color_accent': '#3b82f6',
            'color_form_bg': '#ffffff',
            'font_heading': 'Inter, sans-serif',
            'font_body': 'Inter, sans-serif',
            'font_heading_size': '32px',
            'layout_padding': '80px',
            'layout_container_width': '1200px',
        },
    },
}

#: Ordered list of section keys used for the landing page.
HOME_SECTIONS = [
    'hero', 'features', 'statistics', 'about',
    'testimonials', 'cta', 'footer', 'how_it_works', 'contact',
]


# ===========================================================================
# MODEL: SectionDesign
# ===========================================================================

class SectionDesign(models.Model):
    """Per-section design storage for the landing page.

    Each record stores its own JSON ``settings`` blob that overrides
    the defaults in ``SECTION_DEFAULTS``.  Sections are uniquely
    identified by the combination of ``page_name`` + ``section_name``.
    """

    page_name = models.CharField(
        max_length=50,
        default='landing',
        help_text='Which page this section belongs to (e.g. "landing").',
    )
    section_name = models.CharField(
        max_length=50,
        help_text='Machine-readable section key (e.g. "hero", "features").',
    )
    label = models.CharField(
        max_length=100,
        default='',
        help_text='Human-readable section label shown in the admin UI.',
    )
    is_visible = models.BooleanField(
        default=True,
        help_text='Whether this section is displayed on the live site.',
    )
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text='Custom JSON settings that override SECTION_DEFAULTS.',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Timestamp when this section design was first created.',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='Timestamp of the last modification.',
    )

    class Meta:
        unique_together = ('page_name', 'section_name')
        ordering = ['page_name', 'section_name']
        verbose_name = 'Section Design'
        verbose_name_plural = 'Section Designs'

    def __str__(self):
        return f'{self.label or self.section_name} ({self.page_name})'

    def get_settings(self):
        """Merge saved settings on top of section defaults.

        Returns a complete dict with all expected keys populated.
        """
        defaults = dict(
            SECTION_DEFAULTS.get(self.section_name, {}).get('settings', {})
        )
        if self.settings:
            defaults.update(self.settings)
        return defaults

    def get_setting(self, key, default=None):
        """Return a single setting value, falling back to section defaults."""
        if self.settings and key in self.settings:
            return self.settings[key]
        return (
            SECTION_DEFAULTS
            .get(self.section_name, {})
            .get('settings', {})
            .get(key, default)
        )

    @classmethod
    def get_or_create_defaults(cls, page_name='landing'):
        """Ensure every known ``HOME_SECTIONS`` has a DB record for *page_name*.

        Idempotent -- existing records are not modified.
        """
        for section_name in HOME_SECTIONS:
            info = SECTION_DEFAULTS.get(section_name, {})
            cls.objects.get_or_create(
                page_name=page_name,
                section_name=section_name,
                defaults={
                    'label': info.get('label', section_name),
                    'is_visible': True,
                    'settings': {},
                },
            )


# ===========================================================================
# MODEL: DesignSettings  (Singleton)
# ===========================================================================

class DesignSettings(models.Model):
    """Global design settings singleton.

    Controls the colours, fonts, images, text content, and layout options
    used by the landing page and dashboards.  There should only ever be
    **one** instance (pk=1), retrieved via ``DesignSettings.get_settings()``.
    """

    # -- Landing Page Colours --
    landing_primary_color = models.CharField(max_length=7, default='#2563eb')
    landing_primary_dark = models.CharField(max_length=7, default='#1d4ed8')
    landing_primary_light = models.CharField(max_length=7, default='#dbeafe')
    landing_text_dark = models.CharField(max_length=7, default='#111827')
    landing_text_gray = models.CharField(max_length=7, default='#6b7280')
    landing_bg_light = models.CharField(max_length=7, default='#f8fafc')
    landing_bg_white = models.CharField(max_length=7, default='#ffffff')
    landing_font_family = models.CharField(max_length=100, default='Inter, sans-serif')
    landing_logo_text = models.CharField(max_length=50, default='ASL Connect')
    landing_logo_icon_bg = models.CharField(max_length=7, default='#2563eb')
    landing_nav_bg = models.CharField(max_length=30, default='rgba(255,255,255,0.95)')

    # -- Landing Page Gradients --
    landing_hero_gradient_start = models.CharField(max_length=7, default='#3b82f6')
    landing_hero_gradient_end = models.CharField(max_length=7, default='#1d4ed8')
    landing_cta_gradient_start = models.CharField(max_length=7, default='#1e40af')
    landing_cta_gradient_end = models.CharField(max_length=7, default='#2563eb')
    landing_stats_gradient_start = models.CharField(max_length=7, default='#1e40af')
    landing_stats_gradient_end = models.CharField(max_length=7, default='#2563eb')

    # -- Landing Page Images --
    landing_logo_image = models.ImageField(
        upload_to='design/', blank=True, null=True,
        help_text='Custom logo image (replaces text logo).',
    )
    landing_hero_image = models.ImageField(
        upload_to='design/', blank=True, null=True,
        help_text='Hero section background image.',
    )
    landing_hero_video = models.FileField(
        upload_to='design/', blank=True, null=True,
        help_text='Hero section background video (MP4/WebM).',
    )
    landing_about_image = models.ImageField(
        upload_to='design/', blank=True, null=True,
        help_text='About section illustration image.',
    )
    landing_favicon = models.ImageField(
        upload_to='design/', blank=True, null=True,
        help_text='Browser tab favicon image.',
    )

    # -- Dashboard Colours --
    dashboard_sidebar_bg = models.CharField(max_length=7, default='#ffffff')
    dashboard_sidebar_text = models.CharField(max_length=7, default='#1a1d2e')
    dashboard_sidebar_accent = models.CharField(max_length=7, default='#3b5bdb')
    dashboard_sidebar_logo_bg = models.CharField(max_length=7, default='#3b5bdb')
    dashboard_chat_bg = models.CharField(max_length=7, default='#f0f2f8')
    dashboard_card_bg = models.CharField(max_length=7, default='#ffffff')
    dashboard_card_border = models.CharField(max_length=7, default='#e5e7ef')
    dashboard_text_primary = models.CharField(max_length=7, default='#1a1d2e')
    dashboard_text_secondary = models.CharField(max_length=7, default='#6b7280')
    dashboard_font_family = models.CharField(max_length=100, default='Plus Jakarta Sans, sans-serif')
    dashboard_header_gradient_start = models.CharField(max_length=7, default='#ef4444')
    dashboard_header_gradient_end = models.CharField(max_length=7, default='#f97316')

    # -- Branding --
    site_title = models.CharField(max_length=100, default='ASL Connect')
    footer_text = models.CharField(
        max_length=200,
        default='Making communication accessible for everyone.',
    )
    copyright_text = models.CharField(max_length=200, default='')

    # -- Editable Text Content --
    landing_texts = models.JSONField(
        default=dict, blank=True,
        help_text=(
            'Overrides for all landing-page text.  Keys match the '
            'DEFAULT_LANDING_TEXTS dict keys.'
        ),
    )

    # -- Layout Options --
    landing_layout = models.JSONField(
        default=dict, blank=True,
        help_text='Section-visibility and layout toggles for the landing page.',
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Design Settings'
        verbose_name_plural = 'Design Settings'

    def __str__(self):
        return 'Design Settings'

    def get_text(self, key, default=''):
        """Return a landing-page text value, falling back to defaults."""
        if not self.landing_texts:
            return DEFAULT_LANDING_TEXTS.get(key, default)
        return self.landing_texts.get(
            key, DEFAULT_LANDING_TEXTS.get(key, default)
        )

    def get_layout(self, key, default=True):
        """Return a layout toggle value, falling back to defaults."""
        if not self.landing_layout:
            return DEFAULT_LANDING_LAYOUT.get(key, default)
        return self.landing_layout.get(
            key, DEFAULT_LANDING_LAYOUT.get(key, default)
        )

    @classmethod
    def get_settings(cls):
        """Return the singleton ``DesignSettings`` instance (pk=1).

        Creates the record if it does not exist yet.
        """
        obj, _created = cls.objects.get_or_create(id=1)
        return obj


# ===========================================================================
# MODEL: PageDesign
# ===========================================================================

class PageDesign(models.Model):
    """Per-page design configuration.

    Each page (landing, auth, asl_dashboard, normal_dashboard) can have
    its own colour/font/layout settings stored as JSON.  Supports global
    apply (copy to all pages) and publish toggles.
    """

    page_name = models.CharField(
        max_length=50,
        unique=True,
        choices=PAGE_CHOICES,
        help_text='Machine-readable page identifier.',
    )
    label = models.CharField(
        max_length=100,
        help_text='Human-readable page name shown in the admin UI.',
    )
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text='Custom settings that override DEFAULT_PAGE_SETTINGS.',
    )
    apply_globally = models.BooleanField(
        default=False,
        help_text='When True, copy these settings to every other page.',
    )
    is_published = models.BooleanField(
        default=False,
        help_text='Whether this design is live and visible to end users.',
    )
    is_default = models.BooleanField(
        default=False,
        help_text='Whether this uses the out-of-the-box default settings.',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Timestamp when this page design was created.',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='Timestamp of the last modification.',
    )

    class Meta:
        ordering = ['page_name']
        verbose_name = 'Page Design'
        verbose_name_plural = 'Page Designs'

    def __str__(self):
        return f'{self.label} Design'

    def get_settings(self):
        """Return merged settings (saved on top of ``DEFAULT_PAGE_SETTINGS``)."""
        merged = copy.deepcopy(DEFAULT_PAGE_SETTINGS)
        if self.settings:
            merged.update(self.settings)
        return merged

    def get_setting(self, key, default=None):
        """Return a single setting, falling back to ``DEFAULT_PAGE_SETTINGS``."""
        if self.settings and key in self.settings:
            return self.settings[key]
        return DEFAULT_PAGE_SETTINGS.get(key, default)

    @classmethod
    def get_or_create_defaults(cls):
        """Ensure every ``PAGE_CHOICES`` entry has a DB record.

        Idempotent -- existing records are not modified.
        """
        for name, label in PAGE_CHOICES:
            cls.objects.get_or_create(
                page_name=name,
                defaults={
                    'label': label,
                    'is_default': True,
                    'settings': {},
                },
            )
