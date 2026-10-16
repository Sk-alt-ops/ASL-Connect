"""
Authentication URL Configuration

Provides AJAX endpoints for registration, login, logout, profile
updates, and password changes.
"""

from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # --- Authentication ---
    path('auth/register/', views.register, name='register'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),

    # --- Profile Management ---
    path('auth/update-profile/', views.update_profile, name='update_profile'),
    path('auth/change-password/', views.change_password, name='change_password'),
]
