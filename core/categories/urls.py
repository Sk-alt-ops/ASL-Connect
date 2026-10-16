"""
Categories / Gestures / Symbols — URL Configuration

Maps endpoints for category, gesture, and ASL symbol CRUD operations.

Route groups:
* ``api/categories/``       — Admin CRUD for gesture categories
* ``api/gestures/``         — Admin CRUD for individual gestures
* ``api/public/``           — Read-only endpoints for the ASL dashboard
* ``api/asl-symbols/``      — List / upload finger-spelling images
"""

from django.urls import path

from . import views

app_name = "categories"

urlpatterns = [
    # ---- Categories (admin CRUD) --------------------------------------------
    path("api/categories/", views.category_list, name="category_list"),
    path("api/categories/create/", views.category_create, name="category_create"),
    path(
        "api/categories/<int:category_id>/update/",
        views.category_update,
        name="category_update",
    ),
    path(
        "api/categories/<int:category_id>/delete/",
        views.category_delete,
        name="category_delete",
    ),
    # ---- Gestures (admin CRUD) ----------------------------------------------
    path("api/gestures/", views.gesture_list, name="gesture_list"),
    path("api/gestures/create/", views.gesture_create, name="gesture_create"),
    path(
        "api/gestures/<int:gesture_id>/update/",
        views.gesture_update,
        name="gesture_update",
    ),
    path(
        "api/gestures/<int:gesture_id>/delete/",
        views.gesture_delete,
        name="gesture_delete",
    ),
    # ---- Public read-only API -----------------------------------------------
    path("api/public/categories/", views.public_categories, name="public_categories"),
    path(
        "api/public/categories/<int:category_id>/gestures/",
        views.public_gestures,
        name="public_gestures",
    ),
    # ---- ASL Symbols --------------------------------------------------------
    path("api/asl-symbols/", views.asl_symbols_list, name="asl_symbols_list"),
    path(
        "api/asl-symbols/upload/<str:symbol_type>/<str:character>/",
        views.asl_symbol_upload,
        name="asl_symbol_upload",
    ),
]
