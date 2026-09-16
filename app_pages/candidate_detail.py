"""
app_pages/candidate_detail.py — Detailed Scientific Inspection Card for ExoTrace.

Features:
  - Deep astrophysical parameters (Depth, Ingress, Egress, Asymmetry A).
  - Raw and detrended light curve visualizers.
  - Side-by-side physical comparison (Comet dust tail transit vs. Planet symmetric transit).
  - Researcher review, classification override, and notes persistence.
  - 100% Bilingual (Arabic & English).
"""

import os
import streamlit as st
from lib.i18n import t, get_theme, get_lang
from lib.data_loader import (
    load_lightcurve,
    get_candidate_plots,
    save_review,
    get_review,
)

is_en = (get_lang() == "en")
is_light = (get_theme() == "light")

# ── Candidate Selection Verification ───────────────────────────────
candidate = st.session_state.get("selected_candidate")

if not candidate:
    st.warning(t("detail_no_candidate_warning"))
    if st.button(t("detail_back_to_candidates"), icon=":material/arrow_back:"):
        st.switch_page("app_pages/candidates.py")
    st.stop()

tic_id = int(candidate.get("tic_id", 0))
sector = int(candidate.get("sector", 0))
event_id = str(candidate.get("event_id", ""))
start_time = candidate.get("start_time")
classification_display = candidate.get("classification_en" if is_en else "classification_ar", "Under review" if is_en else "مرشح قيد التدقيق")
badge_color = candidate.get("badge_color", "#ef4444")
depth = candidate.get("depth_display", "—")
ingress = candidate.get("ingress_display_en" if is_en else "ingress_display_ar", candidate.get("ingress_display", "—"))
egress = candidate.get("egress_display_en" if is_en else "egress_display_ar", candidate.get("egress_display", "—"))
asymmetry = candidate.get("asym_display", "—")
duration = candidate.get("duration_display_en" if is_en else "duration_display_ar", candidate.get("duration_display", "—"))
asym_shape = candidate.get("asym_shape_display", "—")
asym_area = candidate.get("asym_area_display", "—")
slope_ratio = candidate.get("slope_ratio_display", "—")
snr_val = candidate.get("snr_display", "—")
morph_score = candidate.get("morphology_score_display", "—")
coverage_display = candidate.get("gap_flag_display_en" if is_en else "gap_flag_display_ar", "—")
dominance_display = candidate.get("dominance_display_en" if is_en else "dominance_display_ar", "—")

# ── Header Card ────────────────────────────────────────────────────
title_color = "#0f172a" if is_light else "#f8fafc"
sub_color = "#475569" if is_light else "#94a3b8"

with st.container(border=True):
    h_col1, h_col2 = st.columns([3, 1], vertical_alignment="center")
    with h_col1:
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:12px;">
                <span style="font-size:2.2rem;">☄️</span>
                <div>
                    <div style="display:flex;align-items:center;gap:10px;">
                        <h2 style="margin:0;font-size:1.6rem;font-weight:900;color:{title_color};">
                            TIC {tic_id}
                        </h2>
                        <span style="background:{badge_color}22;color:{badge_color};border:1px solid {badge_color}55;padding:3px 12px;border-radius:12px;font-size:0.8rem;font-weight:800;">
                            {classification_display}
                        </span>
                    </div>
                    <div style="color:{sub_color};font-size:0.85rem;margin-top:4px;">
                        {t('detail_meta_sub', sector=sector)}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with h_col2:
        if st.button(t("detail_back_to_list"), icon=":material/arrow_back:"):
            st.switch_page("app_pages/candidates.py")

# ── Astrophysical Metrics Row ──────────────────────────────────────
with st.container(horizontal=True):
    st.metric(t("metric_dip_depth"), depth, border=True)
    st.metric(t("metric_ingress_time"), ingress, border=True)
    st.metric(t("metric_egress_time"), egress, border=True)
    st.metric(t("metric_asymmetry"), asymmetry, border=True)
    st.metric(t("metric_total_duration"), duration, border=True)

