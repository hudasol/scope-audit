"""Estimators and intervals for the event level false omission rate (FOR).

FOR is the share of AI negative events that contain an animal:

    FOR = FN / (FN + TN)

It is not the false negative rate, which is FN / (FN + TP). Everything in this
module estimates FOR for a finite pool of N negative events from a review
sample, using design based formulas.

All functions accept numpy arrays. Stratified functions take arrays whose last
axis is the stratum axis, so that thousands of simulated samples can be
evaluated in one call.
"""
from __future__ import annotations

import numpy as np
from scipy import stats

CONF = 0.95


def _z(conf: float = CONF) -> float:
    return float(stats.norm.ppf(1 - (1 - conf) / 2))


def wilson_fpc(x, n, N, conf: float = CONF):
    """Wilson interval for a simple random sample with finite population correction.

    The variance is scaled by (1 - n / N), which is applied through an effective
    sample size n / (1 - n / N). A census (n equal to N) returns a zero width interval.
    """
    x = np.asarray(x, dtype=float)
    n = np.asarray(n, dtype=float)
    z = _z(conf)
    f = np.clip(n / float(N), 0.0, 1.0)
    n_eff = np.minimum(n / np.maximum(1.0 - f, 1e-12), 1e12)
    p = x / n
    denom = 1.0 + z ** 2 / n_eff
    centre = (p + z ** 2 / (2 * n_eff)) / denom
    half = z * np.sqrt(p * (1 - p) / n_eff + z ** 2 / (4 * n_eff ** 2)) / denom
    return p, np.clip(centre - half, 0, 1), np.clip(centre + half, 0, 1)


def weights(N_h):
    N_h = np.asarray(N_h, dtype=float)
    return N_h / N_h.sum(axis=-1, keepdims=True)


def strat_point(N_h, n_h, x_h):
    """Stratified estimate of FOR: sum over strata of W_h times the sample rate."""
    W = weights(N_h)
    return (W * np.asarray(x_h, float) / np.asarray(n_h, float)).sum(axis=-1)


def strat_var(N_h, n_h, x_h, smoothed: bool = False):
    """Plug in variance of the stratified estimate, with finite population correction.

    With smoothed set, the stratum rate used inside the variance is (x + 0.5) / (n + 1).
    The point estimate is never smoothed. Smoothing only prevents a zero variance in
    strata where no animal was found.
    """
    N_h = np.asarray(N_h, float)
    n_h = np.asarray(n_h, float)
    x_h = np.asarray(x_h, float)
    W = weights(N_h)
    p = (x_h + 0.5) / (n_h + 1.0) if smoothed else x_h / n_h
    f = n_h / N_h
    return (W ** 2 * (1 - f) * p * (1 - p) / n_h).sum(axis=-1)


def strat_wald(N_h, n_h, x_h, smoothed: bool = False, conf: float = CONF):
    est = strat_point(N_h, n_h, x_h)
    se = np.sqrt(strat_var(N_h, n_h, x_h, smoothed=smoothed))
    z = _z(conf)
    return est, np.clip(est - z * se, 0, 1), np.clip(est + z * se, 0, 1)


def strat_bootstrap(N_h, n_h, x_h, rng, B: int = 1000, conf: float = CONF, chunk: int = 250):
    """Percentile bootstrap of the stratified estimate.

    Each replicate redraws every stratum sample from its observed rate with a
    binomial resample. No finite population correction is applied, so the
    intervals are slightly conservative when a large share of a stratum is
    reviewed. This is recorded as a limitation. A stratum with no animal found
    resamples to zero in every replicate, which is the same weakness the plug in
    Wald interval has.
    """
    N_h = np.asarray(N_h, float)
    n_h_arr = np.asarray(n_h)
    x_h = np.asarray(x_h)
    single = x_h.ndim == 1
    if single:
        x_h = x_h[None, :]
        n_h_arr = n_h_arr[None, :] if n_h_arr.ndim == 1 else n_h_arr
    S, H = x_h.shape
    n_b = np.broadcast_to(n_h_arr, (S, H)).astype(int)
    W = weights(N_h)
    est = strat_point(np.broadcast_to(N_h, (S, H)), n_b, x_h)
    lo = np.empty(S)
    hi = np.empty(S)
    a = (1 - conf) / 2
    for start in range(0, S, chunk):
        sl = slice(start, min(S, start + chunk))
        p = x_h[sl] / n_b[sl]
        draws = rng.binomial(n_b[sl][:, None, :], p[:, None, :], size=(sl.stop - sl.start, B, H))
        rep = (W * draws / n_b[sl][:, None, :]).sum(axis=-1)
        q = np.quantile(rep, [a, 1 - a], axis=1)
        lo[sl], hi[sl] = q[0], q[1]
    if single:
        return est[0], lo[0], hi[0]
    return est, lo, hi


def sensitivity_bounds(N_h, n_h, x_h, u_h, conf: float = CONF):
    """Bounds on FOR when some reviewed events are unresolved.

    x_h counts resolved hits and u_h counts unresolved events, both inside n_h.
    The lower bound treats every unresolved event as empty. The upper bound treats
    every unresolved event as a hit. The outer interval uses the lower limit of the
    lower bound and the upper limit of the upper bound, each with the smoothed
    variance interval.
    """
    x_h = np.asarray(x_h, float)
    u_h = np.asarray(u_h, float)
    lo_est, lo_lo, _ = strat_wald(N_h, n_h, x_h, smoothed=True, conf=conf)
    hi_est, _, hi_hi = strat_wald(N_h, n_h, x_h + u_h, smoothed=True, conf=conf)
    return {"lower_bound": lo_est, "upper_bound": hi_est,
            "outer_lower": lo_lo, "outer_upper": hi_hi}
