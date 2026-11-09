"""Measles SignalCheck AI - dashboard for immunization coordinators (Milestone 6).

Run from the project root:
    .venv\\Scripts\\python.exe -m streamlit run app\\streamlit_app.py

All figures come from the verified connector and deterministic signal rules. Investigation
briefs are OFFLINE DEMONSTRATIONS (hand-written fixtures) unless live Claude is explicitly
enabled; live validation is deferred (PROJECT_DECISIONS.md D-025).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signalcheck import dashboard_data as dd  # noqa: E402
from signalcheck import demo_briefs  # noqa: E402
from signalcheck.brief_validator import validate_draft  # noqa: E402
from signalcheck.briefing import observations_from_packet, render_markdown  # noqa: E402

# ------------------------------------------------------------------ palette (reference, validated)
BLUE, ORANGE, RED = "#2a78d6", "#eb6834", "#e34948"
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
SIGNAL_LABELS = {
    "recorded_dose_change": "Recorded-dose change ≥30%",
    "reported_coverage_change": "Coverage swing ≥30 pts",
    "implausible_coverage": "Coverage above 100%",
    "state_benchmark_divergence": "Differs from state ≥25 pts",
    "small_denominator_caution": "Small numbers",
    "insufficient_evidence": "Insufficient evidence",
}

st.set_page_config(page_title="Measles SignalCheck AI", page_icon="💉", layout="wide")


def style(fig: go.Figure, title: str, y_title: str | None, height: int = 340, years: bool = True) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=INK), x=0, xanchor="left"),
        height=height, margin=dict(l=8, r=8, t=48, b=40), plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
        font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", color=INK2, size=13),
        hovermode="x unified", legend=dict(orientation="h", y=-0.12, x=0, xanchor="left", yanchor="top"),
        hoverlabel=dict(bgcolor="white", font_color=INK))
    if years:
        fig.update_xaxes(showgrid=False, linecolor=AXIS, tickcolor=AXIS, dtick=1, title=None, range=[2014.6, 2022.4])
    else:
        fig.update_xaxes(linecolor=AXIS, tickcolor=AXIS, title=None)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=AXIS, title=y_title, rangemode="tozero")
    return fig


def line(fig, x, y, name, color, dash=None, fmt=",.0f"):
    fig.add_trace(go.Scatter(x=x, y=y, name=name, mode="lines+markers",
                             line=dict(color=color, width=2, dash=dash),
                             marker=dict(size=8, color=color, line=dict(width=2, color=SURFACE)),
                             hovertemplate=f"%{{y:{fmt}}}<extra>{name}</extra>"))


@st.cache_resource(show_spinner="Loading verified data…")
def bundle(raw: str, ref: str):
    """Cached per data location; ``ref`` is part of the key so region availability is re-checked."""
    return dd.load_bundle(Path(raw))


@st.cache_data(show_spinner="Running signal rules for 92 municipalities…")
def signals_for(raw: str, ref: str, y1: int) -> pd.DataFrame:
    return dd.signal_table(bundle(raw, ref), y1)


def key_configured() -> bool:
    """True if a non-placeholder key exists. Never reads the value into the UI."""
    if os.getenv("ANTHROPIC_API_KEY"):
        return True
    env = ROOT / ".env"
    if env.exists():
        for line_ in env.read_text(encoding="utf-8").splitlines():
            if line_.strip().startswith("ANTHROPIC_API_KEY=") and line_.split("=", 1)[1].strip() not in ("", "your-api-key-here"):
                return True
    return False


def redact_paths(text: str) -> str:
    """Replace absolute server/computer paths with project-relative ones before showing them to visitors."""
    for root in {str(ROOT), str(ROOT.resolve()), str(Path(os.path.realpath(ROOT)))}:
        text = text.replace(root, ".")
    # Any remaining absolute path keeps only its file name (no user names or server directories).
    text = re.sub(r"[A-Za-z]:\\(?:[^\\\r\n:*?\"<>|]+\\)+", "…\\\\", text)
    return re.sub(r"(?<![\w.:/])/(?:[^/\s:'\"]+/)+", "…/", text)   # not URLs (http://host/...)


def fetch_public_data() -> tuple[bool, str]:
    """Download the public TabNet sample with the repository's own fetch scripts (no API, no key).

    Each script contacts only tabnet.datasus.gov.br, checks the content before saving, writes nothing if a
    query fails, and refuses to replace an existing snapshot (no --force is ever passed from the app).
    """
    lock = ROOT / "data" / "raw" / ".download.lock"      # data/raw/* is git-ignored
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)   # one download at a time (shared hosts)
    except FileExistsError:
        if time.time() - lock.stat().st_mtime < 900:
            return False, "Another download is already in progress. Wait a minute, then reload the page."
        lock.unlink(missing_ok=True)                              # stale lock (>15 min): clear and retry
        return fetch_public_data()
    os.close(fd)
    log = []
    try:
        for script in ("fetch_tabnet.py", "fetch_health_regions.py"):
            try:
                r = subprocess.run([sys.executable, str(ROOT / "scripts" / script)], capture_output=True,
                                   text=True, timeout=600, cwd=str(ROOT))
            except subprocess.TimeoutExpired:
                return False, f"{script}: timed out after 10 minutes"
            tail = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-3:]
            # Show only the last lines, with local paths removed (nothing about the host is exposed).
            log.append(f"{script}: exit {r.returncode} | " + redact_paths(" / ".join(tail)))
            if r.returncode != 0:
                return False, "\n".join(log)
        return True, "\n".join(log)
    finally:
        lock.unlink(missing_ok=True)


# ------------------------------------------------------------------------------ data
RAW_DIR, REF_DIR = str(dd.raw_dir()), str(dd.ref_dir())
try:
    B = bundle(RAW_DIR, REF_DIR)
except Exception as e:  # missing or altered raw files
    st.title("Measles SignalCheck AI")
    if not (Path(RAW_DIR) / "manifest.json").exists():
        st.warning("**The public data sample is not on this computer or server yet.** It is not stored in the "
                   "GitHub repository. It is downloaded directly from the Brazilian Ministry of Health's DATASUS "
                   "TabNet (public, aggregate, no login; about 23 KB of tables plus a 2.1 MB form page for the "
                   "health-region list). No Anthropic API is called.", icon="📥")
        if st.button("Download the public data from DATASUS TabNet", type="primary"):
            with st.spinner("Downloading from tabnet.datasus.gov.br …"):
                ok, log = fetch_public_data()
            if ok:
                st.cache_resource.clear()
                st.cache_data.clear()
                st.rerun()
            st.error("The download did not complete (DATASUS TabNet may be unavailable or busy). Nothing was "
                     "half-saved. Try again later, or run the fetch scripts locally.")
            st.code(log)
        st.caption("Or run locally: `python scripts/fetch_tabnet.py` and `python scripts/fetch_health_regions.py`.")
    else:
        st.error("The data sample failed its integrity check (a raw file is missing or was altered), so it "
                 "will not be used. Re-download it with the fetch scripts.")
        st.code("python scripts/fetch_tabnet.py\npython scripts/fetch_health_regions.py")
    st.caption(f"Details: {type(e).__name__}: {redact_paths(str(e))}")
    st.stop()

units = B.units

# Optional deep links, e.g. ?period=2019&unit=330490&tab=Investigation+brief (invalid values are ignored).
TABS = ["Overview", "Municipality trends", "Signals", "Investigation brief", "Data & limitations"]
qp = st.query_params
q_period = next((p for p in dd.PERIODS if str(p[0]) == qp.get("period", "")), (2019, 2020))
q_tab = qp.get("tab") if qp.get("tab") in TABS else "Overview"
q_unit = qp.get("unit", "330490")

# ---------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### 🔎 Measles SignalCheck AI")
    st.caption("Rio de Janeiro state · MMR first dose · 2015–2022")
    period = st.selectbox("Comparison period", dd.PERIODS, index=dd.PERIODS.index(q_period),
                          format_func=lambda p: f"{p[0]} → {p[1]}",
                          help="Only consecutive years within 2015–2022 are compared (like-for-like reporting).")
    y1, y2 = period
    regions = ["All health regions"] + (sorted(units.cir_name.unique()) if B.regions_available else [])
    q_region = qp.get("region") if qp.get("region") in regions else "All health regions"
    region = st.selectbox("Health region (Região de Saúde)", regions, index=regions.index(q_region),
                          disabled=not B.regions_available,
                          help=None if B.regions_available else "Run scripts/fetch_health_regions.py to enable.")
    in_region = units if region == "All health regions" else units[units.cir_name == region]
    names = dict(zip(in_region.unit_code, in_region.unit_name.str.title()))
    default_code = q_unit if q_unit in names else ("330490" if "330490" in names else next(iter(names)))
    code = st.selectbox("Municipality", list(names), index=list(names).index(default_code),
                        format_func=lambda c: f"{names[c]} ({c})")
    st.divider()
    st.markdown("**Mode**")
    st.info("**Offline demonstration mode.** Briefs shown are hand-written examples validated by the same "
            "rules. No Claude API calls are made.", icon="🧪")
    has_key = key_configured()
    live_allowed = has_key and os.getenv("SIGNALCHECK_ENABLE_LIVE") == "1"
    st.toggle("Live Claude briefs", value=False, disabled=not live_allowed, key="live",
              help=("Disabled: no API key configured, and live validation is deferred (decision D-025)."
                    if not has_key else "Disabled: set SIGNALCHECK_ENABLE_LIVE=1 to allow paid calls."))
    st.caption(f"Data retrieved {B.retrieved_at} from DATASUS TabNet (SI-PNI, SINASC). "
               "Raw files verified against SHA-256 manifest.")

name = names[code]
sig = signals_for(RAW_DIR, REF_DIR, y1)
sig_region = sig if region == "All health regions" else sig[sig.health_region == region]

st.title("Measles SignalCheck AI")
st.markdown("**Find municipalities whose recorded measles first-dose (MMR1) data changed sharply, "
            "and decide what to verify first — without mistaking a records problem for a change in vaccination.**")
st.caption("🧪 Offline demonstration: figures are official public DATASUS data processed by tested rules. "
           "Live Claude generation is **not enabled**; no Anthropic API calls are made.")

tab_over, tab_explore, tab_signals, tab_brief, tab_data = st.tabs(TABS, default=q_tab)

# --------------------------------------------------------------------------- overview
with tab_over:
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader("The problem")
        st.markdown(
            "Between 2019 and 2020 the MMR first-dose coverage published for Rio de Janeiro state fell from "
            f"**{dd.TABNET_STATE_COVERAGE[2019]:.2f}%** to **{dd.TABNET_STATE_COVERAGE[2020]:.2f}%** "
            "(DATASUS TabNet). Some municipalities moved far more than others. For each one, a coordinator needs "
            "to know whether **recorded doses** fell, whether the **denominator** moved, or whether values are "
            "**implausible** — and what to check before acting.\n\n"
            "This tool flags those situations with transparent, tested rules and packages the evidence so every "
            "statement can be traced to an official figure.")
    with right:
        st.subheader("How to use it")
        st.markdown("1. Pick a **comparison period** and **health region** in the sidebar.\n"
                    "2. Review **Signals** to see which municipalities need attention.\n"
                    "3. Open a municipality's **trends** and **investigation brief**.\n"
                    "4. Read **Data & limitations** before drawing conclusions.")
    st.divider()
    scope_codes = list(in_region.unit_code)
    area = dd.area_series(B, scope_codes).set_index("year")
    state = dd.area_series(B, list(units.unit_code)).set_index("year")
    scope_label = "Rio de Janeiro state" if region == "All health regions" else region
    k1, k2, k3, k4 = st.columns(4)
    d1, d2 = area.loc[y1, "doses"], area.loc[y2, "doses"]
    k1.metric(f"Recorded doses {y2}", f"{d2:,.0f}", f"{(d2 / d1 - 1) * 100:+.1f}% vs {y1}",
              delta_color="off", border=True, help=f"Sum over {scope_label} municipalities (observed counts).")
    c2 = area.loc[y2, "coverage_weighted"]
    k2.metric(f"Coverage {y2} (weighted)", f"{c2:.1f}%",
              f"{c2 - area.loc[y1, 'coverage_weighted']:+.1f} pts vs {y1}", delta_color="off", border=True,
              help="Ratio of summed doses to summed back-calculated denominators — reproduces TabNet's state "
                   "total within 0.3 pts. Not an average of municipal percentages.")
    k3.metric("Dose-change signals", f"{int(sig_region.recorded_dose_change.sum())} of {len(sig_region)}",
              border=True, help=f"Municipalities whose recorded doses changed by 30% or more, {y1}→{y2}.")
    k4.metric("Coverage above 100%", f"{int(sig_region.implausible_coverage.sum())} of {len(sig_region)}",
              border=True, help=f"Municipalities with published coverage above 100% in {y1} or {y2}. This can arise "
                                "when doses and the target population are attributed to different places; not corrected.")

    a, b_ = st.columns(2, gap="large")
    with a:
        fig = go.Figure()
        line(fig, area.index, area.doses, scope_label, BLUE)
        fig.add_vrect(x0=2019.5, x1=2021.5, fillcolor=GRID, opacity=0.35, line_width=0,
                      annotation_text="2020–21", annotation_position="top left",
                      annotation_font=dict(size=11, color=INK2))
        st.plotly_chart(style(fig, f"Recorded MMR1 doses, {scope_label}", "Doses (age 1 year)"), width="stretch")
    with b_:
        rc = dd.region_changes(B, y1, y2)
        if len(rc):
            colors = [RED if v < 0 else BLUE for v in rc.change_pct]
            fig = go.Figure(go.Bar(x=rc.change_pct, y=rc.cir_name, orientation="h", marker_color=colors,
                                   marker_line=dict(width=0), text=[f"{v:+.1f}%" for v in rc.change_pct],
                                   textposition="outside", textfont=dict(color=INK2),
                                   hovertemplate="%{y}: %{x:+.1f}%<extra>recorded doses</extra>"))
            fig = style(fig, f"Recorded doses by health region, {y1}→{y2}", None, height=360, years=False)
            lo, hi = min(0, rc.change_pct.min()), max(0, rc.change_pct.max())
            pad = (hi - lo) * 0.22 + 5
            fig.update_traces(cliponaxis=False)
            fig.update_xaxes(dtick=None, ticksuffix="%", zeroline=True, zerolinecolor=AXIS, showgrid=True,
                             gridcolor=GRID, range=[lo - (pad if lo < 0 else 0), hi + (pad if hi > 0 else 2)])
            fig.update_yaxes(title=None, gridcolor="rgba(0,0,0,0)", rangemode=None)
            fig.update_layout(hovermode="closest", showlegend=False)
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Health-region mapping not loaded.")
    st.caption("Doses are counts of recorded first doses for 1-year-olds, attributed to the municipality where "
               "they were recorded. Recorded doses are records, not confirmed vaccinations. The shaded 2020–21 "
               "band may combine service disruption with registration-system effects; the data cannot separate them.")

# --------------------------------------------------------------------- municipality trends
with tab_explore:
    st.subheader(f"{name} — {units.set_index('unit_code').loc[code, 'cir_name']}")
    s = dd.unit_series(B, code).set_index("year")
    a, b_ = st.columns(2, gap="large")
    with a:
        fig = go.Figure()
        line(fig, s.index, dd.indexed(s.doses), name, BLUE, fmt=".0f")
        line(fig, state.index, dd.indexed(state.doses), "Rio de Janeiro state", ORANGE, dash="dot", fmt=".0f")
        fig.add_hline(y=100, line=dict(color=AXIS, width=1))
        st.plotly_chart(style(fig, "Recorded doses, indexed (2015 = 100)", "Index"), width="stretch")
        st.caption("Indexing puts a municipality and the state on one scale (no second axis).")
    with b_:
        fig = go.Figure()
        line(fig, s.index, s.coverage, f"{name} (published)", BLUE, fmt=".2f")
        fig.add_hline(y=100, line=dict(color=RED, width=1, dash="dash"), annotation_text="100%",
                      annotation_position="bottom right", annotation_font=dict(color=INK2, size=11))
        f = style(fig, f"Published MMR1 coverage, {name}", "Coverage (%)")
        f.update_yaxes(ticksuffix="%")
        f.update_layout(showlegend=False)
        st.plotly_chart(f, width="stretch")
        st.caption("Values above 100% are shown as published. They can arise when doses and the target population "
                   "are attributed to different places; they are neither corrected nor interpreted.")
    table = s.rename(columns={"doses": "Recorded doses", "coverage": "Published coverage (%)",
                              "births_previous_year": "SINASC births, previous year (reference)"})
    st.dataframe(table.T.rename(columns=str), width="stretch")
    st.caption("SINASC births are an independent reference (by mother's residence). They are not the official "
               "denominator, which is unpublished.")

# ---------------------------------------------------------------------------- signals
with tab_signals:
    st.subheader(f"Signals, {y1} → {y2} · {('Rio de Janeiro state' if region == 'All health regions' else region)}")
    st.markdown("Signals are **review triggers** from documented, configurable thresholds "
                "(`config/signal_thresholds.toml`). They say *what to look at*, never *why it happened*.")
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        c1.markdown("**Change signals**  \n📉 *Recorded-dose change* — recorded doses moved ≥30%.  \n"
                    "📊 *Coverage swing* — published coverage moved ≥30 points.  \n"
                    "↔️ *Differs from state* — dose change ≥25 points away from the statewide change.")
        c2.markdown("**Data-quality warnings**  \n⚠️ *Coverage above 100%* — implausible as true coverage.  \n"
                    "🔍 *Small numbers* — percentages are volatile.  \n"
                    "❔ *Insufficient evidence* — inputs missing or invalid; nothing is computed.")
        c3.markdown("**Causes are not shown**  \nThe data cannot tell why a value changed. Possible explanations "
                    "appear only in the investigation brief, under *Unverified possibilities (not findings)*.")
    counts = {SIGNAL_LABELS[k]: int(sig_region[k].sum()) for k in SIGNAL_LABELS}
    fig = go.Figure(go.Bar(x=list(counts.values()), y=list(counts), orientation="h", marker_color=BLUE,
                           text=list(counts.values()), textposition="outside", textfont=dict(color=INK2),
                           hovertemplate="%{y}: %{x} municipalities<extra></extra>"))
    fig = style(fig, f"Municipalities flagged ({len(sig_region)} in scope)", None, height=280, years=False)
    fig.update_xaxes(showgrid=True, gridcolor=GRID, range=[0, max(counts.values() or [1]) * 1.15 + 1])
    fig.update_traces(cliponaxis=False)
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)", rangemode=None)
    fig.update_layout(hovermode="closest", showlegend=False)
    st.plotly_chart(fig, width="stretch")

    chosen = st.pills("Show municipalities with", list(SIGNAL_LABELS), selection_mode="multi",
                      default=["recorded_dose_change"], format_func=lambda k: SIGNAL_LABELS[k])
    view = sig_region.copy()
    if chosen:
        view = view[view[list(chosen)].any(axis=1)]
    view = view.sort_values("dose_change_pct", na_position="last")
    cols = ["municipality", "health_region", "dose_change_pct", "coverage_change_pp", "coverage_to"] + list(SIGNAL_LABELS)
    if view.empty:
        st.info("No municipalities in this scope match the selected signals for this period.", icon="ℹ️")
    st.dataframe(view[cols], hide_index=True, width="stretch", column_config={
        "municipality": "Municipality", "health_region": "Health region",
        "dose_change_pct": st.column_config.NumberColumn("Recorded doses change", format="%+.1f%%"),
        "coverage_change_pp": st.column_config.NumberColumn("Coverage change (pts)", format="%+.2f"),
        "coverage_to": st.column_config.NumberColumn(f"Published coverage {y2}", format="%.2f%%"),
        **{k: st.column_config.CheckboxColumn(v) for k, v in SIGNAL_LABELS.items()}})
    st.download_button("Download this table (CSV)", view[cols].to_csv(index=False).encode("utf-8"),
                       file_name=f"signals_rj_{y1}_{y2}.csv", mime="text/csv")

# --------------------------------------------------------------------------- brief
with tab_brief:
    st.subheader(f"Investigation brief · {name} · {y1} → {y2}")
    pk = dd.packet(B, code, y1)
    obs = observations_from_packet(pk)
    st.markdown("#### Verified observations")
    st.caption("Generated by Python from the evidence packet. Every number traces to an official figure (F#) "
               "or a documented calculation (D#).")
    if not obs:
        st.success("No signals for this municipality and period: recorded doses and published coverage stayed "
                   "within the review thresholds.", icon="✅")
    for o in obs:
        sigd = next(x for x in pk["signals"] if x["id"] == o.signal_id)
        with st.container(border=True):
            st.markdown(f"**{o.id} · {SIGNAL_LABELS[o.classification]}** — {o.text}")
            st.caption(f"Evidence: {', '.join(o.evidence_ids)}")
            for c in sigd["cautions"]:
                st.caption(f"⚠️ {c}")
            with st.expander("What this cannot tell you"):
                for c in sigd["cannot_conclude"]:
                    st.markdown(f"- {c}")

    st.markdown("#### Brief")
    draft = demo_briefs.get(code, y1)
    if draft is not None:
        report = validate_draft(draft, obs, list(units.unit_name))
        st.warning(demo_briefs.LABEL, icon="🧪")
        badge = {"accepted": "✅ accepted", "needs_human_review": "🟡 needs human review",
                 "rejected": "⛔ rejected"}[report.verdict]
        st.markdown(f"Grounding validation: **{badge}** · citation accuracy "
                    f"{report.citation_accuracy:.0%} · grounding accuracy {report.grounding_accuracy:.0%}")
        md = render_markdown(pk, draft, report.verdict, {"source": "offline demonstration fixture",
                                                          "generated_by": "project author, not Claude"})
        with st.container(border=True):
            st.markdown(md.split("\n", 2)[2].replace("\n## ", "\n##### "))
        st.download_button("Download brief (Markdown)", md.encode("utf-8"),
                           file_name=f"brief_{code}_{y1}_{y2}_DEMO.md", mime="text/markdown")
    else:
        st.info("No demonstration brief exists for this selection. Demonstration briefs are available for "
                + ", ".join(f"{dict(zip(units.unit_code, units.unit_name.str.title()))[c]} {y}→{y + 1}"
                            for c, y in demo_briefs.available())
                + ". The verified observations above are the evidence a brief would be built from.", icon="ℹ️")
    st.button("Generate brief with Claude (paid API call)", disabled=not st.session_state.get("live"),
              help="Disabled in offline demonstration mode. Live validation is deferred (D-025).")
    st.download_button("Download evidence packet (JSON)", json.dumps(pk, ensure_ascii=False, indent=2).encode("utf-8"),
                       file_name=f"evidence_packet_{code}_{y1}_{y2}.json", mime="application/json")

# ----------------------------------------------------------------------- data & limits
with tab_data:
    st.subheader("Data, methods and limitations")
    st.error("**Reporting-system break in 2023.** Brazil replaced its immunization information system in "
             "2023 (new SI-PNI integrated with RNDS) and changed the coverage method from 2024. This dashboard "
             "only compares 2015–2022 and refuses comparisons across the break.", icon="🚧")
    a, b_ = st.columns(2, gap="large")
    with a:
        st.markdown("#### Sources")
        st.markdown(
            "- **Doses applied** and **published coverage** (Tríplice Viral D1): Ministério da Saúde, "
            "[DATASUS TabNet SI-PNI](http://tabnet.datasus.gov.br/cgi/dhdat.exe?bd_pni/cpnibr.def), 2015–2022\n"
            "- **Live births** by mother's residence: [SINASC](http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinasc/cnv/nvrj.def), 2014–2021\n"
            "- **Health regions**: DATASUS TabNet CIR selector (official municipality → region mapping)\n"
            f"- Retrieved {B.retrieved_at}; raw files verified by SHA-256 on every load")
        st.markdown("#### Permitted readings")
        st.markdown("- Describe changes in **recorded doses** and **published coverage** within 2015–2022\n"
                    "- Flag municipalities **for investigation**\n"
                    "- Use SINASC births as a labelled **reference**, never as the official denominator")
    with b_:
        st.markdown("#### Known limitations")
        for x in dd.packet(B, "330490", 2019)["limitations"]:
            st.markdown(f"- {x['text']}")
        st.markdown("#### Not permitted")
        for x in dd.packet(B, "330490", 2019)["prohibited_interpretations"]:
            st.markdown(f"- {x}")
    st.markdown("#### Privacy and AI use")
    st.markdown("- This dashboard uses only public, aggregate municipality-year data. It has no user accounts "
                "and stores nothing about visitors.\n"
                "- **Live Claude generation is not enabled.** The dashboard contains no code path that calls the "
                "Anthropic API, and no API key is configured.\n"
                "- If you are viewing a hosted copy (for example on Streamlit Community Cloud), the hosting "
                "platform may collect its own usage statistics; this app does not add any.")
    st.caption("Full documentation: DATA_CARD.md, DATA_SOURCES.md, PROJECT_DECISIONS.md, "
               "docs/SECURITY_AND_GOVERNANCE.md. This is an independent project, not an official tool.")
