"""Write ENVIRONMENT.md and return the environment as a dictionary.

The numerical environment is pinned and reported so that every experiment can
be reproduced and compared on equal terms.
"""
from __future__ import annotations

import json
import os
import platform
import sys
from importlib import metadata
from pathlib import Path

PACKAGES = ["numpy", "pandas", "scipy", "statsmodels", "pydantic", "opencv-python-headless",
            "pillow", "matplotlib", "plotly", "streamlit", "pytest", "jsonschema", "requests"]


def environment() -> dict:
    versions = {}
    for name in PACKAGES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "not installed"
    threads = {k: os.environ.get(k, "unset") for k in
               ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "device": "cpu",
        "thread_environment": threads,
        "packages": versions,
    }


def to_markdown(env: dict) -> str:
    lines = ["# Environment", "",
             "Written by scripts/env_report.py. Every results file repeats these values.", "",
             f"- Python: {env['python']}", f"- Platform: {env['platform']} ({env['machine']})",
             f"- CPU count: {env['cpu_count']}", f"- Device: {env['device']}",
             f"- Thread variables: {json.dumps(env['thread_environment'])}", "", "| Package | Version |",
             "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in env["packages"].items()]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    env = environment()
    Path(__file__).resolve().parents[1].joinpath("ENVIRONMENT.md").write_text(to_markdown(env), encoding="utf8")
    print(json.dumps(env, indent=2))
