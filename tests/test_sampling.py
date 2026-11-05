import numpy as np
import pandas as pd

from scopeaudit import sampling as sm
from scopeaudit.simulate import make_population


def test_allocation_sums_to_budget_and_respects_caps():
    N_h = np.array([1000, 50, 10, 3])
    a = sm.allocate(N_h, N_h * 1.0, 100)
    assert a.sum() == 100
    assert (a <= N_h).all()
    assert (a >= 2).all()


def test_allocation_handles_budget_above_population():
    N_h = np.array([5, 4])
    assert sm.allocate(N_h, np.array([1.0, 1.0]), 100).sum() == 9


def test_same_seed_gives_identical_sample_ids():
    df = make_population(1.0)
    a = sm.simple_random_ids(df, 200, seed=5)
    b = sm.simple_random_ids(df, 200, seed=5)
    c = sm.simple_random_ids(df, 200, seed=6)
    assert a == b and a != c


def test_stratified_ids_reproducible_and_obey_allocation():
    df = make_population(1.0)
    grp = df.groupby("conf_bin").size()
    alloc = {k: 10 for k in grp.index}
    a = sm.draw_ids(df, "conf_bin", alloc, seed=3, tag="m2")
    b = sm.draw_ids(df, "conf_bin", alloc, seed=3, tag="m2")
    assert a == b and len(a) == 10 * len(grp)
    assert len(set(a)) == len(a)


def test_reproducibility_rate_is_one_hundred_percent():
    df = make_population(1.0)
    same = 0
    for seed in range(200):
        same += sm.simple_random_ids(df, 50, seed) == sm.simple_random_ids(df, 50, seed)
    assert same == 200


def test_hypergeometric_matches_identifier_sampling():
    """The fast simulation must match drawing real identifiers and counting hits."""
    df = make_population(2.5)
    n = 150
    strata = df.groupby("conf_bin")
    N_h = strata.size().to_numpy()
    K_h = strata["hit"].sum().to_numpy()
    alloc = sm.allocate(N_h, N_h.astype(float), n)
    rng = np.random.default_rng(0)
    fast = sm.simulate_counts(N_h, K_h, alloc, 3000, rng).sum(axis=1)
    hits = df.set_index("event_id")["hit"]
    slow = []
    for seed in range(1500):
        ids = sm.draw_ids(df, "conf_bin", dict(zip(strata.size().index, alloc)), seed, "eq")
        slow.append(hits.loc[ids].sum())
    assert abs(fast.mean() - np.mean(slow)) < 0.25
    assert abs(fast.std() - np.std(slow)) < 0.25
