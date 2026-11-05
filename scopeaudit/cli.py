"""Command line entry: python -m scopeaudit.cli audit --events FILE --threshold 0.2 --budget 200 --method M2"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from . import audit as au
from .report import audit_report


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="scopeaudit")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit", help="Plan a review sample, simulate an oracle reviewer on labelled data and report.")
    a.add_argument("--events", default="data/working_set/events_features.csv")
    a.add_argument("--threshold", type=float, default=0.2)
    a.add_argument("--budget", type=int, default=200)
    a.add_argument("--method", default="M2", choices=list(au.METHOD_NAMES))
    a.add_argument("--seed", type=int, default=20261106)
    a.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    ev = pd.read_csv(args.events)
    pool = au.build_pool(ev, args.threshold)
    plan = au.plan(pool, args.method, args.budget, args.seed)
    r = pool.set_index("event_id").loc[plan["event_ids"]]
    reviews = pd.DataFrame({"event_id": plan["event_ids"], "outcome": np.where(r["hit"] == 1, "animal", "empty")})
    est = au.estimate(pool, args.method, reviews, seed=args.seed)
    label = ev["data_label"].iloc[0] if "data_label" in ev else "unlabelled"
    print(json.dumps(est, indent=2, default=float) if args.json else audit_report(est, args.threshold, label))


if __name__ == "__main__":
    main()
