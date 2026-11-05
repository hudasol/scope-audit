"""Plain language audit report built from an estimate dictionary."""
from __future__ import annotations

from .audit import METHOD_NAMES

NOTICE = ("The false omission rate is the share of events containing an animal inside the pool the detector "
          "called negative. It is not the detector miss rate, and it does not describe species presence or absence.")


def audit_report(est: dict, threshold: float, data_label: str) -> str:
    lo, hi = est["interval"].get("bayes_jeffreys", next(iter(est["interval"].values())))
    lines = [f"# Audit report", "", f"Data label: {data_label}", "",
             f"Detector threshold: {threshold}", f"Method: {METHOD_NAMES.get(est['scheme'], est['scheme'])}",
             f"AI negative events in the pool: {est['pool_size']}", f"Events reviewed: {est['reviewed']}",
             f"Events found with an animal: {est['hidden_found']}", f"Unresolved reviews: {est['unresolved']}", "",
             f"Estimated false omission rate: {100 * est['estimate']:.2f} percent",
             f"Interval (95 percent): {100 * lo:.2f} to {100 * hi:.2f} percent",
             f"Hidden events found per 100 reviews: {est['yield_per_100_reviews']:.1f}"]
    if "sensitivity" in est:
        s = est["sensitivity"]
        lines += ["", f"Bounds for unresolved reviews: {100 * s['lower_bound']:.2f} to {100 * s['upper_bound']:.2f} percent."]
    lines += ["", NOTICE, ""]
    return "\n".join(lines)
