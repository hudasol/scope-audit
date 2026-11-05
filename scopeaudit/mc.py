"""Repeated audit evaluation on a population with known truth.

A population is a table with one row per AI negative event and the columns:
    hit        1 if the event contains an animal, else 0 (truth, used by the oracle)
    conf_bin   detector confidence stratum label
    conf_mid   bin midpoint
    cond       image condition stratum (optional)
    night      night flag (optional)

Methods
    M0  simple random sample of events
    M1  proportional stratified, condition strata
    M2p proportional stratified, confidence strata (control, no oversampling)
    M2  confidence strata, allocation proportional to W_h * (midpoint + 0.02)
    M3  confidence by night strata, same allocation rule
    M4  two phase: 20 percent proportional pilot, then Neyman style allocation
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import estimators as est
from .sampling import allocate, simulate_counts

RISK_OFFSET = 0.02
PILOT_SHARE = 0.20

SCHEMES = {
    "M0": {"kind": "srs"},
    "M1": {"kind": "strat", "cols": ["cond"], "alloc": "proportional"},
    "M2p": {"kind": "strat", "cols": ["conf_bin"], "alloc": "proportional"},
    "M2": {"kind": "strat", "cols": ["conf_bin"], "alloc": "risk"},
    "M3": {"kind": "strat", "cols": ["conf_bin", "night"], "alloc": "risk"},
    "M4": {"kind": "two_phase", "cols": ["conf_bin"]},
}


def available(df: pd.DataFrame) -> list:
    out = []
    for name, sc in SCHEMES.items():
        cols = sc.get("cols", [])
        if all(c in df.columns for c in cols):
            out.append(name)
    return out


def strata_table(df: pd.DataFrame, cols) -> pd.DataFrame:
    g = df.groupby(cols, sort=True).agg(N=("hit", "size"), K=("hit", "sum"), mid=("conf_mid", "mean"))
    return g.reset_index()


def _two_phase(N_h, K_h, n, S, rng):
    H = len(N_h)
    pilot = int(min(max(round(n * PILOT_SHARE), 2 * H), n))
    a1 = allocate(N_h, N_h.astype(float), pilot)
    x1 = simulate_counts(N_h, K_h, a1, S, rng)
    N2 = N_h - a1
    K2 = K_h[None, :] - x1
    n2 = int(min(n - a1.sum(), N2.sum()))
    xs = np.zeros((S, H), dtype=np.int64)
    ns = np.zeros((S, H), dtype=np.int64)
    for s in range(S):
        p = (x1[s] + 0.5) / (a1 + 1.0)
        score = N_h * np.sqrt(p * (1 - p))
        a2 = allocate(N2, score, n2, min_per=0)
        x2 = rng.hypergeometric(K2[s], N2 - K2[s], a2)
        xs[s] = x1[s] + x2
        ns[s] = a1 + a2
    return xs, ns


def run_scheme(df: pd.DataFrame, scheme: str, n: int, S: int, rng, B: int = 1000, with_bootstrap: bool = True):
    """Run S repeated audits of one scheme with budget n. Returns per seed arrays."""
    sc = SCHEMES[scheme]
    N_total = len(df)
    K_total = int(df["hit"].sum())
    truth = K_total / N_total
    n = int(min(n, N_total))
    if sc["kind"] == "srs":
        x = rng.hypergeometric(K_total, N_total - K_total, n, size=(S, 1))
        nn = np.full((S, 1), n)
        p, lo, hi = est.wilson_fpc(x[:, 0], n, N_total)
        ci0 = {"wilson_fpc": (lo, hi)}
        if with_bootstrap:
            _, blo, bhi = est.strat_bayes(np.array([N_total]), nn, x, rng, B=B)
            ci0["bayes_jeffreys"] = (blo, bhi)
        return {"truth": truth, "n_h": nn, "x_h": x, "estimate": p,
                "ci": ci0, "yield": 100.0 * x[:, 0] / n, "N_h": np.array([N_total]),
                "K_h": np.array([K_total]), "mid": np.array([0.0])}
    tab = strata_table(df, sc["cols"])
    N_h = tab["N"].to_numpy(dtype=np.int64)
    K_h = tab["K"].to_numpy(dtype=np.int64)
    mid = tab["mid"].to_numpy(dtype=float)
    if sc["kind"] == "two_phase":
        x, nn = _two_phase(N_h, K_h, n, S, rng)
    else:
        score = N_h.astype(float) if sc["alloc"] == "proportional" else N_h * (mid + RISK_OFFSET)
        a = allocate(N_h, score, n)
        nn = np.broadcast_to(a, (S, len(a))).astype(np.int64)
        x = simulate_counts(N_h, K_h, a, S, rng)
    Nb = np.broadcast_to(N_h, x.shape)
    point = est.strat_point(Nb, nn, x)
    ci = {}
    _, lo, hi = est.strat_wald(Nb, nn, x, smoothed=False)
    ci["wald_plugin"] = (lo, hi)
    _, lo, hi = est.strat_wald(Nb, nn, x, smoothed=True)
    ci["wald_smoothed"] = (lo, hi)
    if with_bootstrap:
        _, lo, hi = est.strat_bootstrap(N_h, nn, x, rng, B=B)
        ci["bootstrap"] = (lo, hi)
        _, lo, hi = est.strat_bayes(N_h, nn, x, rng, B=B)
        ci["bayes_jeffreys"] = (lo, hi)
    yld = 100.0 * x.sum(axis=1) / nn.sum(axis=1)
    return {"truth": truth, "n_h": nn, "x_h": x, "estimate": point, "ci": ci, "yield": yld,
            "N_h": N_h, "K_h": K_h, "mid": mid}


def summarise(res: dict) -> dict:
    t = res["truth"]
    e = res["estimate"]
    out = {"truth": float(t), "bias": float(np.mean(e - t)), "mae": float(np.mean(np.abs(e - t))),
           "yield_mean": float(np.mean(res["yield"])), "ci": {}}
    for name, (lo, hi) in res["ci"].items():
        out["ci"][name] = {"coverage": float(np.mean((lo <= t) & (t <= hi))), "width": float(np.mean(hi - lo))}
    return out


def yield_ratio(y_method: np.ndarray, y_base: np.ndarray, rng, B: int = 2000):
    """Ratio of mean yields with a bootstrap interval over seeds."""
    S1, S0 = len(y_method), len(y_base)
    a = y_method[rng.integers(0, S1, size=(B, S1))].mean(axis=1)
    b = y_base[rng.integers(0, S0, size=(B, S0))].mean(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = a / b
    r = r[np.isfinite(r)]
    point = float(y_method.mean() / y_base.mean()) if y_base.mean() > 0 else float("nan")
    if len(r) == 0:
        return {"ratio": point, "lo": float("nan"), "hi": float("nan")}
    return {"ratio": point, "lo": float(np.quantile(r, 0.025)), "hi": float(np.quantile(r, 0.975))}


def unresolved_check(res: dict, frac: float, rng) -> dict:
    """Share of audits whose sensitivity interval contains the truth when frac of reviews is unresolved."""
    x, nn = res["x_h"], res["n_h"]
    N_h = res["N_h"]
    hit_unres = rng.binomial(x, frac)
    non_unres = rng.binomial(nn - x, frac)
    x_res = x - hit_unres
    U = hit_unres + non_unres
    Nb = np.broadcast_to(N_h, x.shape)
    b = est.sensitivity_bounds(Nb, nn, x_res, U)
    t = res["truth"]
    contain = (b["outer_lower"] <= t) & (t <= b["outer_upper"])
    return {"unresolved_fraction": frac, "contains_truth": float(np.mean(contain)),
            "mean_lower": float(np.mean(b["lower_bound"])), "mean_upper": float(np.mean(b["upper_bound"]))}
