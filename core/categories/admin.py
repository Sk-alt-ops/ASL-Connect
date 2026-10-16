"""
Admin configuration for Categories, Gestures, and ASL Symbols.

Registered with Django's admin site via the ``@admin.register`` decorator
for clean, declarative registration.
"""

from django.contrib import admin

from .models import ASLSymbol, Category, Gesture


# ==============================================================================
# Category
# ==============================================================================


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin configuration for the ``Category`` model."""

    list_display = ["name", "icon", "color", "created_at"]
    list_editable = ["icon", "color"]
    search_fields = ["name"]


# ==============================================================================
# Gesture
# ==============================================================================


@admin.register(Gesture)
class GestureAdmin(admin.ModelAdmin):
    """Admin configuration for the ``Gesture`` model."""

    list_display = ["title", "category", "translation", "created_at"]
    list_filter = ["category"]
    search_fields = ["title", "translation", "keywords"]
    autocomplete_fields = ["category"]


# ==============================================================================
# ASLSymbol
# ==============================================================================


@admin.register(ASLSymbol)
class ASLSymbolAdmin(admin.ModelAdmin):
    """Admin configuration for the ``ASLSymbol`` model."""

    list_display = ["character", "type", "created_at"]
    list_filter = ["type"]
    search_fields = ["character"]
