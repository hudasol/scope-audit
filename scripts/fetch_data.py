"""Download the Caltech Camera Traps labels and the published MegaDetector results.

Source: LILA BC (https://lila.science/datasets/caltech-camera-traps), released under the
Community Data License Agreement (permissive variant). The data are BORROWED from the
Southwestern United States and are used only as a method benchmark.

Usage: python scripts/fetch_data.py
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import requests

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
FILES = {
    "labels": ("https://storage.googleapis.com/public-datasets-lila/caltechcameratraps/labels/caltech_camera_traps.json.zip",
               "caltech_images_20210113.json"),
    "md_results": ("https://lila.science/public/lila-md-results/caltech-camera-traps_mdv5a.0.0_results.json.zip",
                   "caltech-camera-traps_mdv5a.0.0_results.json"),
}


def fetch() -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    out = {}
    for key, (url, member) in FILES.items():
        target = RAW / member
        if not target.exists():
            zpath = RAW / (member + ".zip")
            r = requests.get(url, timeout=180)
            r.raise_for_status()
            zpath.write_bytes(r.content)
            with zipfile.ZipFile(zpath) as z:
                z.extract(member, RAW)
            zpath.unlink()
        out[key] = target
    return out


if __name__ == "__main__":
    for k, v in fetch().items():
        print(k, v, v.stat().st_size)
    sys.exit(0)
