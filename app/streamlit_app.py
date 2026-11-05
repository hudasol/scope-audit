"""SCOPE AUDIT demo application with three screens.

1. Ingest and integrity   2. Audit   3. Review, approve and export

Data in this demo are BORROWED (Caltech Camera Traps, southwestern United States) with
SYNTHETIC deployment coordinates. The reviewer in screen 2 is a stand in that reads the
benchmark labels. Nothing here describes the United Arab Emirates.
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import streamlit as st

from scopeaudit import audit as au
from scopeaudit.export_camtrapdp import ExportError, build_tables, write_package
from scopeaudit.ingest import attach_metadata, scan_images, summary
from scopeaudit.integrity import check_media, recording_gaps
from scopeaudit.privacy import visible_deployments
from scopeaudit.review import ReviewError, ReviewLog
from scopeaudit.species import read_predictions, to_payload

LABEL = "BORROWED benchmark data with SYNTHETIC deployment coordinates"
CONTEXT_NOTE = ("This demo reads Caltech Camera Traps images from the southwestern United States. "
                "Nothing shown describes the United Arab Emirates.")

st.set_page_config(page_title="SCOPE AUDIT", page_icon="🌸", layout="wide")
st.markdown("""<style>
h1,h2,h3{color:#C2557A;} .stButton>button{background:#C2557A;color:#FAF3F0;border:0;border-radius:8px;}
.label{background:#F8C8DC;border-radius:8px;padding:6px 12px;color:#4A2B3A;font-size:0.9rem;}
</style>""", unsafe_allow_html=True)


@st.cache_data
def load_events() -> pd.DataFrame:
    return pd.read_csv(ROOT / "data" / "working_set" / "events_features.csv")


@st.cache_data
def load_demo() -> tuple[pd.DataFrame, pd.DataFrame]:
    ev = pd.read_csv(ROOT / "data" / "demo" / "demo_events.csv")
    reg = pd.read_csv(ROOT / "data" / "demo" / "demo_registry.csv", parse_dates=["deployment_start", "deployment_end"])
    return ev, reg


@st.cache_data
def load_species() -> list[str]:
    d = json.load(open(ROOT / "data" / "reference" / "uae_mammals_gbif.json", encoding="utf8"))
    items = d.get("species", d) if isinstance(d, dict) else d
    names = [s.get("canonicalName") or s["scientificName"] if isinstance(s, dict) else s for s in items]
    return sorted(set(names))


def log() -> ReviewLog:
    if "log" not in st.session_state:
        st.session_state["log"] = ReviewLog(str(Path(tempfile.mkdtemp()) / "review.sqlite"))
    return st.session_state["log"]


st.title("🌷 SCOPE AUDIT")
st.markdown(f"<div class='label'>{LABEL}. {CONTEXT_NOTE}</div>", unsafe_allow_html=True)
role = st.sidebar.selectbox("Role", ["reviewer", "approver", "admin"], index=0)
screen = st.sidebar.radio("Screen", ["1. Ingest and integrity", "2. Audit", "3. Review, approve and export"])
demo_ev, registry = load_demo()
demo_ev = demo_ev.assign(timestamp=pd.to_datetime(demo_ev["timestamp"]))

if screen.startswith("1"):
    st.header("Ingest and integrity")
    imgs = scan_images(ROOT / "data" / "demo" / "images", "Caltech Camera Traps (BORROWED)")
    imgs["event_id"] = imgs["original_filename"].str.replace(".jpg", "", regex=False)
    meta = demo_ev.rename(columns={"image_file": "original_filename"})[["original_filename", "camera_id", "deployment_id", "timestamp"]]
    media = attach_metadata(imgs, meta)
    media["image_id"] = media["event_id"].str.replace("-", "").str[:16]
    dep = registry.rename(columns={"deployment_start": "deployment_start", "deployment_end": "deployment_end"})
    flags = check_media(media, dep)
    s = summary(media, flags)
    cols = st.columns(3)
    for i, (k, v) in enumerate(s.items()):
        cols[i % 3].metric(k.replace("_", " ").capitalize(), v)
    st.subheader("Flags")
    st.dataframe(flags if len(flags) else pd.DataFrame({"result": ["No integrity flags in the demo images."]}))
    st.subheader("Recording gaps")
    gaps = recording_gaps(media)
    st.dataframe(gaps if len(gaps) else pd.DataFrame({"result": ["No prolonged gaps in this small sample."]}))
    st.subheader("Deployment registry (coordinates SYNTHETIC)")
    st.dataframe(visible_deployments(dep, role))

elif screen.startswith("2"):
    st.header("Audit of AI negative events")
    events = load_events()
    c1, c2, c3, c4 = st.columns(4)
    T = c1.select_slider("Detector threshold", [0.1, 0.2, 0.4, 0.6, 0.8], value=0.2)
    budget = c2.slider("Review budget (events)", 50, 800, 200, step=50)
    scheme = c3.selectbox("Sampling method", list(au.METHOD_NAMES), index=2, format_func=lambda k: au.METHOD_NAMES[k])
    unres = c4.slider("Unresolved reviews (share)", 0, 10, 0, format="%d%%")
    pool = au.build_pool(events, T)
    if scheme == "M3" and "night" not in pool:
        scheme = "M2"
    p = au.plan(pool, scheme, budget, seed=20261106)
    ids = p["event_ids"]
    rev = pool.set_index("event_id").loc[ids]
    outcome = np.where(rev["hit"] == 1, "animal", "empty").astype(object)
    k = int(round(len(ids) * unres / 100.0))
    outcome[:k] = "unresolved"
    reviews = pd.DataFrame({"event_id": ids, "outcome": outcome})
    e = au.estimate(pool, scheme, reviews, seed=1)
    truth = float(pool["hit"].mean())
    st.caption("The reviewer here is a stand in that reads benchmark labels. In use, a person reviews each event.")
    m = st.columns(4)
    m[0].metric("AI negative events", f"{len(pool):,}")
    m[1].metric("Estimated false omission rate", f"{100 * e['estimate']:.2f}%")
    iname, (lo, hi) = au.headline_interval(e)
    m[2].metric(f"95% interval ({iname})", f"{100 * lo:.2f}% to {100 * hi:.2f}%")
    m[3].metric("Hidden events found per 100 reviews", f"{e['yield_per_100_reviews']:.1f}")
    st.write(f"Reviewed {e['reviewed']} events, found {e['hidden_found']} with an animal, {e['unresolved']} unresolved. "
             f"Benchmark value for this pool, known only because the data are labelled: {100 * truth:.2f}%.")
    if "sensitivity" in e:
        sb = e["sensitivity"]
        st.info(f"Unresolved reviews are handled by bounds, not guessed: the rate lies between {100 * sb['lower_bound']:.2f}% and "
                f"{100 * sb['upper_bound']:.2f}% if every unresolved event were empty or an animal.")
    st.subheader("Intervals")
    st.dataframe(pd.DataFrame([{"interval": k_, "lower %": 100 * v[0], "upper %": 100 * v[1]} for k_, v in e["interval"].items()]))
    if "strata" in e:
        st.subheader("Strata")
        st.dataframe(pd.DataFrame(e["strata"]))
    st.caption("The false omission rate is the share of animal events inside the AI negative pool. It is not the miss rate. "
               "An estimate of a rate in a pool does not describe species presence or absence.")

else:
    st.header("Review, approve and export")
    L = log()
    spp = load_species()
    st.caption("Species names come from a candidate list built from GBIF (not approved by an expert). "
               "Nothing is exported before a person with the approver role approves it.")
    row = st.selectbox("Event", demo_ev["event_id"], format_func=lambda i: i[:8] + "  " + str(demo_ev.set_index("event_id").loc[i, "timestamp"]))
    r = demo_ev.set_index("event_id").loc[row]
    img = ROOT / "data" / "demo" / "images" / r["image_file"]
    left, right = st.columns([2, 1])
    left.image(str(img), caption="Borrowed image from Caltech Camera Traps", use_container_width=True)
    state = L.current_state(row)
    right.write(f"Current state: **{state or 'not yet in the log'}**")
    up = st.sidebar.file_uploader("Optional classifier predictions (JSON)", type="json")
    sugg = None
    if up is not None:
        try:
            preds = read_predictions(json.load(up)).set_index("image_file")
            if r["image_file"] in preds.index:
                sugg = to_payload(preds.loc[r["image_file"]].assign(image_file=r["image_file"]), spp)
        except (ValueError, KeyError) as ex:
            st.sidebar.error(f"Predictions could not be read: {ex}")
    if sugg:
        sg = sugg["suggestion"]
        right.info(f"Suggestion only: {sg['scientific_name'] or sg['suggested_observation_type']} "
                   f"(score {sg['score']}, {sg['candidate_list_check'].replace('_', ' ')}). You decide.")
    otype = right.selectbox("Observation type", ["animal", "blank", "unknown", "human", "vehicle"])
    sci = right.selectbox("Scientific name", [""] + spp) if otype == "animal" else ""
    payload = {"image_id": r["image_id"], "event_id": row, "observation_type": otype,
               "scientific_name": sci or None, "count": 1}
    if right.button("Record review"):
        try:
            if state is None:
                L.append(row, "ai_candidate", "detector", "admin",
                         {**(sugg or {"source": "detector"}), "image_id": r["image_id"]})
            L.append(row, "human_review", f"user_{role}", role, payload)
            st.success("Review recorded.")
        except ReviewError as ex:
            st.error(str(ex))
    if right.button("Approve"):
        try:
            L.append(row, "approved", f"user_{role}", role, payload)
            st.success("Approved.")
        except ReviewError as ex:
            st.error(str(ex))
    st.subheader("History of this event")
    st.dataframe(pd.DataFrame([{k: v for k, v in h.items() if k != "payload"} | {"payload": json.dumps(h["payload"])} for h in L.history(row)]))
    ok, bad = L.verify_chain()
    st.write("Log integrity: " + ("chain verified" if ok else f"chain broken at record {bad}"))
    st.subheader("Export")
    if st.button("Export approved observations as Camtrap DP"):
        try:
            approved = L.latest("approved")
            media = demo_ev.assign(deployment_id=demo_ev["deployment_id"])[["image_id", "deployment_id", "timestamp", "image_file"]] \
                .rename(columns={"image_file": "original_filename"})
            reg = registry.rename(columns={})
            tables = build_tables(approved, media, reg)
            tmp = Path(tempfile.mkdtemp())
            out = write_package(tmp / "package", tables, "Scope audit demo package",
                                "SYNTHETIC deployment coordinates. Borrowed images. Demonstration only.",
                                {"label": LABEL})
            for rec in approved:
                L.append(rec["observation_id"], "exported", f"user_{role}", role, rec["payload"])
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                for f in out.iterdir():
                    z.write(f, f.name)
            st.download_button("Download package", buf.getvalue(), "camtrap_dp_demo.zip")
            st.success(f"Exported {len(approved)} approved observations.")
        except (ExportError, ReviewError) as ex:
            st.error(str(ex))
