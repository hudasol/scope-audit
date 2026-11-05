"""Shared helpers for writing results files with the pinned environment on top."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def predictions_commit() -> str:
    try:
        out = subprocess.run(["git", "log", "-n", "1", "--format=%H", "--", "docs/PREDICTIONS.md"],
                             cwd=ROOT, capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except Exception:
        return "unknown"


def header(experiment: str, data_label: str, extra: dict | None = None) -> dict:
    from env_report import environment
    h = {"experiment": experiment, "data_label": data_label,
         "predictions_commit": predictions_commit(), "environment": environment()}
    if extra:
        h.update(extra)
    return h


def write(path: str | Path, payload: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf8")
