"""Synthetic populations of AI negative events with known truth.

Everything produced here is SYNTHETIC. It is used to validate the estimators and
intervals against a known false omission rate, never to say anything about real
animals or real detectors.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .sampling import rng_for
from .strata import confidence_bins

LABEL = "SYNTHETIC"

# Share of events and base hit rate by confidence bin for threshold 0.4.
BIN_SHARE = np.array([0.62, 0.14, 0.08, 0.08, 0.08])
BIN_HIT = np.array([0.002, 0.006, 0.02, 0.05, 0.12])
BIN_MIDPOINT_CONF = np.array([0.0, 0.025, 0.075, 0.15, 0.3])
BIN_LABELS = ["none", "(0,0.05]", "(0.05,0.1]", "(0.1,0.2]", "(0.2,0.4]"]
COND_SHARE = {"normal": 0.55, "night": 0.2, "low_light": 0.1, "high_blur": 0.1, "low_resolution": 0.05}
COND_MULT = {"normal": 1.0, "night": 1.4, "low_light": 1.2, "high_blur": 1.1, "low_resolution": 1.0}


def make_population(scale: float, N: int = 8000, seed: int = 11) -> pd.DataFrame:
    """Synthetic negative pool. scale multiplies every hit rate (SYNTHETIC)."""
    rng = rng_for(seed, "synthetic", scale)
    b = rng.choice(len(BIN_SHARE), size=N, p=BIN_SHARE)
    conds = list(COND_SHARE)
    c = rng.choice(len(conds), size=N, p=list(COND_SHARE.values()))
    cond = np.array(conds, dtype=object)[c]
    mult = np.array([COND_MULT[k] for k in cond])
    p = np.clip(BIN_HIT[b] * mult * scale, 0, 0.9)
    hit = (rng.random(N) < p).astype(int)
    return pd.DataFrame({
        "event_id": [f"syn{seed}_{i:05d}" for i in range(N)],
        "hit": hit,
        "conf_bin": np.array(BIN_LABELS, dtype=object)[b],
        "conf_mid": BIN_MIDPOINT_CONF[b],
        "cond": cond,
        "night": cond == "night",
        "data_label": LABEL,
    })
