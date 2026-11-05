import numpy as np
import pandas as pd

from scopeaudit.audit import build_pool, estimate, plan


def _events(n=3000, seed=3):
    rng = np.random.default_rng(seed)
    conf = np.where(rng.random(n) < 0.5, 0.0, rng.beta(1, 8, n))
    hit = (rng.random(n) < 0.004 + 0.12 * conf).astype(int)
    return pd.DataFrame({"event_id": [f"e{i:05d}" for i in range(n)], "max_animal_conf": conf, "hit": hit})


def _review(pool, ids, unresolved=0):
    r = pool.set_index("event_id").loc[ids]
    out = np.where(r["hit"] == 1, "animal", "empty").astype(object)
    out[:unresolved] = "unresolved"
    return pd.DataFrame({"event_id": ids, "outcome": out})


def test_plan_is_reproducible_and_within_budget():
    pool = build_pool(_events(), 0.4)
    a, b = plan(pool, "M2", 200, 5), plan(pool, "M2", 200, 5)
    assert a["event_ids"] == b["event_ids"] and len(a["event_ids"]) == 200
    assert plan(pool, "M2", 200, 6)["event_ids"] != a["event_ids"]


def test_estimate_close_to_truth_for_both_methods():
    pool = build_pool(_events(), 0.4)
    truth = pool["hit"].mean()
    for scheme in ("M0", "M2"):
        ids = plan(pool, scheme, 800, 1)["event_ids"]
        e = estimate(pool, scheme, _review(pool, ids), seed=1, B=500)
        assert abs(e["estimate"] - truth) < 0.02
        lo, hi = e["interval"]["bayes_jeffreys"]
        assert lo <= truth <= hi


def test_unresolved_bounds_bracket_the_resolved_estimate():
    pool = build_pool(_events(), 0.4)
    ids = plan(pool, "M2", 400, 2)["event_ids"]
    e = estimate(pool, "M2", _review(pool, ids, unresolved=20), seed=2, B=500)
    s = e["sensitivity"]
    assert s["lower_bound"] <= e["estimate"] + 1e-9 and s["upper_bound"] > s["lower_bound"]
    assert e["unresolved"] == 20
