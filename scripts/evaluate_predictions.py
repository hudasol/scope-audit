"""Score the fixed predictions P1 to P8 and criteria S1 to S5 from the results files.

Nothing here is tuned after the fact. Each test is a literal reading of the sentence in
docs/PREDICTIONS.md. Where a sentence leaves a choice open, the choice is written next to
the test and applied to every cell. Output: results/predictions_evaluation.json.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scopeaudit.results_io import write  # noqa: E402

MID_BUDGETS = ["100", "200", "400"]
HIGH_BUDGETS = ["200", "400", "800"]
BIG_BUDGETS = ["400", "800"]


def load(name):
    return json.load(open(ROOT / "results" / name, encoding="utf8"))


def main() -> None:
    a, b, c = load("experiment_a.json"), load("experiment_b.json"), load("experiment_c.json")
    stress = next(r for r in b["regimes"].values() if r["is_stress"])
    sres = stress["results"]
    out = {"stress_threshold": stress["threshold"], "predictions": {}, "criteria": {}}
    P = out["predictions"]

    row = next(r for r in a["rows"] if abs(r["threshold"] - 0.2) < 1e-9)
    P["P1"] = {"claim": "Event level FOR below 3 percent at T of 0.2 (full benchmark, experiment A).",
               "observed": {"event_for": row["event_for"]}, "held": bool(row["event_for"] < 0.03)}

    ratios = {n: sres[n]["M2"]["yield_ratio_vs_M0"] for n in MID_BUDGETS}
    P["P2"] = {"claim": "In the stress regime, M2 yield per 100 reviews is at least 1.5 times M0 at budgets 100 to 400.",
               "observed": ratios, "held": all(v["ratio"] >= 1.5 for v in ratios.values())}

    m1 = {n: sres[n]["M1"]["yield_ratio_vs_M0"] for n in MID_BUDGETS}
    P["P3"] = {"claim": "M1 yield is below 1.3 times M0 (budgets 100 to 400) and the ratio interval includes 1.0 for at least one budget.",
               "observed": m1,
               "held": bool(all(v["ratio"] < 1.3 for v in m1.values()) and any(v["lo"] <= 1.0 <= v["hi"] for v in m1.values()))}

    m3 = {n: {"M3": sres[n]["M3"]["yield_mean"], "M2": sres[n]["M2"]["yield_mean"],
              "relative_difference": sres[n]["M3"]["yield_mean"] / sres[n]["M2"]["yield_mean"] - 1.0} for n in MID_BUDGETS}
    P["P4"] = {"claim": "M3 yield is within 10 percent of M2 (stress regime, budgets 100 to 400).",
               "observed": m3, "held": all(abs(v["relative_difference"]) <= 0.10 for v in m3.values())}

    bias = {n: sres[n]["M2"]["bias"] for n in HIGH_BUDGETS}
    P["P5"] = {"claim": "M2 mean error within 0.25 percentage points at budgets of 200 or more (stress regime).",
               "observed": bias, "held": all(abs(v) <= 0.0025 for v in bias.values())}

    # P6: first clause over every stratified scheme in every cell of experiments B and C.
    under, cells = [], 0
    def scan(res, tag):
        nonlocal cells
        for n, per in res.items():
            for s, v in per.items():
                if s in ("M1", "M2p", "M2", "M3", "M4") and "wald_plugin" in v["ci"]:
                    cells += 1
                    cov = v["ci"]["wald_plugin"]["coverage"]
                    if cov < 0.93:
                        under.append({"where": f"{tag} budget {n} {s}", "coverage": cov})
    for t, r in b["regimes"].items():
        scan(r["results"], f"B T={t}")
    for s_, r in c["scenarios"].items():
        scan(r["results"], f"C {s_}")
    second = {n: {k: sres[n]["M2"]["ci"][k]["coverage"] for k in ("wald_smoothed", "bootstrap")} for n in BIG_BUDGETS}
    second_ok = all(any(0.93 <= v <= 0.97 for v in d.values()) for d in second.values())
    P["P6"] = {"claim": "Wald plug in undercovers (below 93 percent) somewhere; smoothed or bootstrap intervals reach 93 to 97 percent at budgets 400 or more (M2, stress regime).",
               "observed": {"cells_checked": cells, "undercovering_cells": len(under), "worst": sorted(under, key=lambda x: x["coverage"])[:3],
                            "smoothed_or_bootstrap_M2_stress": second},
               "first_clause_held": bool(under), "second_clause_held": bool(second_ok), "held": bool(under) and bool(second_ok)}

    # P7: simple random Wilson with finite population correction, budgets 200+, truth FOR at least 1 percent.
    cov7, bad7 = [], []
    def scan0(res, truth, tag):
        for n in HIGH_BUDGETS:
            cv = res[n]["M0"]["ci"]["wilson_fpc"]["coverage"]
            cov7.append(cv)
            if not 0.93 <= cv <= 0.97:
                bad7.append({"where": f"{tag} budget {n}", "coverage": cv})
    for t, r in b["regimes"].items():
        if r["truth_for"] >= 0.01 and not r["underpowered"]:
            scan0(r["results"], r["truth_for"], f"B T={t}")
    for s_, r in c["scenarios"].items():
        if r["truth_for"] >= 0.01:
            scan0(r["results"], r["truth_for"], f"C {s_}")
    P["P7"] = {"claim": "Wilson with finite population correction covers 93 to 97 percent at budgets of 200 or more when FOR is at least 1 percent.",
               "observed": {"cells": len(cov7), "min": min(cov7), "max": max(cov7), "outside": bad7}, "held": not bad7}

    rep = c["reproducibility"]
    P["P8"] = {"claim": "Identical inputs, configuration and seed give identical sample identifiers in 100 percent of runs.",
               "observed": rep, "held": rep["identical"] == rep["runs"]}

    C = out["criteria"]
    C["S1"] = {"claim": "P2 holds.", "held": P["P2"]["held"]}
    C["S2"] = {"claim": "The recommended estimator covers 93 to 97 percent (read as: a P6 named interval, M2, stress regime, budgets 400 and 800).",
               "observed": second, "held": bool(second_ok)}
    C["S3"] = {"claim": "P5 holds.", "held": P["P5"]["held"]}
    C["S4"] = {"claim": "P8 holds.", "held": P["P8"]["held"]}
    lint = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_claims.py")], capture_output=True, text=True) \
        if (ROOT / "scripts" / "check_claims.py").exists() else None
    C["S5"] = {"claim": "The claims lint passes.", "held": None if lint is None else lint.returncode == 0,
               "note": "lint not yet present" if lint is None else lint.stdout[-400:]}
    out["superiority_claim_allowed"] = bool(C["S1"]["held"])
    write(ROOT / "results" / "predictions_evaluation.json", out)
    for k, v in {**P, **C}.items():
        print(k, "HELD" if v["held"] else ("NOT RUN" if v["held"] is None else "MISSED"))


if __name__ == "__main__":
    main()
