from django.core.management.base import BaseCommand
from shop.models import Product
from django.conf import settings
from django.core.files import File
import os


class Command(BaseCommand):
    help = "Upload existing product images to Cloudinary"

    def handle(self, *args, **options):
        from django.conf import settings
        from django.core.files import File
        import os

        for prod in Product.objects.exclude(image=""):
            local_path = os.path.join(settings.BASE_DIR, "media", prod.image.name)

            if not os.path.exists(local_path):
                self.stdout.write(
                    self.style.WARNING(f"Missing: {local_path}")
                )
                continue

            self.stdout.write(f"Uploading: {prod.prod_name}")

            with open(local_path, "rb") as f:
                prod.image.save(
                    os.path.basename(local_path),
                    File(f),
                    save=True,
                )

        self.stdout.write(
            self.style.SUCCESS("✅ All images uploaded successfully!")
        )
