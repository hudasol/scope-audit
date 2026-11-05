"""Effort aware descriptive summaries.

Only an encounter rate per valid camera day is produced, and only when deployment dates
and approved observations exist. The module makes no statement about population size,
abundance or absence. Events are counted, not individual animals.
"""
from __future__ import annotations

import pandas as pd

NOTICE = ("Encounter rates describe detections per valid camera day at the surveyed cameras. "
          "They do not describe population size or abundance, and a zero does not show absence.")


def camera_days(dep: pd.DataFrame, flagged_deployments: set | None = None) -> pd.DataFrame:
    d = dep.copy()
    d["deployment_start"] = pd.to_datetime(d["deployment_start"], errors="coerce")
    d["deployment_end"] = pd.to_datetime(d["deployment_end"], errors="coerce")
    d["camera_days"] = (d["deployment_end"] - d["deployment_start"]).dt.total_seconds() / 86400.0
    d.loc[d["camera_days"].isna() | (d["camera_days"] <= 0), "camera_days"] = float("nan")
    if flagged_deployments:
        d.loc[d["deployment_id"].isin(flagged_deployments), "camera_days"] = float("nan")
    return d[["deployment_id", "camera_days"]]


def encounter_rates(observations: pd.DataFrame, dep: pd.DataFrame, flagged_deployments: set | None = None) -> pd.DataFrame:
    """Events per valid camera day for each deployment and taxon (human approved observations only)."""
    if observations is None or not len(observations):
        return pd.DataFrame(columns=["deployment_id", "scientific_name", "events", "camera_days", "events_per_100_camera_days"])
    cd = camera_days(dep, flagged_deployments)
    ev = (observations.dropna(subset=["scientific_name"]).groupby(["deployment_id", "scientific_name"])["event_id"]
          .nunique().rename("events").reset_index())
    out = ev.merge(cd, on="deployment_id", how="left")
    out["events_per_100_camera_days"] = 100.0 * out["events"] / out["camera_days"]
    return out
