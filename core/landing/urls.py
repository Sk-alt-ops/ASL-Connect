"""
Landing Page URL Configuration

Routes for the public home page, contact form AJAX endpoint,
and dashboard data API.
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # --- Public Pages ---
    path('', views.index, name='index'),

    # --- Contact ---
    path('contact/submit/', views.contact_submit, name='contact_submit'),

    # --- API ---
    path('api/dashboard/', views.get_dashboard_data, name='dashboard_data'),
]
