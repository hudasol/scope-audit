"""Stratum definitions for the audit.

Strata are always built from information available before review: detector
confidence and image condition. No label is read when strata are defined.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CONF_EDGES = [0.0, 0.05, 0.1, 0.2, 0.4, 0.6, 0.8]


def confidence_bins(max_animal_conf, T: float):
    """Bin the highest sub threshold animal confidence of each event.

    Returns labels and bin midpoints. The label "none" marks events with no animal
    detection at all. Bins above the threshold T are never used because the pool
    holds only events whose highest animal confidence is below T.
    """
    s = np.asarray(max_animal_conf, dtype=float)
    labels = np.empty(len(s), dtype=object)
    mids = np.zeros(len(s), dtype=float)
    labels[s <= 0] = "none"
    edges = [e for e in CONF_EDGES if e < T] + [T]
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (s > lo) & (s <= hi) & (s < T)
        labels[m] = f"({lo:g},{hi:g}]"
        mids[m] = (lo + hi) / 2.0
    return labels, mids


def condition_strata(feat: pd.DataFrame) -> pd.Series:
    """Label free condition strata from image features.

    Order of priority: night, low light, high blur, low resolution, normal.
    Cut points are quantiles of the pool itself, never of the labels:
    the darkest 15 percent of non night events are low light, the blurriest 15
    percent of the rest are high blur, and the lowest 10 percent by pixel count
    of the rest are low resolution.
    """
    out = pd.Series("normal", index=feat.index, dtype=object)
    night = feat["night"].astype(bool)
    out[night] = "night"
    rest = ~night
    if rest.any():
        q = feat.loc[rest, "brightness"].quantile(0.15)
        m = rest & (feat["brightness"] <= q)
        out[m] = "low_light"
        rest = rest & ~m
    if rest.any():
        q = feat.loc[rest, "blur"].quantile(0.15)
        m = rest & (feat["blur"] <= q)
        out[m] = "high_blur"
        rest = rest & ~m
    if rest.any():
        q = feat.loc[rest, "pixels"].quantile(0.10)
        m = rest & (feat["pixels"] < q)
        out[m] = "low_resolution"
    return out
