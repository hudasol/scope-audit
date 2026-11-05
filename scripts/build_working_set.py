"""Build the working set for experiment B and the small demo set.

Draws 8,000 events uniformly at random with a fixed seed from the BORROWED Caltech
Camera Traps benchmark, downloads one frame per event, computes image condition
features, and discards the image. Only features are stored. A 60 event demo subset
is kept as reduced images with attribution.

Usage: python scripts/build_working_set.py [--events 8000] [--workers 12]
"""
from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import requests

from scopeaudit import cct
from scopeaudit.features import image_features, load_reduced
from scopeaudit.sampling import rng_for

BASE = "https://storage.googleapis.com/public-datasets-lila/caltech-unzipped/cct_images/"
ROOT = Path(__file__).resolve().parents[1]
SEED = 20261106
DEMO_HIDDEN = 20
DEMO_EMPTY = 40
DEMO_THRESHOLD = 0.2


def middle_frame(frames: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ev, g in frames.groupby("event_id", sort=False):
        g = g.sort_values("frame_num")
        rows.append(g.iloc[(len(g) - 1) // 2])
    return pd.DataFrame(rows)


def fetch_one(args):
    session, file_name, keep_path = args
    for attempt in range(3):
        try:
            r = session.get(BASE + file_name, timeout=60)
            r.raise_for_status()
            img = load_reduced(r.content)
            feat = image_features(img)
            if keep_path is not None:
                from PIL import Image
                import io
                full = Image.open(io.BytesIO(r.content))
                full.draft("RGB", (640, 640))
                full = full.convert("RGB")
                full.thumbnail((640, 640))
                keep_path.parent.mkdir(parents=True, exist_ok=True)
                full.save(keep_path, "JPEG", quality=78)
            return feat
        except Exception as exc:  # network or decode problem, retry then record
            err = str(exc)
            time.sleep(1.5)
    return {"error": err}


def main(n_events: int, workers: int) -> None:
    frames = cct.load_frames()
    events = cct.to_events(frames)
    rng = rng_for(SEED, "working_set")
    pick = np.sort(rng.choice(len(events), size=n_events, replace=False))
    work = events.iloc[pick].reset_index(drop=True)
    mid = middle_frame(frames[frames["event_id"].isin(set(work["event_id"]))]).set_index("event_id")
    work["feature_frame"] = work["event_id"].map(mid["file_name"])
    work["hour"] = work["start"].dt.hour
    # Demo events: chosen by seeded draw among working events in the 0.2 negative pool.
    pool = work[work["max_animal_conf"] < DEMO_THRESHOLD]
    r2 = rng_for(SEED, "demo")
    hid = pool[pool["hit"] == 1]
    emp = pool[pool["hit"] == 0]
    demo_ids = set(hid.iloc[np.sort(r2.choice(len(hid), size=min(DEMO_HIDDEN, len(hid)), replace=False))]["event_id"]) | \
        set(emp.iloc[np.sort(r2.choice(len(emp), size=DEMO_EMPTY, replace=False))]["event_id"])
    demo_dir = ROOT / "data" / "demo" / "images"
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=workers, pool_maxsize=workers)
    session.mount("https://", adapter)
    jobs = [(session, f, (demo_dir / f"{e}.jpg") if e in demo_ids else None)
            for e, f in zip(work["event_id"], work["feature_frame"])]
    t0 = time.time()
    feats = []
    with ThreadPoolExecutor(workers) as ex:
        for i, f in enumerate(ex.map(fetch_one, jobs)):
            feats.append(f)
            if i % 500 == 0:
                print(i, round(time.time() - t0), flush=True)
    fdf = pd.DataFrame(feats)
    failed = fdf["error"].notna().sum() if "error" in fdf else 0
    out = pd.concat([work, fdf], axis=1)
    out["data_label"] = "BORROWED"
    out["is_demo"] = out["event_id"].isin(demo_ids)
    (ROOT / "data" / "working_set").mkdir(parents=True, exist_ok=True)
    out.to_csv(ROOT / "data" / "working_set" / "events_features.csv", index=False)
    print("done", len(out), "failed", int(failed), "seconds", round(time.time() - t0))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=int, default=8000)
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    main(a.events, a.workers)
