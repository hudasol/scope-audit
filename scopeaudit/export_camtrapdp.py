"""Export approved observations as a Camtrap DP 1.0.2 data package.

Only observations whose latest review state is approved or exported are written. The
three tables are validated against the table schemas stored under data/reference. A
separate audit package JSON records the audit design, estimate and interval. Deployment
coordinates must come from a real registry; the demo registry uses SYNTHETIC placeholders
and says so in the package description.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "data" / "reference" / "camtrap_dp_1.0.2"
PROFILE = "https://raw.githubusercontent.com/tdwg/camtrap-dp/1.0.2/camtrap-dp-profile.json"
TABLES = ["deployments", "media", "observations"]
_DT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$")


class ExportError(Exception):
    pass


def _load(table: str) -> dict:
    return json.load(open(SCHEMA_DIR / f"{table}-table-schema.json", encoding="utf8"))


def _check_value(field: dict, v) -> str | None:
    t = field["type"]
    if t == "datetime" and not _DT.match(str(v)):
        return "not an ISO 8601 datetime with offset"
    if t == "integer":
        try:
            if float(v) != int(float(v)):
                return "not an integer"
        except Exception:
            return "not an integer"
    if t == "number":
        try:
            float(v)
        except Exception:
            return "not a number"
    if t == "boolean" and str(v).lower() not in {"true", "false"}:
        return "not a boolean"
    enum = field.get("constraints", {}).get("enum")
    if enum and str(v) not in enum:
        return f"not in the allowed vocabulary {enum}"
    return None


def validate_table(name: str, df: pd.DataFrame) -> list[str]:
    schema = _load(name)
    errors = []
    names = [f["name"] for f in schema["fields"]]
    for col in df.columns:
        if col not in names:
            errors.append(f"{name}: unknown column {col}")
    for f in schema["fields"]:
        req = f.get("constraints", {}).get("required", False)
        if f["name"] not in df.columns:
            if req:
                errors.append(f"{name}: required column {f['name']} is missing")
            continue
        col = df[f["name"]]
        if req and col.isna().any():
            errors.append(f"{name}: required column {f['name']} has empty values")
        for i, v in col.dropna().items():
            msg = _check_value(f, v)
            if msg:
                errors.append(f"{name}: row {i}, {f['name']} = {v!r} is {msg}")
                break
    pk = schema.get("primaryKey")
    if isinstance(pk, str) and pk in df and df[pk].duplicated().any():
        errors.append(f"{name}: primary key {pk} is not unique")
    return errors


def validate_package(tables: dict[str, pd.DataFrame]) -> list[str]:
    errors = []
    for n in TABLES:
        errors += validate_table(n, tables[n])
    dep = set(tables["deployments"]["deploymentID"])
    for n in ("media", "observations"):
        bad = set(tables[n]["deploymentID"]) - dep
        if bad:
            errors.append(f"{n}: deploymentID values without a deployment row: {sorted(bad)[:3]}")
    if "mediaID" in tables["observations"]:
        mids = set(tables["media"]["mediaID"])
        bad = set(tables["observations"]["mediaID"].dropna()) - mids
        if bad:
            errors.append(f"observations: mediaID values without a media row: {sorted(bad)[:3]}")
    return errors


def _iso(ts) -> str:
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_tables(approved: list[dict], media: pd.DataFrame, registry: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """approved: latest review records. media: image_id, deployment_id, timestamp, original_filename, path.
    registry: deployment_id, latitude, longitude, deployment_start, deployment_end, camera_id."""
    if not approved:
        raise ExportError("No approved observations. Nothing is exported before human approval.")
    m = media.set_index("image_id")
    rows = []
    for rec in approved:
        if rec["state"] not in {"approved", "exported"}:
            raise ExportError(f"Observation {rec['observation_id']} is not approved.")
        p = rec["payload"]
        mid = p["image_id"]
        t = m.loc[mid]
        rows.append({"observationID": rec["observation_id"], "deploymentID": t["deployment_id"], "mediaID": mid,
                     "eventID": p.get("event_id"), "eventStart": _iso(t["timestamp"]), "eventEnd": _iso(t["timestamp"]),
                     "observationLevel": "media", "observationType": p["observation_type"],
                     "scientificName": p.get("scientific_name"), "count": p.get("count", 1),
                     "classificationMethod": "human", "classifiedBy": rec["actor"],
                     "classificationTimestamp": rec["timestamp_utc"]})
    obs = pd.DataFrame(rows)
    used = sorted(set(obs["mediaID"]))
    med = media[media["image_id"].isin(used)]
    media_t = pd.DataFrame({"mediaID": med["image_id"], "deploymentID": med["deployment_id"],
                            "captureMethod": "activityDetection", "timestamp": med["timestamp"].map(_iso),
                            "filePath": med["original_filename"], "filePublic": False, "fileName": med["original_filename"],
                            "fileMediatype": "image/jpeg"})
    reg = registry[registry["deployment_id"].isin(set(obs["deploymentID"]))]
    dep = pd.DataFrame({"deploymentID": reg["deployment_id"], "latitude": reg["latitude"], "longitude": reg["longitude"],
                        "deploymentStart": reg["deployment_start"].map(_iso), "deploymentEnd": reg["deployment_end"].map(_iso),
                        "cameraID": reg["camera_id"]})
    return {"deployments": dep, "media": media_t, "observations": obs}


def write_package(out_dir, tables: dict[str, pd.DataFrame], title: str, description: str, audit: dict | None = None) -> Path:
    errors = validate_package(tables)
    if errors:
        raise ExportError("Validation failed: " + "; ".join(errors[:5]))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    resources = []
    for n in TABLES:
        tables[n].to_csv(out / f"{n}.csv", index=False)
        resources.append({"name": n, "path": f"{n}.csv", "profile": "tabular-data-resource", "format": "csv",
                          "mediatype": "text/csv", "encoding": "utf-8", "schema": f"https://raw.githubusercontent.com/tdwg/camtrap-dp/1.0.2/{n}-table-schema.json"})
    pkg = {"resources": resources, "profile": PROFILE, "name": re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-"),
           "id": None, "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "title": title,
           "description": description,
           "contributors": [{"title": "Huda Mueen", "role": "author"}],
           "licenses": [{"name": "CC-BY-4.0", "scope": "data"}],
           "project": {"title": title, "samplingDesign": "targeted", "captureMethod": ["activityDetection"],
                       "individualAnimals": False, "observationLevel": ["media"]},
           "spatial": {"type": "Polygon", "coordinates": []}, "temporal": {"start": None, "end": None},
           "taxonomic": [{"scientificName": s} for s in sorted(set(tables["observations"]["scientificName"].dropna()))]}
    tmin = tables["observations"]["eventStart"].min()
    tmax = tables["observations"]["eventEnd"].max()
    pkg["temporal"] = {"start": tmin[:10], "end": tmax[:10]}
    lat, lon = tables["deployments"]["latitude"], tables["deployments"]["longitude"]
    x0, x1, y0, y1 = float(lon.min()), float(lon.max()), float(lat.min()), float(lat.max())
    pkg["spatial"] = {"type": "Polygon", "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]}
    json.dump(pkg, open(out / "datapackage.json", "w", encoding="utf8"), indent=2)
    if audit is not None:
        json.dump(audit, open(out / "audit_package.json", "w", encoding="utf8"), indent=2, default=str)
    return out
