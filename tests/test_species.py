import pandas as pd

from scopeaudit.species import check_against_list, parse_label, read_predictions, to_payload
from scopeaudit.review import ReviewLog
from scopeaudit.export_camtrapdp import ExportError, build_tables
import pytest

# SYNTHETIC fixture in the documented field layout. Labels are invented for the test.
FIX = {"predictions": [
    {"filepath": "a/img1.jpg", "prediction": "11111111-2222-3333-4444-555555555555;mammalia;carnivora;canidae;vulpes;vulpes;red fox",
     "prediction_score": 0.91, "model_version": "test-1", "detections": [{"category": "1", "label": "animal", "conf": 0.88, "bbox": [0, 0, 1, 1]}],
     "classifications": {"classes": ["x"], "scores": [0.9]}},
    {"filepath": "b/img2.jpg", "prediction": "blank", "prediction_score": 0.99, "model_version": "test-1", "detections": []},
    {"filepath": "c/img3.jpg", "prediction": ";mammalia;carnivora;felidae;panthera;;", "prediction_score": 0.4, "model_version": "test-1"},
    {"filepath": "d/img4.jpg", "failures": ["CLASSIFIER"]},
]}
CAND = ["Vulpes vulpes", "Felis catus"]


def test_parse_label_levels():
    assert parse_label(FIX["predictions"][0]["prediction"])["scientific_name"] == "Vulpes vulpes"
    assert parse_label("blank")["special"] == "blank"
    g = parse_label(FIX["predictions"][2]["prediction"])
    assert g["taxon_level"] == "genus" and g["scientific_name"] == "Panthera"
    assert parse_label(None)["taxon_level"] == "none"


def test_read_predictions_and_flags():
    df = read_predictions(FIX).set_index("image_file")
    assert df.loc["img1.jpg", "suggestion"] == "Vulpes vulpes" and df.loc["img1.jpg", "detector_animal_conf"] == 0.88
    assert bool(df.loc["img4.jpg", "failed"])
    assert check_against_list("Vulpes vulpes", CAND) == "in_candidate_list"
    assert check_against_list("Vulpes zerda", CAND) == "genus_in_list_species_not"
    assert check_against_list("Panthera", CAND) == "outside_candidate_list"


def test_suggestion_cannot_be_exported_without_human_approval():
    df = read_predictions(FIX)
    payload = to_payload(df.iloc[0], CAND)
    log = ReviewLog()
    log.append("o1", "ai_candidate", "classifier", "admin", payload)
    media = pd.DataFrame({"image_id": ["m1"], "deployment_id": ["d1"], "timestamp": ["2026-01-02 10:00:00"], "original_filename": ["img1.jpg"]})
    reg = pd.DataFrame({"deployment_id": ["d1"], "latitude": [24.5], "longitude": [54.4], "deployment_start": ["2026-01-01"], "deployment_end": ["2026-02-01"], "camera_id": ["c1"]})
    with pytest.raises(ExportError):
        build_tables(log.latest("approved"), media, reg)
    assert payload["suggestion"]["candidate_list_check"] == "in_candidate_list"
