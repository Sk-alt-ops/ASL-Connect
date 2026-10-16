"""
Normal User URL Configuration

Routes for the hearing user dashboard.
"""

from django.urls import path
from . import views

app_name = 'normal_user'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
]
