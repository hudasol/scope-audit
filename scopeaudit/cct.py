"""Load Caltech Camera Traps labels and MegaDetector results into an event table.

The data are BORROWED from the Southwestern United States (LILA BC, CDLA permissive).
An event is a sequence of frames that share a sequence identifier. Truth for an event
is whether any frame carries an animal label. Labels named empty and car are not
animals. The oracle reviewer in the experiments reads this truth.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
LABELS = RAW / "caltech_images_20210113.json"
MD = RAW / "caltech-camera-traps_mdv5a.0.0_results.json"
NON_ANIMAL = {"empty", "car"}
DATA_LABEL = "BORROWED: Caltech Camera Traps (LILA BC, Southwestern United States, CDLA permissive)"


def load_frames() -> pd.DataFrame:
    """One row per image with label, detector confidences and sequence information."""
    lab = json.load(open(LABELS, encoding="utf8"))
    cats = {c["id"]: c["name"] for c in lab["categories"]}
    ann = {}
    for a in lab["annotations"]:
        ann.setdefault(a["image_id"], set()).add(cats[a["category_id"]])
    rows = []
    for im in lab["images"]:
        names = ann.get(im["id"], {"empty"})
        rows.append((im["id"], im["file_name"], im["seq_id"], im["frame_num"], im["seq_num_frames"],
                     im["location"], im["date_captured"], im["width"], im["height"],
                     bool(names - NON_ANIMAL), ";".join(sorted(names - NON_ANIMAL))))
    fr = pd.DataFrame(rows, columns=["image_id", "file_name", "event_id", "frame_num", "n_frames", "location",
                                     "date_captured", "width", "height", "animal", "species"])
    md = json.load(open(MD, encoding="utf8"))
    best = {}
    for im in md["images"]:
        c_animal = 0.0
        c_person = 0.0
        c_vehicle = 0.0
        for d in im.get("detections", []):
            if d["category"] == "1":
                c_animal = max(c_animal, d["conf"])
            elif d["category"] == "2":
                c_person = max(c_person, d["conf"])
            else:
                c_vehicle = max(c_vehicle, d["conf"])
        best[im["file"]] = (c_animal, c_person, c_vehicle)
    conf = fr["file_name"].map(best)
    fr = fr[conf.notna()].copy()
    conf = conf[conf.notna()]
    fr["conf_animal"] = [c[0] for c in conf]
    fr["conf_person"] = [c[1] for c in conf]
    fr["conf_vehicle"] = [c[2] for c in conf]
    fr["date_captured"] = pd.to_datetime(fr["date_captured"], errors="coerce")
    return fr.reset_index(drop=True)


def to_events(frames: pd.DataFrame) -> pd.DataFrame:
    """One row per event with truth and the highest animal confidence of any frame."""
    g = frames.groupby("event_id", sort=True)
    ev = g.agg(location=("location", "first"), n_frames=("image_id", "size"),
               hit=("animal", "max"), max_animal_conf=("conf_animal", "max"),
               start=("date_captured", "min"), end=("date_captured", "max"),
               species=("species", lambda s: ";".join(sorted(set(";".join(s).split(";")) - {""}))))
    ev["hit"] = ev["hit"].astype(int)
    ev["data_label"] = "BORROWED"
    return ev.reset_index()


def pool(events: pd.DataFrame, T: float) -> pd.DataFrame:
    """AI negative events at threshold T: no frame has an animal detection of confidence T or higher."""
    return events[events["max_animal_conf"] < T].copy()
