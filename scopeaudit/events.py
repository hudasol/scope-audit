"""Group frames into events and decide whether an event is AI negative.

An event is AI negative at threshold T only when every frame has no animal detection of
confidence T or higher. When no sequence identifier exists, frames of one camera taken
within a short interval are grouped.
"""
from __future__ import annotations

import pandas as pd

DEFAULT_GAP_SECONDS = 60


def group_by_time(media: pd.DataFrame, gap_seconds: int = DEFAULT_GAP_SECONDS) -> pd.Series:
    """Event identifiers from camera and timestamp when the data have no sequence identifier."""
    df = media.assign(_ts=pd.to_datetime(media["timestamp"], errors="coerce")).sort_values(["camera_id", "_ts"])
    new = (df["camera_id"] != df["camera_id"].shift()) | (df["_ts"].diff().dt.total_seconds() > gap_seconds)
    ids = new.cumsum()
    ev = (df["camera_id"].astype(str) + "_" + ids.astype(str)).reindex(media.index)
    return ev


def event_table(frames: pd.DataFrame, event_col: str = "event_id", conf_col: str = "conf_animal") -> pd.DataFrame:
    g = frames.groupby(event_col)
    return g.agg(n_frames=(conf_col, "size"), max_animal_conf=(conf_col, "max")).reset_index().rename(
        columns={event_col: "event_id"})


def is_negative(events: pd.DataFrame, threshold: float) -> pd.Series:
    return events["max_animal_conf"] < threshold
