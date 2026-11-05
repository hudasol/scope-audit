"""Build a candidate regional reference list of mammal species recorded in the UAE.

Source: the GBIF occurrence API (country AE, class Mammalia). Species names are resolved
against the GBIF backbone taxonomy. The result is a CANDIDATE reference list and has NOT
been approved by an expert. It includes species of any status (wild, introduced, marine,
domestic records) because GBIF counts all occurrence records.

Usage: python scripts/fetch_gbif_uae.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parents[1] / "data" / "reference" / "uae_mammals_gbif.json"
API = "https://api.gbif.org/v1"


def main() -> int:
    cls = requests.get(f"{API}/species/match", params={"name": "Mammalia", "rank": "class"}, timeout=60).json()
    class_key = cls["usageKey"]
    occ = requests.get(f"{API}/occurrence/search", params={
        "country": "AE", "classKey": class_key, "limit": 0, "facet": "speciesKey", "facetLimit": 1000}, timeout=120).json()
    species = []
    for f in occ["facets"][0]["counts"]:
        key = int(f["name"])
        sp = requests.get(f"{API}/species/{key}", timeout=60).json()
        species.append({"speciesKey": key, "scientificName": sp.get("scientificName"),
                        "canonicalName": sp.get("canonicalName"), "family": sp.get("family"),
                        "taxonomicStatus": sp.get("taxonomicStatus"), "occurrenceRecords": f["count"]})
    species.sort(key=lambda s: -s["occurrenceRecords"])
    payload = {
        "label": "CANDIDATE reference list from GBIF occurrence records, not expert approved",
        "source": "GBIF occurrence API, country=AE, classKey=%d (Mammalia)" % class_key,
        "retrieved_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_occurrence_records": occ["count"],
        "species_count": len(species),
        "species": species,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf8")
    print(len(species), "species,", occ["count"], "records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
