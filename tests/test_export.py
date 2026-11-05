import json

import pandas as pd
import pytest

from scopeaudit.export_camtrapdp import ExportError, build_tables, validate_package, write_package
from scopeaudit.review import ReviewLog


def _setup():
    media = pd.DataFrame({"image_id": ["m1", "m2"], "deployment_id": ["d1", "d1"],
                          "timestamp": ["2026-01-02 10:00:00", "2026-01-03 11:00:00"],
                          "original_filename": ["a.jpg", "b.jpg"]})
    reg = pd.DataFrame({"deployment_id": ["d1"], "latitude": [24.5], "longitude": [54.4],
                        "deployment_start": ["2026-01-01"], "deployment_end": ["2026-02-01"], "camera_id": ["c1"]})
    log = ReviewLog()
    for i, obs in enumerate(["o1", "o2"]):
        log.append(obs, "ai_candidate", "detector", "admin", {"source": "detector"})
        log.append(obs, "human_review", "r1", "reviewer", {"image_id": f"m{i+1}", "observation_type": "animal",
                                                           "scientific_name": "Vulpes vulpes", "count": 1})
    log.append("o1", "approved", "a1", "approver", {"image_id": "m1", "observation_type": "animal",
                                                   "scientific_name": "Vulpes vulpes", "count": 1})
    return log, media, reg


def test_only_approved_is_exported(tmp_path):
    log, media, reg = _setup()
    approved = log.latest("approved")
    assert [a["observation_id"] for a in approved] == ["o1"]
    tables = build_tables(approved, media, reg)
    assert list(tables["observations"]["observationID"]) == ["o1"]
    assert validate_package(tables) == []
    out = write_package(tmp_path, tables, "Demo", "SYNTHETIC registry coordinates.", {"x": 1})
    assert json.load(open(out / "datapackage.json"))["profile"].endswith("camtrap-dp-profile.json")
    assert (out / "audit_package.json").exists()


def test_nothing_exported_without_approval():
    log, media, reg = _setup()
    with pytest.raises(ExportError):
        build_tables(log.latest("exported"), media, reg)


def test_validation_catches_bad_vocabulary_and_missing_coordinates():
    log, media, reg = _setup()
    tables = build_tables(log.latest("approved"), media, reg)
    tables["observations"].loc[0, "observationType"] = "lion"
    assert any("allowed vocabulary" in e for e in validate_package(tables))
    tables = build_tables(log.latest("approved"), media, reg.assign(latitude=None))
    assert any("latitude" in e for e in validate_package(tables))
