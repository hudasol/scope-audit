"""Experiment C: calibration of estimators on SYNTHETIC populations with known FOR.

All populations here are SYNTHETIC. The purpose is to check bias, interval
coverage, width and discovery yield against a known truth, so that the
estimators are validated even where real data are not available.

Usage:  python experiments/c_calibration.py [--seeds 5000] [--boot 1000]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from scopeaudit import mc
from scopeaudit.results_io import header, write
from scopeaudit.sampling import rng_for, simple_random_ids
from scopeaudit.simulate import LABEL, make_population

BUDGETS = [50, 100, 200, 400, 800]
SCENARIOS = {"rare": 0.2, "low": 0.5, "medium": 1.0, "high": 2.5}
UNRESOLVED = [0.0, 0.05, 0.10]


def main(seeds: int, boot: int) -> None:
    t0 = time.time()
    out = {"header": header("C_calibration", LABEL, {"seeds": seeds, "bootstrap_replicates": boot,
                                                     "budgets": BUDGETS, "scenarios": SCENARIOS}),
           "scenarios": {}}
    for sname, scale in SCENARIOS.items():
        df = make_population(scale)
        truth = float(df["hit"].mean())
        sc = {"truth_for": truth, "pool_size": int(len(df)), "hidden_events": int(df["hit"].sum()),
              "results": {}}
        for n in BUDGETS:
            per = {}
            raw = {}
            for scheme in mc.available(df):
                rng = rng_for(7, "C", sname, scheme, n)
                res = mc.run_scheme(df, scheme, n, seeds, rng, B=boot)
                raw[scheme] = res
                s = mc.summarise(res)
                if scheme in ("M1", "M2", "M3"):
                    s["unresolved"] = [mc.unresolved_check(res, u, rng_for(9, "C", sname, scheme, n, u))
                                       for u in UNRESOLVED]
                per[scheme] = s
            for scheme in per:
                if scheme == "M0":
                    continue
                per[scheme]["yield_ratio_vs_M0"] = mc.yield_ratio(
                    raw[scheme]["yield"], raw["M0"]["yield"], rng_for(3, "C", sname, scheme, n))
            sc["results"][str(n)] = per
        out["scenarios"][sname] = sc
        print(f"{sname}: truth {truth:.4f}, elapsed {time.time() - t0:.0f}s", flush=True)
    # Reproducibility of sample identifiers: same seed, same inputs, same identifiers.
    df = make_population(1.0)
    same = sum(simple_random_ids(df, 100, s) == simple_random_ids(df, 100, s) for s in range(1000))
    out["reproducibility"] = {"runs": 1000, "identical": int(same), "rate": same / 1000.0}
    out["runtime_seconds"] = round(time.time() - t0, 1)
    write(Path(__file__).resolve().parents[1] / "results" / "experiment_c.json", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5000)
    ap.add_argument("--boot", type=int, default=1000)
    a = ap.parse_args()
    main(a.seeds, a.boot)