# ── Multi-metric Diagnostics Container ─────────────────────────────
with st.container(border=True):
    st.subheader(f"🔬 {t('section_multimetric_diagnostics')}", anchor=False)
    st.caption(t("multimetric_caption"))

    diag_c1, diag_c2, diag_c3, diag_c4 = st.columns(4)
    with diag_c1:
        st.metric(t("metric_asym_shape"), asym_shape, border=True)
    with diag_c2:
        st.metric(t("metric_asym_area"), asym_area, border=True)
    with diag_c3:
        st.metric(t("metric_slope_ratio"), slope_ratio, border=True)
    with diag_c4:
        st.metric(t("metric_morphology_score"), morph_score, border=True)

    diag_sub1, diag_sub2, diag_sub3 = st.columns(3)
    with diag_sub1:
        st.metric(t("metric_snr_mad"), snr_val, border=True)
    with diag_sub2:
        st.metric(t("metric_coverage_status"), coverage_display, border=True)
    with diag_sub3:
        st.metric(t("metric_dominance_type"), dominance_display, border=True)

    st.info(f"ℹ️ {t('diag_preliminary_notice')}")

# ── Light Curve Visualization (Raw vs Detrended) ───────────────────
lc_col1, lc_col2 = st.columns(2)
import plotly.express as px

with lc_col1:
    with st.container(border=True):
        st.subheader(f"📈 {t('lightcurve_raw')}", anchor=False)
        st.caption(t("detail_raw_caption"))
        raw_lc = load_lightcurve(tic_id, sector, flat=False)
        if not raw_lc.empty and "flux" in raw_lc.columns:
            fig_raw = px.scatter(raw_lc, x="time", y="flux", render_mode="webgl")
            fig_raw.update_traces(marker=dict(size=3, color="#38bdf8", opacity=0.7))
            fig_raw.update_layout(
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis_title="Time (BJD)",
                yaxis_title="Flux",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8")
            )
            st.plotly_chart(fig_raw, use_container_width=True, key=f"raw_lc_{tic_id}")
        else:
            st.info(t("error_no_lightcurve"))

with lc_col2:
    with st.container(border=True):
        st.subheader(f"📉 {t('lightcurve_detrended')}", anchor=False)
        st.caption(t("detail_detrended_caption"))
        flat_lc = load_lightcurve(tic_id, sector, flat=True)
        if not flat_lc.empty and "flux_flat" in flat_lc.columns:
            fig_flat = px.scatter(flat_lc, x="time", y="flux_flat", render_mode="webgl")
            fig_flat.update_traces(marker=dict(size=3, color="#fbbf24", opacity=0.7))
            fig_flat.update_layout(
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis_title="Time (BJD)",
                yaxis_title="Normalized Flux",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8")
            )
            # Add a zero/baseline reference line
            fig_flat.add_hline(y=1.0, line_dash="dash", line_color="#475569", opacity=0.5)
            
            e_time = candidate.get("end_time")
            import pandas as pd
            if pd.notna(start_time) and pd.notna(e_time):
                fig_flat.add_vrect(
                    x0=start_time, x1=e_time,
                    fillcolor="red", opacity=0.15,
                    layer="below", line_width=0,
                )
                
            st.plotly_chart(fig_flat, use_container_width=True, key=f"flat_lc_{tic_id}")
        else:
            st.info(t("error_no_lightcurve"))

# ── Plot Archives Gallery (if any) ─────────────────────────────────
plots = get_candidate_plots(tic_id, sector, start_time=start_time)
if plots:
    with st.container(border=True):
        st.subheader(f"🖼️ {t('detail_plots_gallery')}", anchor=False)
        plot_cols = st.columns(2)
        for i, plot_path in enumerate(plots):
            with plot_cols[i % 2]:
                st.image(plot_path, caption=os.path.basename(plot_path))

