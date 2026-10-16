"""
ASL User — Django Admin Configuration.

This app does not register any models with the Django admin site.
All relevant models (User, Chat, Friends, Notifications, etc.) are
registered by their respective apps for better separation of concerns.

If custom models are added to this app in the future, register them
here using the @admin.register decorator pattern.
"""

# from django.contrib import admin
# Register your models here.
