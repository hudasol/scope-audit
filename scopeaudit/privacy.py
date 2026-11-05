"""Location privacy.

Exact deployment coordinates are visible only to roles that need them. Other roles see
coordinates generalised to a grid. The grid is a simple rounding of latitude and longitude.
All coordinates in tests and the demo registry are SYNTHETIC placeholders.
"""
from __future__ import annotations

import pandas as pd

EXACT_ROLES = {"admin", "approver"}
GRID_DEGREES = 0.1


def generalise(value: float, step: float = GRID_DEGREES) -> float:
    return round(round(value / step) * step, 6)


def visible_deployments(dep: pd.DataFrame, role: str, step: float = GRID_DEGREES) -> pd.DataFrame:
    out = dep.copy()
    if role in EXACT_ROLES:
        return out
    for col in ("latitude", "longitude"):
        if col in out:
            out[col] = out[col].map(lambda v: generalise(v, step) if pd.notna(v) else v)
    out["coordinates_generalised"] = True
    return out