# ── Researcher Scientific Review & Peer Validation ────────────────
with st.container(border=True):
    st.subheader(f"📝 {t('detail_review_title')}", anchor=False)

    existing_review = get_review(tic_id, sector, event_id=event_id, start_time=start_time) or {}

    if st.session_state.pop(f"review_just_saved_{tic_id}_{sector}", False):
        st.success(f"✅ {t('detail_saved_success')}", icon="💾")

    class_options = [
        t("class_strong"),
        t("class_possible"),
        t("class_needs_review"),
        t("class_symmetric"),
        t("class_noise"),
        t("class_rejected"),
    ]
    current_class = existing_review.get("classification", class_options[0])
    class_idx = class_options.index(current_class) if current_class in class_options else 0

    rev_col1, rev_col2 = st.columns(2)

    with rev_col1:
        classification_val = st.selectbox(
            t("detail_review_classification"),
            options=class_options,
            index=class_idx,
            key=f"sel_class_{tic_id}_{sector}",
        )

    with rev_col2:
        status_options = [t("review_pending"), t("review_approved"), t("review_rejected")]
        current_status = existing_review.get("status", status_options[0])

        status_val = st.segmented_control(
            t("detail_review_status"),
            options=status_options,
            default=current_status if current_status in status_options else status_options[0],
            key=f"seg_status_{tic_id}_{sector}",
        )

    notes_val = st.text_area(
        t("detail_review_notes"),
        value=existing_review.get("notes", ""),
        placeholder=t("detail_review_notes_placeholder"),
        height=90,
        key=f"txt_notes_{tic_id}_{sector}",
    )

    btn_col1, btn_col2 = st.columns([1.5, 3], vertical_alignment="center")
    with btn_col1:
        if st.button(
            t("detail_save_review"),
            type="primary",
            icon=":material/save:",
            key=f"btn_save_review_{tic_id}_{sector}",
            width="stretch",
        ):
            final_class = classification_val or current_class
            final_status = status_val or current_status
            final_notes = (notes_val or "").strip()

            save_review(tic_id, sector, final_class, final_status, final_notes, event_id=event_id, start_time=start_time)
            st.session_state[f"review_just_saved_{tic_id}_{sector}"] = True
            st.toast(f"✅ {t('detail_saved_success')}", icon="💾")
            st.rerun()

    with btn_col2:
        last_ts = existing_review.get("timestamp")
        if last_ts:
            st.markdown(
                f"""
                <div style="font-size: 0.85rem; color: #34d399; display: flex; align-items: center; gap: 6px;">
                    <span>💾</span>
                    <span>{t('detail_saved_timestamp', ts=last_ts)}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ── Visual Comparison: Comet vs Planet Transit ────────────────────
if is_light:
    comet_bg = "#f0f9ff"
    comet_border = "1px solid #bae6fd"
    comet_title = "#0369a1"
    comet_desc = "#334155"
    comet_inner_bg = "#e0f2fe"
    comet_inner_text = "#075985"

    planet_bg = "#faf5ff"
    planet_border = "1px solid #e9d5ff"
    planet_title = "#7c3aed"
    planet_desc = "#334155"
    planet_inner_bg = "#f3e8ff"
    planet_inner_text = "#581c87"
else:
    comet_bg = "rgba(8,47,73,0.3)"
    comet_border = "1px solid rgba(56,189,248,0.3)"
    comet_title = "#38bdf8"
    comet_desc = "#cbd5e1"
    comet_inner_bg = "rgba(15,23,42,0.6)"
    comet_inner_text = "#94a3b8"

    planet_bg = "rgba(30,27,75,0.3)"
    planet_border = "1px solid rgba(167,139,250,0.3)"
    planet_title = "#a78bfa"
    planet_desc = "#cbd5e1"
    planet_inner_bg = "rgba(15,23,42,0.6)"
    planet_inner_text = "#94a3b8"

with st.container(border=True):
    st.subheader(t("detail_comparison_title"), anchor=False)

    comp_c1, comp_c2 = st.columns(2)

    with comp_c1:
        st.markdown(
            f"""
            <div style="background:{comet_bg};border:{comet_border};border-radius:12px;padding:16px;">
                <div style="font-weight:800;color:{comet_title};font-size:1.05rem;margin-bottom:6px;">
                    ☄️ {t('detail_comet_transit')}
                </div>
                <p style="font-size:0.85rem;color:{comet_desc};line-height:1.5;">
                    {t('detail_comet_desc')}
                </p>
                <div style="font-size:0.78rem;color:{comet_inner_text};background:{comet_inner_bg};padding:8px;border-radius:6px;margin-top:8px;">
                    {t('physics_comet')}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with comp_c2:
        st.markdown(
            f"""
            <div style="background:{planet_bg};border:{planet_border};border-radius:12px;padding:16px;">
                <div style="font-weight:800;color:{planet_title};font-size:1.05rem;margin-bottom:6px;">
                    🪐 {t('detail_planet_transit')}
                </div>
                <p style="font-size:0.85rem;color:{planet_desc};line-height:1.5;">
                    {t('detail_planet_desc')}
                </p>
                <div style="font-size:0.78rem;color:{planet_inner_text};background:{planet_inner_bg};padding:8px;border-radius:6px;margin-top:8px;">
                    {t('physics_planet')}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
