from pathlib import Path
from django.conf import settings
from shop.models import product
import re

updated = 0

for p in product.objects.all():
    current_path = Path(settings.MEDIA_ROOT) / p.image.name

    if not current_path.exists():
        fixed_name = re.sub(r'_[A-Za-z0-9]{7}(?=\.)', '', p.image.name)
        fixed_path = Path(settings.MEDIA_ROOT) / fixed_name

        if fixed_path.exists():
            print(f"Fixing Product {p.id}")
            print(f"  {p.image.name}")
            print(f"  -> {fixed_name}")

            p.image.name = fixed_name
            p.save(update_fields=["image"])
            updated += 1

print(f"\nUpdated {updated} products.")