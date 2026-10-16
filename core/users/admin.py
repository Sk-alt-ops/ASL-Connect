"""
Admin Registration for the Custom User Model.

Registers the ``User`` model with Django's built-in ``UserAdmin``
for full admin interface support.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

admin.site.register(User, UserAdmin)
