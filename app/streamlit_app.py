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

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from scopeaudit import audit as au
from scopeaudit.export_camtrapdp import ExportError, build_tables, write_package
from scopeaudit.ingest import attach_metadata, scan_images, summary
from scopeaudit.integrity import check_media, recording_gaps
from scopeaudit.privacy import visible_deployments
from scopeaudit.report import audit_report
from scopeaudit.review import ReviewError, ReviewLog
from scopeaudit.species import read_predictions, to_payload

LABEL = "BORROWED benchmark data with SYNTHETIC deployment coordinates"
CONTEXT_NOTE = ("This demo reads Caltech Camera Traps images from the southwestern United States. "
                "Nothing shown describes the United Arab Emirates.")

SAKURA, PEARL, ROSE, DEEP, PETAL = "#F8C8DC", "#FAF3F0", "#C2557A", "#4A2B3A", "#FDE8F0"
STATES = ["ai_candidate", "human_review", "adjudication", "approved", "exported"]

st.set_page_config(page_title="SCOPE AUDIT", page_icon="🌸", layout="wide")

st.markdown(f"""<style>
.block-container{{padding-top:1.6rem;max-width:1250px;}}
h1,h2,h3{{color:{ROSE};font-weight:600;}}
section[data-testid="stSidebar"]{{background:{SAKURA};}}
.stButton>button,.stDownloadButton>button{{background:{ROSE};color:{PEARL};border:0;border-radius:10px;padding:0.45rem 1.1rem;}}
.stButton>button:hover,.stDownloadButton>button:hover{{background:{DEEP};color:{PEARL};}}
div[data-testid="stMetric"]{{background:white;border:1px solid {SAKURA};border-radius:14px;padding:12px 16px;
  box-shadow:0 1px 4px rgba(194,85,122,0.10);}}
div[data-testid="stMetricLabel"]{{color:{DEEP};}}
div[data-testid="stMetricValue"]{{color:{ROSE};font-size:1.6rem;}}
div[data-testid="stMetricLabel"] p,div[data-testid="stMetricDelta"]{{white-space:normal;overflow:visible;text-overflow:clip;}}
.hero{{background:linear-gradient(120deg,{SAKURA},{PETAL});border-radius:18px;padding:20px 26px;margin-bottom:12px;}}
.hero h1{{margin:0;font-size:2.0rem;}}
.hero p{{margin:4px 0 0 0;color:{DEEP};font-size:1.0rem;}}
.label{{display:inline-block;background:white;border:1px solid {ROSE};border-radius:999px;padding:3px 12px;
  color:{DEEP};font-size:0.82rem;margin:8px 8px 0 0;}}
.chip{{display:inline-block;border-radius:999px;padding:4px 14px;margin:2px 4px 2px 0;font-size:0.88rem;
  background:white;border:1px solid {SAKURA};color:{DEEP};}}
.chip.done{{background:{SAKURA};}}
.chip.now{{background:{ROSE};color:{PEARL};border-color:{ROSE};font-weight:600;}}
.card{{background:white;border:1px solid {SAKURA};border-radius:14px;padding:14px 18px;color:{DEEP};}}
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


def style_axes(ax) -> None:
    ax.set_facecolor("white")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(SAKURA)
    ax.tick_params(colors=DEEP, labelsize=9)
    ax.xaxis.label.set_color(DEEP)
    ax.yaxis.label.set_color(DEEP)
    ax.title.set_color(ROSE)


def new_fig(w: float = 6.0, h: float = 3.0):
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor(PEARL)
    style_axes(ax)
    return fig, ax


def chips(current: str | None, history: list[str]) -> str:
    out = []
    for s in STATES:
        cls = "now" if s == current else ("done" if s in history else "")
        out.append(f"<span class='chip {cls}'>{s.replace('_', ' ')}</span>")
    return "".join(out)


def run_design(pool: pd.DataFrame, scheme: str, budget: int, unres: int) -> dict:
    """Plan, review with the labelled stand in reviewer, and estimate."""
    if scheme == "M3" and "night" not in pool:
        scheme = "M2"
    p = au.plan(pool, scheme, budget, seed=20261106)
    ids = p["event_ids"]
    rev = pool.set_index("event_id").loc[ids]
    outcome = np.where(rev["hit"] == 1, "animal", "empty").astype(object)
    outcome[: int(round(len(ids) * unres / 100.0))] = "unresolved"
    reviews = pd.DataFrame({"event_id": ids, "outcome": outcome})
    return au.estimate(pool, scheme, reviews, seed=1)


st.markdown(f"""<div class='hero'><h1>🌷 SCOPE AUDIT</h1>
<p>How many animals hide inside the images a detector calls empty, and how few reviews it takes to find out.</p>
<span class='label'>{LABEL}</span><span class='label'>Author: Huda Mueen</span></div>""", unsafe_allow_html=True)
st.caption(CONTEXT_NOTE)

role = st.sidebar.selectbox("Role", ["reviewer", "approver", "admin"], index=0,
                            help="Roles gate what a person may do. Only an approver may approve.")
screen = st.sidebar.radio("Screen", ["1. Ingest and integrity", "2. Audit", "3. Review, approve and export"])
st.sidebar.markdown("---")
st.sidebar.caption("Free and open. Every number on screen 2 is computed live from the labelled benchmark working set.")
demo_ev, registry = load_demo()
demo_ev = demo_ev.assign(timestamp=pd.to_datetime(demo_ev["timestamp"]))

if screen.startswith("1"):
    st.header("Ingest and integrity")
    st.write("Each image is read, matched to its deployment record and checked for problems before it can enter an audit.")
    imgs = scan_images(ROOT / "data" / "demo" / "images", "Caltech Camera Traps (BORROWED)")
    imgs["event_id"] = imgs["original_filename"].str.replace(".jpg", "", regex=False)
    meta = demo_ev.rename(columns={"image_file": "original_filename"})[["original_filename", "camera_id", "deployment_id", "timestamp"]]
    media = attach_metadata(imgs, meta)
    media["image_id"] = media["event_id"].str.replace("-", "").str[:16]
    dep = registry.copy()
    flags = check_media(media, dep)
    s = summary(media, flags)
    cols = st.columns(3)
    for i, (k, v) in enumerate(s.items()):
        cols[i % 3].metric(k.replace("_", " ").capitalize(), v)
    tab_a, tab_b, tab_c, tab_d = st.tabs(["Sample images", "Flags", "Recording gaps", "Deployment registry"])
    with tab_a:
        files = sorted((ROOT / "data" / "demo" / "images").glob("*.jpg"))[:12]
        g = st.columns(4)
        for i, f in enumerate(files):
            g[i % 4].image(str(f), use_container_width=True)
        st.caption("A sample of the 60 borrowed demo images. Source and licence are in data/demo/ATTRIBUTION.md.")
    with tab_b:
        st.dataframe(flags if len(flags) else pd.DataFrame({"result": ["No integrity flags in the demo images."]}),
                     use_container_width=True)
        st.caption("Flags cover unreadable files, duplicates, timestamps outside a deployment and missing metadata.")
    with tab_c:
        gaps = recording_gaps(media)
        st.dataframe(gaps if len(gaps) else pd.DataFrame({"result": ["No prolonged gaps in this small sample."]}),
                     use_container_width=True)
    with tab_d:
        st.dataframe(visible_deployments(dep, role), use_container_width=True)
        st.caption(f"Coordinates are SYNTHETIC. Sensitive fields are shown according to the role selected: {role}.")

elif screen.startswith("2"):
    st.header("Audit of AI negative events")
    events = load_events()
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        T = c1.select_slider("Detector threshold", [0.1, 0.2, 0.4, 0.6, 0.8], value=0.2,
                             help="An event is called empty only if no frame reaches this animal confidence.")
        budget = c2.slider("Review budget (events)", 50, 800, 200, step=50)
        scheme = c3.selectbox("Sampling method", list(au.METHOD_NAMES), index=2, format_func=lambda k: au.METHOD_NAMES[k])
        unres = c4.slider("Unresolved reviews (share)", 0, 10, 0, format="%d%%")
    pool = au.build_pool(events, T)
    if scheme == "M3" and "night" not in pool:
        scheme = "M2"
    e = run_design(pool, scheme, budget, unres)
    base = run_design(pool, "M0", budget, unres)
    truth = float(pool["hit"].mean())
    st.caption("The reviewer here is a stand in that reads benchmark labels. In use, a person reviews each event.")
    m = st.columns([1, 1.1, 1.5, 1.3])
    m[0].metric("AI negative events", f"{len(pool):,}")
    m[1].metric("Estimated omission rate", f"{100 * e['estimate']:.2f}%")
    iname, (lo, hi) = au.headline_interval(e)
    m[2].metric(f"95% interval ({iname})", f"{100 * lo:.2f}% to {100 * hi:.2f}%")
    m[3].metric("Hidden found per 100 reviews", f"{e['yield_per_100_reviews']:.1f}",
                delta=f"{e['yield_per_100_reviews'] - base['yield_per_100_reviews']:+.1f} vs simple random",
                delta_color="off")
    st.markdown(f"<div class='card'>Reviewed <b>{e['reviewed']}</b> events, found <b>{e['hidden_found']}</b> with an animal, "
                f"<b>{e['unresolved']}</b> unresolved. Benchmark value for this pool, known only because the data are labelled: "
                f"<b>{100 * truth:.2f}%</b>.</div>", unsafe_allow_html=True)
    if "sensitivity" in e:
        sb = e["sensitivity"]
        st.info(f"Unresolved reviews are handled by bounds, not guessed: the rate lies between {100 * sb['lower_bound']:.2f}% and "
                f"{100 * sb['upper_bound']:.2f}% if every unresolved event were empty or an animal.")

    left, right = st.columns(2)
    with left:
        st.subheader("Intervals against the benchmark")
        fig, ax = new_fig(6.0, 3.2)
        items = list(e["interval"].items())
        for i, (k_, v) in enumerate(items):
            ax.plot([100 * v[0], 100 * v[1]], [i, i], color=ROSE, lw=3, solid_capstyle="round")
            ax.plot([100 * e["estimate"]], [i], "o", color=DEEP, ms=5)
        ax.axvline(100 * truth, color=DEEP, ls="--", lw=1.2, label="benchmark value")
        ax.set_yticks(range(len(items)))
        ax.set_yticklabels([k_ for k_, _ in items])
        ax.invert_yaxis()
        ax.set_xlabel("False omission rate (%)")
        ax.legend(frameon=False, fontsize=8)
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)
    with right:
        st.subheader("Chosen design against simple random")
        fig, ax = new_fig(6.0, 3.2)
        labels = [au.METHOD_NAMES[scheme] if scheme != "M0" else "Chosen (simple random)", "Simple random"]
        vals = [e["yield_per_100_reviews"], base["yield_per_100_reviews"]]
        bars = ax.bar(["Chosen", "Simple random"], vals, color=[ROSE, SAKURA], width=0.5)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.1f}", ha="center", va="bottom", color=DEEP, fontsize=9)
        ax.set_ylabel("Hidden found per 100 reviews")
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)
        st.caption(f"Chosen method: {au.METHOD_NAMES[scheme]}. Same budget, same threshold, same stand in reviewer. "
                   "Risk weighting pays off most in the stress regime (threshold 0.6 or higher, see results/RESULTS.md); "
                   "at low thresholds simple random can do as well or better.")

    if "strata" in e:
        st.subheader("Where the reviews went")
        sd = pd.DataFrame(e["strata"])
        fig, ax = new_fig(9.0, 3.0)
        x = np.arange(len(sd))
        ax.bar(x - 0.2, sd["pool"] / sd["pool"].sum(), 0.4, color=SAKURA, label="share of pool")
        ax.bar(x + 0.2, sd["reviewed"] / max(sd["reviewed"].sum(), 1), 0.4, color=ROSE, label="share of reviews")
        ax.set_xticks(x)
        ax.set_xticklabels(sd["stratum"], rotation=30, ha="right")
        ax.set_ylabel("Share")
        ax.legend(frameon=False, fontsize=8)
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)
        with st.expander("Strata table"):
            st.dataframe(sd, use_container_width=True)
    with st.expander("All intervals as a table"):
        st.dataframe(pd.DataFrame([{"interval": k_, "lower %": 100 * v[0], "upper %": 100 * v[1]} for k_, v in e["interval"].items()]),
                     use_container_width=True)
    with st.expander("How to read this screen"):
        st.write("The false omission rate is the share of events that contain an animal among those the detector called empty. "
                 "The interval shows how sure the audit is after the chosen number of reviews. Risk weighted sampling spends reviews "
                 "where hidden animals are likelier, so it finds more of them per review than simple random sampling. "
                 "The dashed line is known only because this benchmark is fully labelled.")
    report_text = audit_report(e, T, LABEL)
    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button("Download report", report_text, "scope_audit_report.md")
    d2.download_button("Download numbers (JSON)", json.dumps(e, indent=2, default=str), "scope_audit_numbers.json")
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
    state = L.current_state(row)
    hist = [h["state"] for h in L.history(row)]
    st.markdown(chips(state, hist), unsafe_allow_html=True)
    left, right = st.columns([2, 1])
    left.image(str(img), caption="Borrowed image from Caltech Camera Traps", use_container_width=True)
    right.write(f"Current state: **{(state or 'not yet in the log').replace('_', ' ')}**")
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
    hrows = [{k: v for k, v in h.items() if k != "payload"} | {"payload": json.dumps(h["payload"])} for h in L.history(row)]
    if hrows:
        st.dataframe(pd.DataFrame(hrows), use_container_width=True)
    else:
        st.caption("No records yet for this event. Record a review to start its history.")
    ok, bad = L.verify_chain()
    (st.success if ok else st.error)("Log integrity: " + ("chain verified" if ok else f"chain broken at record {bad}"))
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
