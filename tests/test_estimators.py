import numpy as np
import pytest

from scopeaudit import estimators as est
from scopeaudit.sampling import rng_for


def test_wilson_fpc_census_has_zero_width():
    p, lo, hi = est.wilson_fpc(5, 100, 100)
    assert p == pytest.approx(0.05)
    assert hi - lo < 1e-3


def test_wilson_fpc_narrower_than_without_correction():
    _, lo1, hi1 = est.wilson_fpc(5, 100, 100000)
    _, lo2, hi2 = est.wilson_fpc(5, 100, 200)
    assert (hi2 - lo2) < (hi1 - lo1)


def test_strat_point_is_unbiased_by_monte_carlo():
    rng = rng_for(1, "unbiased")
    N_h = np.array([500, 300, 200])
    K_h = np.array([2, 15, 40])
    truth = K_h.sum() / N_h.sum()
    n_h = np.array([30, 30, 30])
    x = rng.hypergeometric(K_h, N_h - K_h, n_h, size=(20000, 3))
    e = est.strat_point(np.broadcast_to(N_h, x.shape), np.broadcast_to(n_h, x.shape), x)
    assert abs(e.mean() - truth) < 5e-4


def test_smoothed_variance_is_positive_when_no_hits():
    N_h = np.array([100, 100])
    n_h = np.array([10, 10])
    x_h = np.array([0, 0])
    assert est.strat_var(N_h, n_h, x_h, smoothed=False) == 0
    assert est.strat_var(N_h, n_h, x_h, smoothed=True) > 0


def test_sensitivity_bounds_are_ordered():
    N_h = np.array([100.0, 100.0])
    n_h = np.array([20.0, 20.0])
    b = est.sensitivity_bounds(N_h, n_h, np.array([1.0, 2.0]), np.array([3.0, 1.0]))
    assert b["outer_lower"] <= b["lower_bound"] <= b["upper_bound"] <= b["outer_upper"]


def test_bootstrap_interval_contains_estimate():
    rng = rng_for(2, "boot")
    N_h = np.array([400.0, 100.0])
    n_h = np.array([40, 20])
    x_h = np.array([3, 5])
    e, lo, hi = est.strat_bootstrap(N_h, n_h, x_h, rng, B=500)
    assert lo <= e <= hi


def test_bayes_interval_contains_estimate_and_handles_zero_hits():
    rng = rng_for(3, "bayes")
    N_h = np.array([800, 200])
    n_h = np.array([40, 20])
    e, lo, hi = est.strat_bayes(N_h, n_h, np.array([0, 0]), rng, B=500)
    assert e == 0 and lo == 0 and hi > 0
    e, lo, hi = est.strat_bayes(N_h, n_h, np.array([2, 4]), rng, B=500)
    assert lo <= e <= hi


def test_bayes_coverage_is_reasonable_for_rare_events():
    rng = rng_for(4, "bayes_cov")
    N_h = np.array([900, 100])
    K_h = np.array([3, 12])
    truth = K_h.sum() / N_h.sum()
    n_h = np.array([60, 30])
    S = 400
    x = rng.hypergeometric(K_h, N_h - K_h, n_h, size=(S, 2))
    _, lo, hi = est.strat_bayes(N_h, np.broadcast_to(n_h, (S, 2)), x, rng, B=400)
    cover = np.mean((lo <= truth) & (truth <= hi))
    assert cover > 0.9
