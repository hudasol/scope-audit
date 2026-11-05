"""Deployment integrity checks.

A flag says what the data show. It never claims what happened to a camera. A long gap
between recordings is reported as "operation could not be established", because a gap
can be caused by a camera fault or by no animal passing.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

GAP_WORDING = ("A prolonged recording gap was identified. Camera operation during this period "
               "could not be established from the available data.")
MIN_GAP_DAYS = 7.0
GAP_MULTIPLE = 20.0


def check_media(media: pd.DataFrame, deployments: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return one row per flag with columns image_id, flag, detail."""
    flags = []

    def add(mask, flag, detail):
        for iid in media.loc[mask, "image_id"]:
            flags.append({"image_id": iid, "flag": flag, "detail": detail})

    add(media["camera_id"].isna(), "missing_camera_id", "The image cannot be linked to a known camera.")
    add(media["deployment_id"].isna(), "missing_deployment_id", "The image is not linked to a deployment.")
    ts = pd.to_datetime(media["timestamp"], errors="coerce")
    add(ts.isna(), "invalid_timestamp", "The timestamp is missing or cannot be parsed.")
    if "is_duplicate" in media:
        add(media["is_duplicate"].astype(bool), "duplicate_image", "An exact duplicate file was detected (same SHA 256).")
    if deployments is not None and len(deployments):
        d = deployments.set_index("deployment_id")
        start = media["deployment_id"].map(d["deployment_start"])
        end = media["deployment_id"].map(d["deployment_end"])
        add(media["deployment_id"].notna() & (start.isna() | end.isna()), "missing_deployment_dates",
            "The deployment period is unavailable.")
        outside = ts.notna() & start.notna() & end.notna() & ((ts < start) | (ts > end))
        add(outside, "timestamp_outside_deployment", "The image time is outside the recorded deployment period.")
        if {"latitude", "longitude"} <= set(d.columns):
            lat = media["deployment_id"].map(d["latitude"])
            add(media["deployment_id"].notna() & lat.isna(), "missing_coordinates",
                "Spatial analysis cannot locate the deployment.")
    out = pd.DataFrame(flags, columns=["image_id", "flag", "detail"])
    return out


def recording_gaps(media: pd.DataFrame) -> pd.DataFrame:
    """Find prolonged gaps between consecutive timestamps of a camera.

    A gap is prolonged when it exceeds MIN_GAP_DAYS and GAP_MULTIPLE times the median gap
    of that camera. The wording never states that the camera malfunctioned.
    """
    rows = []
    ts = pd.to_datetime(media["timestamp"], errors="coerce")
    df = media.assign(_ts=ts).dropna(subset=["_ts", "camera_id"]).sort_values("_ts")
    for cam, g in df.groupby("camera_id"):
        t = g["_ts"].to_numpy()
        if len(t) < 3:
            continue
        gaps = np.diff(t).astype("timedelta64[s]").astype(float) / 86400.0
        med = max(float(np.median(gaps)), 1e-6)
        for i, gap in enumerate(gaps):
            if gap >= MIN_GAP_DAYS and gap >= GAP_MULTIPLE * med:
                rows.append({"camera_id": cam, "gap_start": pd.Timestamp(t[i]), "gap_end": pd.Timestamp(t[i + 1]),
                             "gap_days": round(float(gap), 1), "statement": GAP_WORDING})
    return pd.DataFrame(rows, columns=["camera_id", "gap_start", "gap_end", "gap_days", "statement"])
