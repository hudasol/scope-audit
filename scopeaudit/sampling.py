"""Seeded, reproducible sampling and allocation for the review audit.

Two views of the same design are provided.

1. draw_ids returns the actual event identifiers to review. The same inputs and
   seed always return the same identifiers.
2. simulate_counts returns only the number of hits found in each stratum, using
   the hypergeometric distribution. For a design that samples without
   replacement inside strata this has exactly the same distribution as drawing
   identifiers and counting hits, and it is fast enough for thousands of
   repeated audits. tests/test_sampling.py checks the equivalence.
"""
from __future__ import annotations

import zlib

import numpy as np
import pandas as pd


def rng_for(seed: int, *keys) -> np.random.Generator:
    """Generator that depends on the seed and on stable string keys."""
    salt = [zlib.crc32(str(k).encode("utf8")) for k in keys]
    return np.random.default_rng(np.random.SeedSequence([int(seed), *salt]))


def allocate(N_h, score_h, n: int, min_per: int = 2) -> np.ndarray:
    """Allocate a review budget n over strata in proportion to score_h.

    Every non empty stratum receives at least min_per events, or one event when
    the budget is too small for that. No stratum receives more than its size.
    The remaining budget is shared in proportion to the scores, by repeated water
    filling with largest remainder rounding.
    """
    N_h = np.asarray(N_h, dtype=int)
    score = np.asarray(score_h, dtype=float)
    H = len(N_h)
    n = int(min(n, N_h.sum()))
    floor_n = min_per if n >= H * min_per else min(1, min_per)
    alloc = np.minimum(N_h, floor_n).astype(int)
    if n < alloc.sum():
        raise ValueError("budget is smaller than the number of strata")
    remaining = n - int(alloc.sum())
    cap = N_h - alloc
    while remaining > 0 and (cap > 0).any():
        active = cap > 0
        s = np.where(active, score, 0.0)
        if s.sum() <= 0:
            s = active.astype(float)
        target = remaining * s / s.sum()
        add = np.minimum(np.floor(target).astype(int), cap)
        alloc += add
        cap -= add
        remaining -= int(add.sum())
        if remaining > 0:
            frac = np.where(cap > 0, target - np.floor(target), -1.0)
            for i in np.argsort(-frac, kind="stable"):
                if remaining == 0:
                    break
                if cap[i] > 0:
                    alloc[i] += 1
                    cap[i] -= 1
                    remaining -= 1
    return alloc


def draw_ids(df: pd.DataFrame, strata_cols, alloc_by_stratum: dict, seed: int, tag: str) -> list:
    """Draw review identifiers without replacement inside each stratum.

    df needs an event_id column. strata_cols is a column name or a list of names.
    alloc_by_stratum maps a stratum key to the number of events to draw.
    """
    cols = [strata_cols] if isinstance(strata_cols, str) else list(strata_cols)
    out = []
    for key, grp in df.groupby(cols, sort=True):
        if len(cols) == 1 and isinstance(key, tuple):
            key = key[0]
        k = int(alloc_by_stratum.get(key, 0))
        if k <= 0:
            continue
        ids = np.sort(grp["event_id"].to_numpy())
        rng = rng_for(seed, tag, "|".join(map(str, key if isinstance(key, tuple) else (key,))))
        pick = rng.choice(len(ids), size=min(k, len(ids)), replace=False)
        out.extend(ids[np.sort(pick)].tolist())
    return sorted(out)


def simple_random_ids(df: pd.DataFrame, n: int, seed: int, tag: str = "srs") -> list:
    ids = np.sort(df["event_id"].to_numpy())
    rng = rng_for(seed, tag)
    pick = rng.choice(len(ids), size=min(n, len(ids)), replace=False)
    return sorted(ids[pick].tolist())


def simulate_counts(N_h, K_h, n_h, S: int, rng: np.random.Generator) -> np.ndarray:
    """Hits found per stratum for S repeated audits, drawn from the hypergeometric."""
    N_h = np.asarray(N_h, dtype=np.int64)
    K_h = np.asarray(K_h, dtype=np.int64)
    n_h = np.asarray(n_h, dtype=np.int64)
    return rng.hypergeometric(K_h, N_h - K_h, n_h, size=(S, len(N_h)))
