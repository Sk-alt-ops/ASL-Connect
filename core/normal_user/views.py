"""
Normal User Views — Dashboard

Renders the hearing user dashboard with real-time chat,
notifications, friend management, and profile settings.
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def dashboard(request):
    """Render the hearing user's main dashboard page."""
    return render(request, 'normal_user/dashboard.html')
