"""
Categories, Gestures, and ASL Symbols — CRUD Views

All HTTP view handlers for the ``core.categories`` app. Endpoints are grouped
into four sections:

1. **Categories** — CRUD for gesture categories (staff-only for mutations)
2. **Gestures**   — CRUD for individual ASL signs (staff-only for mutations)
3. **Public API** — Read-only endpoints for the ASL user dashboard
4. **ASL Symbols** — List / upload finger-spelling images (staff-only upload)

Every view requires authentication (``@login_required``) and returns JSON.
"""

import json

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import ASLSymbol, Category, Gesture
from core.notifications.views import create_notification

User = get_user_model()


# ==============================================================================
# Internal helpers
# ==============================================================================


def _staff_required(user):
    """Return ``True`` when *user* has staff or superuser privileges."""
    return user.is_superuser or user.is_staff


def _error(message, status=400):
    """Return a ``JsonResponse`` with the standard error envelope."""
    return JsonResponse({"success": False, "error": message}, status=status)


def _json_body(request):
    """Parse ``request.body`` as JSON; return the dict or ``None``."""
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return None


def _serialize_category(category, *, include_timestamp=False, include_gesture_count=False):
    """
    Serialize a ``Category`` instance to a JSON-safe dictionary.

    Parameters
    ----------
    category : Category
        The model instance to serialize.
    include_timestamp : bool
        When ``True``, include ``created_at`` (formatted string).
    include_gesture_count : bool
        When ``True``, include ``gesture_count``. Prefers an annotated value
        (``category.gesture_count``) and falls back to a fresh query.
    """
    data = {
        "id": category.id,
        "name": category.name,
        "icon": category.icon,
        "color": category.color,
    }
    if include_gesture_count:
        count = getattr(category, "gesture_count", None)
        data["gesture_count"] = count if count is not None else category.gestures.count()
    if include_timestamp:
        data["created_at"] = category.created_at.strftime("%Y-%m-%d %H:%M:%S")
    return data


def _serialize_gesture(gesture, *, include_category=False, include_timestamp=False):
    """
    Serialize a ``Gesture`` instance to a JSON-safe dictionary.

    Parameters
    ----------
    gesture : Gesture
        The model instance to serialize.
    include_category : bool
        When ``True``, include ``category_id`` and ``category_name``.
    include_timestamp : bool
        When ``True``, include ``created_at`` (formatted string).
    """
    data = {
        "id": gesture.id,
        "title": gesture.title,
        "translation": gesture.translation,
        "keywords": gesture.keywords,
        "video_url": gesture.video.url if gesture.video else None,
    }
    if include_category:
        data["category_id"] = gesture.category_id
        data["category_name"] = gesture.category.name
    if include_timestamp:
        data["created_at"] = gesture.created_at.strftime("%Y-%m-%d %H:%M:%S")
    return data


def _serialize_asl_symbol(symbol):
    """
    Serialize an ``ASLSymbol`` instance to a JSON-safe dictionary.
    """
    return {
        "id": symbol.id,
        "type": symbol.type,
        "character": symbol.character,
        "image_url": symbol.image.url,
    }


# ==============================================================================
# Categories — CRUD
# ==============================================================================


@login_required
def category_list(request):
    """
    List all gesture categories with gesture counts and timestamps.

    **Access:** Any authenticated user.
    """
    categories = Category.objects.with_gesture_count()
    return JsonResponse({
        "success": True,
        "categories": [
            _serialize_category(c, include_timestamp=True, include_gesture_count=True)
            for c in categories
        ],
    })


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def category_create(request):
    """
    Create a new gesture category.

    **Access:** Staff / superuser only.
    **Body:** JSON with ``name`` (required), ``icon``, ``color``.
    """
    if not _staff_required(request.user):
        return _error("Unauthorized", 403)

    data = _json_body(request)
    if not data:
        return _error("Invalid JSON")

    name = data.get("name", "").strip()
    if not name:
        return _error("Category name is required")
    if Category.objects.filter(name__iexact=name).exists():
        return _error("Category with this name already exists")

    category = Category.objects.create(
        name=name,
        icon=data.get("icon", "ti ti-hand-stop"),
        color=data.get("color", "#3b82f6"),
    )
    return JsonResponse({
        "success": True,
        "category": _serialize_category(category, include_timestamp=True),
    })


@login_required
@csrf_exempt
@require_http_methods(["PUT"])
def category_update(request, category_id):
    """
    Update an existing gesture category.

    **Access:** Staff / superuser only.
    **Body:** JSON with any of ``name``, ``icon``, ``color``.
    """
    if not _staff_required(request.user):
        return _error("Unauthorized", 403)

    category = get_object_or_404(Category, id=category_id)
    data = _json_body(request)
    if not data:
        return _error("Invalid JSON")

    name = data.get("name", "").strip()
    if name:
        if Category.objects.filter(name__iexact=name).exclude(id=category_id).exists():
            return _error("Category with this name already exists")
        category.name = name
    if "icon" in data:
        category.icon = data["icon"]
    if "color" in data:
        category.color = data["color"]
    category.save()

    return JsonResponse({"success": True})


@login_required
@csrf_exempt
@require_http_methods(["DELETE"])
def category_delete(request, category_id):
    """
    Delete a category and all gestures associated with it (cascade).

    **Access:** Staff / superuser only.
    """
    if not _staff_required(request.user):
        return _error("Unauthorized", 403)

    category = get_object_or_404(Category, id=category_id)
    category.delete()
    return JsonResponse({"success": True})


