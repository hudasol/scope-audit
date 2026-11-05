"""Plan and evaluate a false omission audit of AI negative events.

The pool holds the events the detector called negative at threshold T. plan() chooses
which events a human reviews. estimate() turns the review outcomes into an estimate of
the false omission rate FOR with an interval, and reports sensitivity bounds when some
reviews are unresolved. Strata use only information available before review.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import estimators as est
from .mc import RISK_OFFSET, SCHEMES
from .sampling import allocate, draw_ids, rng_for, simple_random_ids
from .strata import confidence_bins, condition_strata

DEFAULT_INTERVAL = "wald_smoothed"  # post hoc choice, see DECISIONS.md entry 10
SRS_INTERVAL = "wilson_fpc"
METHOD_NAMES = {"M0": "Simple random sample", "M1": "Condition strata (proportional)",
                "M2": "Detector confidence strata, risk weighted", "M3": "Confidence by day or night, risk weighted"}


def build_pool(events: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """AI negative events at the threshold with strata columns. events needs event_id and max_animal_conf."""
    pool = events[events["max_animal_conf"] < threshold].copy()
    lab, mid = confidence_bins(pool["max_animal_conf"].to_numpy(), threshold)
    pool["conf_bin"], pool["conf_mid"] = lab, mid
    if "night" in pool.columns:
        pool["night"] = pool["night"].astype(bool)
    if {"brightness", "blur", "pixels", "night"} <= set(pool.columns):
        pool["cond"] = condition_strata(pool)
    return pool.reset_index(drop=True)


def _strata_cols(scheme: str):
    return SCHEMES[scheme].get("cols", [])


def plan(pool: pd.DataFrame, scheme: str, budget: int, seed: int) -> dict:
    """Allocation and the identifiers to review. Same inputs and seed always give the same identifiers."""
    budget = int(min(budget, len(pool)))
    if scheme == "M0":
        ids = simple_random_ids(pool, budget, seed, tag="M0")
        return {"scheme": scheme, "budget": budget, "seed": seed, "event_ids": ids, "allocation": {"all": len(ids)}}
    if scheme not in SCHEMES or SCHEMES[scheme]["kind"] != "strat":
        raise ValueError(f"Scheme {scheme} is not available for a live audit.")
    cols = _strata_cols(scheme)
    g = pool.groupby(cols, sort=True).agg(N=("event_id", "size"), mid=("conf_mid", "mean")).reset_index()
    N_h = g["N"].to_numpy(dtype=np.int64)
    score = N_h.astype(float) if SCHEMES[scheme]["alloc"] == "proportional" else N_h * (g["mid"].to_numpy() + RISK_OFFSET)
    a = allocate(N_h, score, budget)
    key = (lambda r: r[cols[0]]) if len(cols) == 1 else (lambda r: tuple(r[c] for c in cols))
    alloc = {key(r): int(k) for (_, r), k in zip(g.iterrows(), a)}
    ids = draw_ids(pool, cols, alloc, seed, tag=scheme)
    return {"scheme": scheme, "budget": budget, "seed": seed, "event_ids": ids,
            "allocation": {str(k): v for k, v in alloc.items()}}


def estimate(pool: pd.DataFrame, scheme: str, reviews: pd.DataFrame, seed: int = 0, B: int = 4000) -> dict:
    """reviews: event_id, outcome in {animal, empty, unresolved}. Returns estimate, intervals and bounds."""
    r = reviews.drop_duplicates("event_id", keep="last").merge(pool, on="event_id", how="inner")
    n_rev = len(r)
    if n_rev == 0:
        raise ValueError("No reviewed events.")
    hit = (r["outcome"] == "animal").astype(int)
    unres = (r["outcome"] == "unresolved").astype(int)
    rng = rng_for(seed, "estimate", scheme)
    out = {"scheme": scheme, "pool_size": int(len(pool)), "reviewed": int(n_rev),
           "hidden_found": int(hit.sum()), "unresolved": int(unres.sum()),
           "yield_per_100_reviews": 100.0 * float(hit.sum()) / n_rev}
    resolved = r[unres == 0].assign(hit_=hit[unres == 0])
    if scheme == "M0":
        n, x = len(resolved), int(resolved["hit_"].sum())
        if n == 0:
            raise ValueError("All reviews are unresolved.")
        p, lo, hi = est.wilson_fpc(np.array([x]), n, len(pool))
        out.update(estimate=float(p[0]), interval={"wilson_fpc": [float(lo[0]), float(hi[0])]})
        _, bl, bh = est.strat_bayes(np.array([len(pool)]), np.array([[n]]), np.array([[x]]), rng, B=B)
        out["interval"]["bayes_jeffreys"] = [float(bl[0]), float(bh[0])]
        if out["unresolved"]:
            xu = int(resolved["hit_"].sum())
            out["sensitivity"] = {"lower_bound": xu / (n + out["unresolved"]),
                                  "upper_bound": (xu + out["unresolved"]) / (n + out["unresolved"])}
        return out
    cols = _strata_cols(scheme)
    tab = pool.groupby(cols, sort=True).size().rename("N").reset_index()
    rv = r.assign(hit_=hit.to_numpy(), unres_=unres.to_numpy())
    agg = rv.groupby(cols, sort=True).agg(n=("event_id", "size"), x=("hit_", "sum"), u=("unres_", "sum")).reset_index()
    tab = tab.merge(agg, on=cols, how="left").fillna({"n": 0, "x": 0, "u": 0})
    keep = tab["n"] - tab["u"] > 0
    if not keep.any():
        raise ValueError("All reviews are unresolved.")
    N_h = tab["N"].to_numpy(dtype=np.int64)
    n_res = (tab["n"] - tab["u"]).to_numpy(dtype=np.int64)
    x_h = tab["x"].to_numpy(dtype=np.int64)
    if (n_res == 0).any():
        out["note"] = "Some strata have no resolved review; the estimate covers the reviewed strata only."
        N_use, n_use, x_use = N_h[n_res > 0], n_res[n_res > 0], x_h[n_res > 0]
    else:
        N_use, n_use, x_use = N_h, n_res, x_h
    p = float(est.strat_point(N_use[None, :], n_use[None, :], x_use[None, :])[0])
    ci = {}
    for name, sm in (("wald_plugin", False), ("wald_smoothed", True)):
        _, lo, hi = est.strat_wald(N_use[None, :], n_use[None, :], x_use[None, :], smoothed=sm)
        ci[name] = [float(lo[0]), float(hi[0])]
    _, lo, hi = est.strat_bootstrap(N_use, n_use[None, :], x_use[None, :], rng, B=B)
    ci["bootstrap"] = [float(lo[0]), float(hi[0])]
    _, lo, hi = est.strat_bayes(N_use, n_use[None, :], x_use[None, :], rng, B=B)
    ci["bayes_jeffreys"] = [float(lo[0]), float(hi[0])]
    out.update(estimate=p, interval=ci,
               strata=[{"stratum": " | ".join(map(str, row[cols])), "pool": int(row["N"]), "reviewed": int(row["n"]),
                        "hidden": int(row["x"]), "unresolved": int(row["u"])} for _, row in tab.iterrows()])
    if out["unresolved"]:
        sb = est.sensitivity_bounds(N_use[None, :], (tab["n"].to_numpy()[n_res > 0] if (n_res == 0).any() else tab["n"].to_numpy())[None, :].astype(np.int64),
                                    x_use[None, :], (tab["u"].to_numpy()[n_res > 0] if (n_res == 0).any() else tab["u"].to_numpy())[None, :].astype(np.int64))
        out["sensitivity"] = {k: float(v[0]) for k, v in sb.items()}
    return out


def headline_interval(est: dict) -> tuple[str, list]:
    """Name and limits of the interval shown first: smoothed Wald for stratified designs, Wilson for simple random."""
    name = SRS_INTERVAL if est["scheme"] == "M0" else DEFAULT_INTERVAL
    return name, est["interval"][name]
