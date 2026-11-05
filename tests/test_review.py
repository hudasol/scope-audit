import pandas as pd
import pytest

from scopeaudit.intel import encounter_rates, camera_days
from scopeaudit.privacy import visible_deployments, generalise
from scopeaudit.review import ReviewLog, ReviewError


def _flow(log, obs="o1"):
    log.append(obs, "ai_candidate", "detector", "admin", {"source": "detector", "conf": 0.8})
    log.append(obs, "human_review", "r1", "reviewer", {"scientific_name": "Vulpes vulpes"})
    log.append(obs, "approved", "a1", "approver", {})


def test_lifecycle_and_export_gate():
    log = ReviewLog()
    _flow(log)
    with pytest.raises(ReviewError):
        log.append("o1", "exported", "r1", "reviewer", {})
    log.append("o1", "exported", "root", "admin", {})
    assert log.current_state("o1") == "exported"


def test_reviewer_cannot_approve_and_no_skipping():
    log = ReviewLog()
    log.append("o1", "ai_candidate", "detector", "admin", {"source": "detector"})
    with pytest.raises(ReviewError):
        log.append("o1", "approved", "a1", "approver", {})
    log.append("o1", "human_review", "r1", "reviewer", {})
    with pytest.raises(ReviewError):
        log.append("o1", "approved", "r1", "reviewer", {})


def test_correction_appends_and_never_overwrites():
    log = ReviewLog()
    _flow(log)
    log.append("o1", "human_review", "r2", "reviewer", {"scientific_name": "Canis lupus", "corrects": "approved"})
    names = [h["payload"].get("scientific_name") for h in log.history("o1")]
    assert names[:2] == [None, "Vulpes vulpes"] and names[-1] == "Canis lupus"
    assert len(log.history("o1")) == 4


def test_chain_detects_tampering():
    log = ReviewLog()
    _flow(log)
    assert log.verify_chain() == (True, None)
    log.con.execute("UPDATE log SET payload='{\"scientific_name\": \"Panthera leo\"}' WHERE seq=2")
    ok, seq = log.verify_chain()
    assert not ok and seq == 2


def test_privacy_grid_and_role_gate():
    dep = pd.DataFrame({"deployment_id": ["d"], "latitude": [24.4567], "longitude": [54.3789]})
    assert visible_deployments(dep, "admin").latitude[0] == 24.4567
    low = visible_deployments(dep, "reviewer")
    assert low.latitude[0] == generalise(24.4567) == 24.5 and bool(low.coordinates_generalised[0])


def test_encounter_rate_needs_valid_effort():
    dep = pd.DataFrame({"deployment_id": ["d1", "d2"], "deployment_start": ["2026-01-01", None],
                        "deployment_end": ["2026-01-11", None]})
    obs = pd.DataFrame({"deployment_id": ["d1", "d1", "d2"], "scientific_name": ["A b"] * 3, "event_id": [1, 2, 3]})
    r = encounter_rates(obs, dep).set_index("deployment_id")
    assert r.loc["d1", "events_per_100_camera_days"] == pytest.approx(20.0)
    assert pd.isna(r.loc["d2", "events_per_100_camera_days"])
    assert pd.isna(camera_days(dep, {"d1"}).set_index("deployment_id").loc["d1", "camera_days"])
