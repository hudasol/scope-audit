"""Adapter for the standard MegaDetector batch output format.

Reads a results file, keeps the model name, version and threshold metadata, and groups
images into animal candidates, other detections (person or vehicle) and negative
predictions. The original machine output is stored unchanged. Species classification is
not done here: an adapter interface is provided for a later classifier.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

CATEGORY_NAMES = {"1": "animal", "2": "person", "3": "vehicle"}


def read_results(path) -> tuple[pd.DataFrame, dict]:
    d = json.load(open(Path(path), encoding="utf8"))
    meta = {"detector": d.get("info", {}).get("detector"),
            "detector_metadata": d.get("info", {}).get("detector_metadata", {}),
            "format_version": d.get("info", {}).get("format_version"),
            "detection_categories": d.get("detection_categories", CATEGORY_NAMES)}
    rows = []
    for im in d["images"]:
        best = {"animal": 0.0, "person": 0.0, "vehicle": 0.0}
        for det in im.get("detections", []):
            name = CATEGORY_NAMES.get(det["category"], "vehicle")
            best[name] = max(best[name], det["conf"])
        rows.append({"file": im["file"], "conf_animal": best["animal"], "conf_person": best["person"],
                     "conf_vehicle": best["vehicle"], "n_detections": len(im.get("detections", [])),
                     "raw": json.dumps(im.get("detections", []))})
    return pd.DataFrame(rows), meta


def group(results: pd.DataFrame, threshold: float) -> pd.Series:
    """Label each image: animal_candidate, other_detection or negative_prediction."""
    out = pd.Series("negative_prediction", index=results.index, dtype=object)
    out[(results["conf_person"] >= threshold) | (results["conf_vehicle"] >= threshold)] = "other_detection"
    out[results["conf_animal"] >= threshold] = "animal_candidate"
    return out


class SpeciesClassifier(ABC):
    """Interface for an optional species classifier. No classifier is bundled.

    A prediction from any implementation is a candidate until a human reviewer approves it.
    """

    name: str = "none"
    version: str = "0"

    @abstractmethod
    def classify(self, image_path: str, bbox: list) -> dict:
        """Return scientific_name, taxonomic_level, probability and model identity."""


class NoClassifier(SpeciesClassifier):
    def classify(self, image_path: str, bbox: list) -> dict:
        return {"scientific_name": None, "taxonomic_level": "unknown", "probability": None,
                "model": self.name, "model_version": self.version}
