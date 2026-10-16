"""
ASL Content Models — Categories, Gestures, and Alphabet/Number Symbols

These models form the core ASL learning and communication content:

* ``Category`` —— Groups related gestures (e.g. "Greetings", "Food")
* ``Gesture``  —— A specific ASL sign with video, translation and keywords
* ``ASLSymbol`` —— A-Z alphabet and 0-9 number hand-sign images for the
  ASL keyboard used in chat composition
"""

from django.db import models
from django.db.models import Count


# ==============================================================================
# Custom QuerySets
# ==============================================================================


class CategoryQuerySet(models.QuerySet):
    """Reusable queryset methods for ``Category`` models."""

    def with_gesture_count(self):
        """Annotate each category with the count of related gestures."""
        return self.annotate(gesture_count=Count("gestures"))


class GestureQuerySet(models.QuerySet):
    """Reusable queryset methods for ``Gesture`` models."""

    def with_category(self):
        """Eagerly load the related category to avoid N+1 queries."""
        return self.select_related("category")

    def by_category(self, category_id):
        """Filter gestures belonging to a specific category."""
        return self.filter(category_id=category_id)


# ==============================================================================
# Category
# ==============================================================================


class Category(models.Model):
    """
    Groups ASL gestures into named, themed categories.

    Each category carries an icon (Tabler CSS class) and a colour for
    visual identification in the category-selector UI.
    Example categories: "Greetings", "Common Phrases", "Emergency".
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text='Display name for the gesture category (e.g. "Greetings", "Food").',
        verbose_name="Category Name",
    )
    icon = models.CharField(
        max_length=50,
        default="ti ti-hand-stop",
        help_text="Tabler icon CSS class for the category's visual icon in the selector.",
        verbose_name="Icon Class",
    )
    color = models.CharField(
        max_length=20,
        default="#3b82f6",
        help_text="Hex colour code for the category badge and highlight.",
        verbose_name="Colour",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the category was created.",
        verbose_name="Created At",
    )

    objects = CategoryQuerySet.as_manager()

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Category id={self.id} name={self.name!r}>"


# ==============================================================================
# Gesture
# ==============================================================================


class Gesture(models.Model):
    """
    A specific ASL sign / gesture with video demonstration.

    Each gesture belongs to a ``Category`` and includes a title, an English
    translation, comma-separated keywords for search matching, and a video
    file showing the sign being performed.

    Gestures are matched to text input via the translation engine
    (``translation.utils.find_gesture_match``) for normal-to-ASL translation.
    """

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="gestures",
        help_text="The category this gesture belongs to.",
        verbose_name="Category",
    )
    title = models.CharField(
        max_length=200,
        help_text='The name / title of this gesture (e.g. "Hello", "Thank You").',
        verbose_name="Gesture Title",
    )
    translation = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="English text translation of this gesture. "
        "Used by the translation engine for ASL<->text matching.",
        verbose_name="Translation",
    )
    keywords = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Comma-separated keywords for matching this gesture to text input.",
        verbose_name="Keywords",
    )
    video = models.FileField(
        upload_to="gesture_videos/",
        blank=True,
        null=True,
        help_text="Video demonstration of the gesture being performed.",
        verbose_name="Gesture Video",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the gesture was added.",
        verbose_name="Created At",
    )

    objects = GestureQuerySet.as_manager()

    class Meta:
        ordering = ["title"]
        verbose_name = "Gesture"
        verbose_name_plural = "Gestures"

    def __str__(self):
        return self.title

    def __repr__(self):
        return f"<Gesture id={self.id} title={self.title!r}>"


# ==============================================================================
# ASLSymbol
# ==============================================================================


class ASLSymbol(models.Model):
    """
    Stores individual ASL finger-spelling images for the ASL keyboard.

    Covers all 26 alphabet letters (A-Z) and 10 digits (0-9) with
    corresponding hand-sign images. These are used by the ASL keyboard
    UI component and the text-to-ASL translation engine.

    Each symbol is uniquely identified by its ``type`` + ``character``
    combination.
    """

    SYMBOL_TYPES = [
        ("alphabet", "Alphabet"),
        ("number", "Number"),
    ]

    type = models.CharField(
        max_length=10,
        choices=SYMBOL_TYPES,
        help_text="Whether this is an alphabet letter (A-Z) or a number (0-9).",
        verbose_name="Symbol Type",
    )
    character = models.CharField(
        max_length=2,
        help_text="The character this symbol represents (single letter A-Z or digit 0-9).",
        verbose_name="Character",
    )
    image = models.ImageField(
        upload_to="asl_symbols/",
        help_text="Image showing the ASL hand-sign for this character.",
        verbose_name="Symbol Image",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the symbol image was uploaded.",
        verbose_name="Created At",
    )

    class Meta:
        unique_together = ["type", "character"]
        ordering = ["character"]
        verbose_name = "ASL Symbol"
        verbose_name_plural = "ASL Symbols"

    def __str__(self):
        return f"{self.get_type_display()}: {self.character}"

    def __repr__(self):
        return f"<ASLSymbol id={self.id} type={self.type!r} char={self.character!r}>"
