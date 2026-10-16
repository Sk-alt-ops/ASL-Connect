"""
Frontend URL Configuration

Provides server-rendered page preview routes.
"""

from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    path('', views.landing_preview, name='landing_preview'),
]
