"""
Frontend Views — Landing Preview

Provides a server-rendered preview of the landing page for design
review and embedding into iframes (same-origin only).
"""

from django.shortcuts import render


def landing_preview(request):
    """
    Render the landing page in preview mode for design review.

    Sets ``X-Frame-Options: SAMEORIGIN`` so the page can be embedded
    in iframes on the same origin (e.g., for an admin preview panel).
    """
    response = render(request, 'landing.html', {'is_preview': True})
    response['X-Frame-Options'] = 'SAMEORIGIN'
    return response
