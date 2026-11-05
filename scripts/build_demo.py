"""Build the demo tables from the working set.

demo_events.csv: the 60 demo events (20 hidden animal events and 40 empty events, all AI
negative at T of 0.2), with the image file named by event identifier.
demo_registry.csv: SYNTHETIC deployment registry. Coordinates are placeholders derived
from the location number. They are not real camera positions and say so in each row.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ev = pd.read_csv(ROOT / "data" / "working_set" / "events_features.csv")
    demo = ev[ev["is_demo"]].copy()
    demo["image_file"] = demo["event_id"] + ".jpg"
    demo["image_id"] = demo["event_id"].str.replace("-", "").str[:16]
    demo["deployment_id"] = "dep_" + demo["location"].astype(str)
    demo["camera_id"] = "cam_" + demo["location"].astype(str)
    demo["timestamp"] = demo["start"]
    cols = ["event_id", "image_id", "image_file", "deployment_id", "camera_id", "timestamp", "location", "max_animal_conf",
            "hit", "species", "data_label"]
    demo[cols].sort_values("timestamp").to_csv(ROOT / "data" / "demo" / "demo_events.csv", index=False)
    allv = ev.assign(deployment_id="dep_" + ev["location"].astype(str))
    g = allv[allv["deployment_id"].isin(demo["deployment_id"])].groupby("deployment_id")
    reg = g.agg(start=("start", "min"), end=("end", "max")).reset_index()
    loc = reg["deployment_id"].str.replace("dep_", "").astype(int)
    reg["latitude"] = (24.00 + (loc % 17) * 0.037).round(4)
    reg["longitude"] = (54.20 + (loc % 23) * 0.031).round(4)
    reg["deployment_start"] = pd.to_datetime(reg["start"]).dt.floor("D") - pd.Timedelta(days=1)
    reg["deployment_end"] = pd.to_datetime(reg["end"]).dt.ceil("D") + pd.Timedelta(days=1)
    reg["camera_id"] = "cam_" + loc.astype(str)
    reg["coordinate_label"] = "SYNTHETIC placeholder, not a real camera position"
    reg[["deployment_id", "camera_id", "latitude", "longitude", "deployment_start", "deployment_end", "coordinate_label"]] \
        .to_csv(ROOT / "data" / "demo" / "demo_registry.csv", index=False)
    print(len(demo), "demo events;", len(reg), "synthetic registry rows")


if __name__ == "__main__":
    main()