# ==============================================================================
# Gestures — CRUD
# ==============================================================================


@login_required
def gesture_list(request):
    """
    List gestures, optionally filtered by ``?category_id=``.

    **Access:** Any authenticated user.
    """
    category_id = request.GET.get("category_id")
    gestures = Gesture.objects.with_category()
    if category_id:
        gestures = gestures.by_category(category_id)

    return JsonResponse({
        "success": True,
        "gestures": [
            _serialize_gesture(g, include_category=True, include_timestamp=True)
            for g in gestures
        ],
    })


@login_required
@csrf_exempt
def gesture_create(request):
    """
    Create a new gesture with an optional video upload.

    Notifies all non-staff users about the new gesture.

    **Access:** Staff / superuser only.
    **Body:** Multipart form with ``translation``, ``category_id``,
             and optionally ``video`` (file).
    """
    if not _staff_required(request.user):
        return _error("Unauthorized", 403)
    if request.method != "POST":
        return _error("POST required", 405)

    translation = request.POST.get("translation", "").strip()
    category_id = request.POST.get("category_id")
    if not translation:
        return _error("Translation is required")
    if not category_id:
        return _error("Category is required")

    category = get_object_or_404(Category, id=category_id)
    gesture = Gesture.objects.create(
        category=category,
        title=translation,
        translation=translation,
        video=request.FILES.get("video"),
    )

    # Notify all non-admin users about the newly added gesture.
    users = User.objects.exclude(is_staff=True).exclude(is_superuser=True)
    for user in users:
        create_notification(
            user=user,
            type="new_gesture",
            title=f"New Gesture: {gesture.title}",
            message=(
                f'A new gesture "{gesture.title}" has been added '
                f'to the "{category.name}" category.'
            ),
            link="/dashboard/",
            icon="ti ti-hand-gesture",
        )

    return JsonResponse({
        "success": True,
        "gesture": _serialize_gesture(gesture, include_category=True),
    })


@login_required
@csrf_exempt
@require_http_methods(["PUT"])
def gesture_update(request, gesture_id):
    """
    Update a gesture's title, translation, keywords, or category.

    **Access:** Staff / superuser only.
    **Body:** JSON with any of ``title``, ``translation``, ``keywords``,
             ``category_id``.
    """
    if not _staff_required(request.user):
        return _error("Unauthorized", 403)

    gesture = get_object_or_404(Gesture, id=gesture_id)
    data = _json_body(request)
    if not data:
        return _error("Invalid JSON")

    if "title" in data:
        gesture.title = data["title"].strip() or gesture.title
    if "translation" in data:
        gesture.translation = data["translation"].strip()
    if "keywords" in data:
        gesture.keywords = data["keywords"].strip()
    if "category_id" in data:
        gesture.category = get_object_or_404(Category, id=data["category_id"])
    gesture.save()

    return JsonResponse({"success": True})


@login_required
@csrf_exempt
@require_http_methods(["DELETE"])
def gesture_delete(request, gesture_id):
    """
    Delete a single gesture.

    **Access:** Staff / superuser only.
    """
    if not _staff_required(request.user):
        return _error("Unauthorized", 403)

    gesture = get_object_or_404(Gesture, id=gesture_id)
    gesture.delete()
    return JsonResponse({"success": True})


# ==============================================================================
# Public API — read-only (no staff required)
# ==============================================================================


@login_required
def public_categories(request):
    """
    Public read-only list of categories for the ASL user dashboard.

    **Access:** Any authenticated user (no staff privileges needed).
    """
    categories = Category.objects.with_gesture_count()
    return JsonResponse({
        "success": True,
        "categories": [
            _serialize_category(c, include_gesture_count=True)
            for c in categories
        ],
    })


@login_required
def public_gestures(request, category_id):
    """
    Public read-only list of gestures within a specific category.

    **Access:** Any authenticated user (no staff privileges needed).
    """
    category = get_object_or_404(Category, id=category_id)
    gestures = category.gestures.all()

    return JsonResponse({
        "success": True,
        "category": _serialize_category(category),
        "gestures": [_serialize_gesture(g) for g in gestures],
    })


# ==============================================================================
# ASL Symbols — list & upload
# ==============================================================================


@login_required
def asl_symbols_list(request):
    """
    List all ASL alphabet / number finger-spelling symbol images.

    **Access:** Any authenticated user.
    """
    symbols = ASLSymbol.objects.all()
    return JsonResponse({
        "success": True,
        "symbols": [_serialize_asl_symbol(s) for s in symbols],
    })


@login_required
@csrf_exempt
def asl_symbol_upload(request, symbol_type, character):
    """
    Upload or update an ASL symbol image by type and character.

    Uses ``update_or_create`` so uploading the same type+character
    replaces the previous image.

    **Access:** Staff / superuser only.
    **Body:** Multipart form with ``image`` (file).
    """
    if not _staff_required(request.user):
        return _error("Unauthorized", 403)
    if request.method != "POST":
        return _error("POST required", 405)

    image = request.FILES.get("image")
    if not image:
        return _error("Image file is required")

    symbol, created = ASLSymbol.objects.update_or_create(
        type=symbol_type,
        character=character.upper(),
        defaults={"image": image},
    )
    return JsonResponse({
        "success": True,
        "symbol": _serialize_asl_symbol(symbol),
    })
