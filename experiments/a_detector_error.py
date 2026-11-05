"""Experiment A: detector error on the BORROWED Caltech Camera Traps benchmark.

Uses labels and published MegaDetector v5a results only (no images). Reports, for each
threshold in the sweep, the event level and image level false omission rate, the event
level recall and false negative rate, and the size of the negative pool.

Important: Caltech Camera Traps is part of the public training data of earlier
MegaDetector versions, so the error rates here are likely optimistic. They are reported
to size the audit problem and to check statistical power, not as expected field performance.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from scopeaudit import cct
from scopeaudit.results_io import header, write

SWEEP = [0.1, 0.2, 0.4, 0.6, 0.8]
STRESS_FOR_MIN = 0.02
POWER_MIN_HIDDEN = 30


def stress_threshold(rows: list) -> float:
    """Rule fixed before the experiment: smallest threshold with event FOR of at least 2 percent, else the largest."""
    for r in rows:
        if r["event_for"] >= STRESS_FOR_MIN:
            return r["threshold"]
    return rows[-1]["threshold"]


def main() -> None:
    frames = cct.load_frames()
    events = cct.to_events(frames)
    rows = []
    for T in SWEEP:
        neg = events[events["max_animal_conf"] < T]
        pos = events[events["max_animal_conf"] >= T]
        fn = int(neg["hit"].sum())
        tn = int(len(neg) - fn)
        tp = int(pos["hit"].sum())
        img_neg = frames[frames["conf_animal"] < T]
        img_fn = int(img_neg["animal"].sum())
        by_loc = neg.groupby("location")["hit"].agg(["size", "sum"])
        by_loc["rate"] = by_loc["sum"] / by_loc["size"]
        top10 = float(by_loc["sum"].sort_values(ascending=False).head(10).sum() / max(fn, 1))
        sp = neg[neg["hit"] == 1]["species"].str.split(";").explode().value_counts().head(8)
        rows.append({
            "threshold": T,
            "events_total": int(len(events)),
            "pool_size": int(len(neg)),
            "pool_share": float(len(neg) / len(events)),
            "hidden_events": fn,
            "event_for": fn / len(neg),
            "event_recall": tp / (tp + fn),
            "event_fnr": fn / (fn + tp),
            "images_total": int(len(frames)),
            "image_pool_size": int(len(img_neg)),
            "image_hidden": img_fn,
            "image_for": img_fn / len(img_neg),
            "locations_with_hidden": int((by_loc["sum"] > 0).sum()),
            "location_rate_median": float(by_loc["rate"].median()),
            "location_rate_max": float(by_loc["rate"].max()),
            "share_of_hidden_in_top10_locations": top10,
            "top_hidden_species": {k: int(v) for k, v in sp.items()},
            "underpowered_full_data": fn < POWER_MIN_HIDDEN,
        })
    stress = stress_threshold(rows)
    out = {"header": header("A_detector_error", cct.DATA_LABEL,
                            {"detector": "MegaDetector v5a.0.0 (published LILA results)",
                             "note": "Benchmark overlaps the detector training data, so error rates are optimistic.",
                             "stress_rule": "smallest threshold in the sweep with event FOR >= 2 percent, else the largest",
                             "min_hidden_for_power": POWER_MIN_HIDDEN}),
           "headline_threshold": 0.2, "stress_threshold": stress, "rows": rows,
           "frames_with_labels_and_detections": int(len(frames)), "events": int(len(events)),
           "share_events_with_animal": float(events["hit"].mean())}
    write(Path(__file__).resolve().parents[1] / "results" / "experiment_a.json", out)
    for r in rows:
        print(r["threshold"], r["pool_size"], r["hidden_events"], round(100 * r["event_for"], 3),
              round(100 * r["image_for"], 3), round(r["event_recall"], 4))
    print("stress threshold:", stress)


if __name__ == "__main__":
    main()
