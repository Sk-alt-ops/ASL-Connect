"""
Context Processor -- Admin Dashboard
======================================
Injects global ``design_settings`` and per-section ``section_designs``
into every Django template context, enabling dynamic CSS variable
rendering and section-level overrides on the landing page.
"""

from .models import SECTION_DEFAULTS, DesignSettings, SectionDesign


def design_settings(request):
    """Make global ``DesignSettings`` + per-section designs available
    in all templates.

    The returned dict contains:

    ``design_settings``
        The singleton ``DesignSettings`` instance (pk=1).

    ``section_designs``
        A dict mapping ``{section_name: merged_settings_dict}`` for all
        landing-page sections.
    """
    # Load the global design settings singleton.
    ds = DesignSettings.get_settings()
    context = {'design_settings': ds}

    # Load per-section design settings for the landing page.
    SectionDesign.get_or_create_defaults('landing')
    section_designs = {}

    try:
        sections = SectionDesign.objects.filter(page_name='landing')
        for s in sections:
            section_designs[s.section_name] = s.get_settings()
    except Exception:
        # If the DB is unavailable, fall back to default values so the
        # site still renders without error.
        for sec_name, sec_info in SECTION_DEFAULTS.items():
            section_designs[sec_name] = dict(sec_info.get('settings', {}))

    context['section_designs'] = section_designs
    return context
