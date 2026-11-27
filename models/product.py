# -*- coding: utf-8 -*-
"""Product image helpers shared by persistence and presentation layers."""

import json
from typing import Any, Dict, List


MAX_PRODUCT_IMAGES = 10


def get_images(product: Dict[str, Any]) -> List[str]:
    """Return unique product file IDs with the legacy primary image first."""
    stored_images = product.get('images') or product.get('image_ids') or []
    if isinstance(stored_images, str):
        try:
            stored_images = json.loads(stored_images)
        except (TypeError, ValueError):
            stored_images = [stored_images]
    if not isinstance(stored_images, (list, tuple)):
        stored_images = [stored_images]

    primary_image = product.get('image_id') or product.get('photo_file_id')
    ordered_images = [primary_image, *stored_images]
    images = []
    seen = set()
    for image_id in ordered_images:
        if not isinstance(image_id, str):
            continue
        image_id = image_id.strip()
        if image_id and image_id not in seen:
            images.append(image_id)
            seen.add(image_id)
        if len(images) >= MAX_PRODUCT_IMAGES:
            break
    return images
