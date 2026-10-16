import os
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image

from core.categories.models import ASLSymbol


class Command(BaseCommand):
    help = "Convert ASL symbol JPEG images to WebP format for smaller size"

    def handle(self, *args, **options):
        count = 0
        skipped = 0
        for symbol in ASLSymbol.objects.all():
            if not symbol.image:
                skipped += 1
                continue
            path = symbol.image.path
            if path.lower().endswith(".webp"):
                skipped += 1
                continue
            try:
                img = Image.open(path)
                img = img.convert("RGB")
                webp_io = BytesIO()
                img.save(webp_io, format="WEBP", quality=85)
                webp_name = os.path.splitext(os.path.basename(path))[0] + ".webp"
                symbol.image.save(webp_name, ContentFile(webp_io.getvalue()), save=True)
                os.remove(path)
                self.stdout.write(f"  Converted {path} -> {symbol.image.path}")
                count += 1
            except Exception as e:
                self.stderr.write(f"  Error converting {path}: {e}")
                skipped += 1
        self.stdout.write(
            self.style.SUCCESS(f"Done. Converted {count}, skipped {skipped}")
        )
