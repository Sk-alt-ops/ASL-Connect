"""
Translation API URL Configuration

Provides REST endpoints for converting between English text
and ASL symbol/finger-spelling representations.

Endpoints:
- POST api/text-to-asl/   — Convert text to ASL symbol images
- POST api/asl-to-text/   — Convert ASL symbols back to text
"""

from django.urls import path
from . import views

urlpatterns = [
    path('api/text-to-asl/', views.TranslateTextToASL.as_view(), name='translate-text-to-asl'),
    path('api/asl-to-text/', views.TranslateASLToText.as_view(), name='translate-asl-to-text'),
]
