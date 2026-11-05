"""Ingestion: preserve the original image, hash it and record its metadata.

The original image is never overwritten, resized or enhanced. A SHA 256 hash is stored
for every file so that exact duplicates are found and integrity can be verified later.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
from PIL import Image

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
REQUIRED = ["camera_id", "deployment_id", "timestamp"]


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _exif_datetime(img: Image.Image):
    try:
        exif = img.getexif()
        raw = exif.get(36867) or exif.get(306) or exif.get(0x9003)
        if raw:
            return pd.to_datetime(str(raw), format="%Y:%m:%d %H:%M:%S", errors="coerce")
    except Exception:
        pass
    return pd.NaT


def scan_images(folder, dataset_source: str) -> pd.DataFrame:
    """Hash and describe every image under a folder. Files that cannot be opened are recorded as invalid."""
    rows = []
    for p in sorted(Path(folder).rglob("*")):
        if p.suffix.lower() not in IMAGE_SUFFIXES or not p.is_file():
            continue
        rec = {"image_id": None, "original_filename": p.name, "path": str(p), "sha256": sha256_file(p),
               "file_size": p.stat().st_size, "dataset_source": dataset_source, "valid": True,
               "width": None, "height": None, "format": None, "exif_timestamp": pd.NaT}
        try:
            with Image.open(p) as im:
                im.verify()
            with Image.open(p) as im:
                rec.update(width=im.width, height=im.height, format=im.format, exif_timestamp=_exif_datetime(im))
        except Exception:
            rec["valid"] = False
        rec["image_id"] = rec["sha256"][:16]
        rows.append(rec)
    df = pd.DataFrame(rows)
    if len(df):
        df["duplicate_of"] = df.groupby("sha256")["image_id"].transform("first")
        df["is_duplicate"] = df.duplicated("sha256", keep="first")
    return df


def attach_metadata(images: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    """Join camera and deployment metadata on original_filename (CSV columns: original_filename, camera_id, deployment_id, timestamp)."""
    out = images.merge(meta, on="original_filename", how="left", suffixes=("", "_meta"))
    out["timestamp"] = pd.to_datetime(out.get("timestamp"), errors="coerce")
    out["timestamp"] = out["timestamp"].fillna(out["exif_timestamp"])
    return out


def summary(images: pd.DataFrame, flags: pd.DataFrame | None = None) -> dict:
    """Counts shown to the user at the end of ingestion."""
    total = int(len(images))
    valid = int(images["valid"].sum()) if total else 0
    dup = int(images["is_duplicate"].sum()) if total else 0
    incomplete = int(images[REQUIRED].isna().any(axis=1).sum()) if total and all(c in images for c in REQUIRED) else total
    inconsistent = int(flags["image_id"].nunique()) if flags is not None and len(flags) else 0
    ready = valid - dup - incomplete if total else 0
    return {"total_images": total, "valid_images": valid, "duplicate_files": dup,
            "incomplete_metadata": incomplete, "deployment_inconsistencies": inconsistent,
            "ready_for_ai_processing": max(int(ready), 0), "requiring_data_correction": int(total - max(ready, 0))}
