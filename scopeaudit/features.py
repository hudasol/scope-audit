"""Image condition features computed on a reduced copy of the image.

The original image is never modified. Features describe recording conditions only.
They are risk categories for the audit design, not proof that an animal was missed.
"""
from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image

MAX_SIDE = 320
GRAYSCALE_SATURATION = 3.0  # mean channel spread below this marks an infrared (grayscale) frame


def load_reduced(source) -> Image.Image:
    """Open a path or bytes and return an RGB copy no larger than about 320 pixels."""
    img = Image.open(io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else source)
    size = img.size
    img.draft("RGB", (MAX_SIDE, MAX_SIDE))
    img = img.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    img.info["original_size"] = size
    return img


def image_features(img: Image.Image) -> dict:
    rgb = np.asarray(img, dtype=np.uint8)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    spread = (rgb.max(axis=2).astype(float) - rgb.min(axis=2).astype(float)).mean()
    w, h = img.info.get("original_size", img.size)
    return {
        "brightness": float(gray.mean()),
        "contrast": float(gray.std()),
        "blur": float(cv2.Laplacian(gray, cv2.CV_64F).var()),
        "underexposed": float((gray < 10).mean()),
        "overexposed": float((gray > 245).mean()),
        "saturation": float(spread),
        "night": bool(spread < GRAYSCALE_SATURATION),
        "pixels": int(w) * int(h),
    }
