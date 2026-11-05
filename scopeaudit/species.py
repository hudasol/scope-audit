"""Species suggestions from a classifier, kept strictly as suggestions.

The adapter reads the batch output of an external classifier (the SpeciesNet style
predictions file: a predictions list with filepath, prediction, prediction_score,
classifications, detections and model_version). No classifier is bundled and none has been
evaluated on UAE species. A suggestion is stored in the review log as an AI candidate and can
never be exported: only a human decision followed by approval reaches the export. Suggestions
are checked against the candidate species list and flagged when they fall outside it.

The taxonomy label layout is not documented in the source read for this build, so the parser
is tolerant (semicolon separated ranks, optional leading identifier) and unverified.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

SPECIAL = {"blank", "animal", "human", "vehicle", "unknown"}
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
OBS_TYPE = {"blank": "blank", "human": "human", "vehicle": "vehicle", "unknown": "unknown", "animal": "animal"}
RANKS = ["class", "order", "family", "genus", "species", "common_name"]


def parse_label(label: str | None) -> dict:
    """Split a taxonomy label into ranks and give a scientific name when genus and species are present."""
    out = {"label": label, "special": None, "scientific_name": None, "taxon_level": "none", "common_name": None}
    if not label:
        return out
    parts = [p.strip() for p in str(label).split(";")]
    if parts and (UUID.match(parts[0]) or parts[0] == ""):
        parts = parts[1:]
    tokens = [p for p in parts if p]
    if len(tokens) == 1 and tokens[0].lower() in SPECIAL:
        out["special"] = tokens[0].lower()
        out["taxon_level"] = "special"
        return out
    ranks = dict(zip(RANKS, (parts + [""] * 6)[:6]))
    if ranks["genus"] and ranks["species"]:
        out["scientific_name"] = f"{ranks['genus'].capitalize()} {ranks['species'].lower()}"
        out["taxon_level"] = "species"
    elif ranks["genus"]:
        out["scientific_name"] = ranks["genus"].capitalize()
        out["taxon_level"] = "genus"
    else:
        for lvl in ("family", "order", "class"):
            if ranks[lvl]:
                out["scientific_name"], out["taxon_level"] = ranks[lvl].capitalize(), lvl
                break
    out["common_name"] = ranks["common_name"] or None
    return out


def read_predictions(source) -> pd.DataFrame:
    """One row per image: top suggestion, score, taxon level, detector animal confidence and model version."""
    d = source if isinstance(source, dict) else json.load(open(Path(source), encoding="utf8"))
    rows = []
    for p in d.get("predictions", []):
        lab = parse_label(p.get("prediction"))
        animal = max([x.get("conf", 0.0) for x in p.get("detections", []) if str(x.get("category")) == "1"] or [0.0])
        cls = p.get("classifications", {})
        rows.append({"image_file": Path(str(p.get("filepath", ""))).name, "suggestion": lab["scientific_name"],
                     "taxon_level": lab["taxon_level"], "special": lab["special"], "common_name": lab["common_name"],
                     "score": p.get("prediction_score"), "detector_animal_conf": animal,
                     "model_version": p.get("model_version"), "failed": bool(p.get("failures")),
                     "top5_classes": cls.get("classes", []), "top5_scores": cls.get("scores", [])})
    return pd.DataFrame(rows)


def check_against_list(name: str | None, candidates: list[str]) -> str:
    """Flag a suggestion against the candidate species list (GBIF derived, not expert approved)."""
    if not name:
        return "no_taxon"
    cand = {c.lower() for c in candidates}
    if name.lower() in cand:
        return "in_candidate_list"
    genera = {c.split()[0].lower() for c in candidates if c}
    if name.split()[0].lower() in genera:
        return "genus_in_list_species_not"
    return "outside_candidate_list"


def to_payload(row: pd.Series, candidates: list[str]) -> dict:
    """Payload for an AI candidate record. It carries the suggestion and its flags, never an approval."""
    flag = check_against_list(row.get("suggestion"), candidates)
    otype = OBS_TYPE.get(row.get("special") or "animal", "animal") if row.get("special") else "animal"
    return {"source": "detector", "image_file": row["image_file"],
            "suggestion": {"scientific_name": row.get("suggestion"), "taxon_level": row.get("taxon_level"),
                           "score": None if pd.isna(row.get("score")) else float(row["score"]),
                           "model_version": row.get("model_version"), "candidate_list_check": flag,
                           "suggested_observation_type": otype},
            "note": "Suggestion only. A reviewer must decide and an approver must approve."}
