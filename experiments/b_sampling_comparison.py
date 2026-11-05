"""Experiment B: comparison of review sampling designs on the BORROWED benchmark working set.

Population: AI negative events at each detector threshold, from 8,000 events drawn
at random from Caltech Camera Traps (BORROWED, Southwestern United States) with
published MegaDetector v5a results. The reviewer is an ORACLE that reads the benchmark
label. A human reviewer is used only in the app demo.

Every design uses the same pool, the same budget and the same seeds. Strata are defined
without reading any label.

Usage: python experiments/b_sampling_comparison.py [--seeds 1000] [--boot 1000]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from scopeaudit import cct, mc
from scopeaudit.results_io import header, write
from scopeaudit.sampling import rng_for
from scopeaudit.strata import condition_strata, confidence_bins

ROOT = Path(__file__).resolve().parents[1]
BUDGETS = [50, 100, 200, 400, 800]
SWEEP = [0.1, 0.2, 0.4, 0.6, 0.8]
UNRESOLVED = [0.0, 0.05, 0.10]
POWER_MIN_HIDDEN = 30


def build_pool(work: pd.DataFrame, T: float) -> pd.DataFrame:
    pool = work[work["max_animal_conf"] < T].copy()
    labels, mids = confidence_bins(pool["max_animal_conf"].to_numpy(), T)
    pool["conf_bin"] = labels
    pool["conf_mid"] = mids
    if "brightness" in pool and pool["brightness"].notna().all():
        pool["cond"] = condition_strata(pool)
        pool["night"] = pool["night"].astype(bool).map({True: "night", False: "day"})
    else:
        pool = pool.drop(columns=[c for c in ("cond", "night") if c in pool], errors="ignore")
    return pool


def main(seeds: int, boot: int) -> None:
    t0 = time.time()
    work = pd.read_csv(ROOT / "data" / "working_set" / "events_features.csv", parse_dates=["start", "end"])
    work = work[work["brightness"].notna()].reset_index(drop=True)
    a = json.load(open(ROOT / "results" / "experiment_a.json"))
    stress = a["stress_threshold"]
    out = {"header": header("B_sampling_comparison", cct.DATA_LABEL,
                            {"seeds": seeds, "bootstrap_replicates": boot, "budgets": BUDGETS, "sweep": SWEEP,
                             "stress_threshold": stress, "working_set_events": int(len(work)),
                             "reviewer": "ORACLE (benchmark labels), not a human",
                             "note": "Benchmark overlaps detector training data; absolute error rates are optimistic."}),
           "regimes": {}}
    for T in SWEEP:
        pool = build_pool(work, T)
        truth = float(pool["hit"].mean())
        reg = {"threshold": T, "pool_size": int(len(pool)), "hidden_events": int(pool["hit"].sum()),
               "truth_for": truth, "underpowered": bool(pool["hit"].sum() < POWER_MIN_HIDDEN),
               "is_stress": bool(T == stress), "is_headline": bool(T == 0.2),
               "strata_counts": {s: int(v) for s, v in pool["conf_bin"].value_counts().items()},
               "condition_counts": {s: int(v) for s, v in pool["cond"].value_counts().items()},
               "results": {}}
        for n in BUDGETS:
            per, raw = {}, {}
            for scheme in mc.available(pool):
                rng = rng_for(13, "B", T, scheme, n)
                res = mc.run_scheme(pool, scheme, n, seeds, rng, B=boot)
                raw[scheme] = res
                s = mc.summarise(res)
                if scheme in ("M1", "M2", "M3"):
                    s["unresolved"] = [mc.unresolved_check(res, u, rng_for(17, "B", T, scheme, n, u))
                                       for u in UNRESOLVED]
                per[scheme] = s
            for scheme in per:
                if scheme != "M0":
                    per[scheme]["yield_ratio_vs_M0"] = mc.yield_ratio(
                        raw[scheme]["yield"], raw["M0"]["yield"], rng_for(5, "B", T, scheme, n))
            reg["results"][str(n)] = per
        out["regimes"][str(T)] = reg
        print(f"T={T}: pool {len(pool)}, hidden {int(pool['hit'].sum())}, elapsed {time.time() - t0:.0f}s", flush=True)
    out["runtime_seconds"] = round(time.time() - t0, 1)
    write(ROOT / "results" / "experiment_b.json", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=1000)
    ap.add_argument("--boot", type=int, default=1000)
    a = ap.parse_args()
    main(a.seeds, a.boot)
