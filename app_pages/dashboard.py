"""
app_pages/dashboard.py — Clean, Dynamic & Interactive Observatory Dashboard for ExoTrace.

Features:
  - Responsive, minimal header with bilingual TESS badge.
  - Interactive Clickable KPI Cards acting as direct filters and navigation triggers.
  - Photorealistic continuous transit simulation.
  - Clear Host Star vs Exocomet Candidate distinction with real plot image.
  - Interactive Candidate Explorer with category filters and pagination.
  - 100% Internationalization (Arabic & English).
"""

import streamlit as st
import pandas as pd
from lib.i18n import t, is_rtl, get_theme, get_lang
from lib.data_loader import (
    compute_dashboard_stats,
    get_all_results,
    load_reanalysis_results,
    load_lightcurve,
    get_candidate_plots,
    classify_display,
    get_review,
    get_comets_table,
    get_dips_table,
    get_review_table,
)
from lib.scan_history import get_scanned_stars_table, get_scan_history, get_star_name
from components.transit_scene import render_transit_scene

is_en = (get_lang() == "en")
is_light = (get_theme() == "light")

# ── 1. Minimal Header ───────────────────────────────
tess_badge_bg = "#e0f2fe" if is_light else "rgba(56,189,248,0.12)"
tess_badge_color = "#0369a1" if is_light else "#38bdf8"
tess_badge_border = "1px solid #bae6fd" if is_light else "1px solid rgba(56,189,248,0.25)"

st.markdown(
    f"""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
        <h2 style="margin:0;font-weight:800;font-size:1.5rem;letter-spacing:-0.5px;">
            {t('dashboard_title')}
        </h2>
        <span style="background:{tess_badge_bg};color:{tess_badge_color};padding:3px 10px;border-radius:12px;font-size:0.75rem;font-weight:700;border:{tess_badge_border};">
            🛰️ TESS LIVE
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── 2. Interactive Clickable KPI Action Cards ─────────────────────────
reanalysis = load_reanalysis_results()
has_data = not reanalysis.empty

focused_tic = st.session_state.get("dashboard_focused_tic") or st.session_state.get("just_analyzed_tic")
if focused_tic:
    focused_tic = str(focused_tic).replace("TIC", "").strip()

# Focused target alert banner right below header
if focused_tic:
    friendly_name = get_star_name(str(focused_tic), lang="en" if is_en else "ar")
    name_clean = friendly_name.split("(")[0].strip() if "(" in friendly_name else friendly_name

    # Retrieve scan date from persistent history
    scan_date = "—"
    for rec in get_scan_history():
        if str(rec.get("tic_id", "")).strip() == str(focused_tic).strip():
            scan_date = rec.get("timestamp", "—")
            break

    f_b_col1, f_b_col2 = st.columns([3.8, 1.2], vertical_alignment="center")
    with f_b_col1:
        if is_en:
            msg = f"📌 **Notice:** Loaded scan results for target **TIC {focused_tic}** ({name_clean}) executed on: `{scan_date}`"
        else:
            msg = f"📌 **ملاحظة:** تم استدعاء فحص النجم **TIC {focused_tic}** ({name_clean}) المنفّذ بتاريخ: `{scan_date}`"
        st.info(msg, icon="🔭")
    with f_b_col2:
        btn_label = "✕ Clear target filter" if is_en else "✕ إغلاق نتيجة الفحص"
        btn_help = "Reset target filter and return to full observatory overview" if is_en else "إلغاء تصفية هذا الفحص والعودة لعرض كافة بيانات المرصد"
        if st.button(btn_label, help=btn_help, width="stretch"):
            st.session_state.pop("dashboard_focused_tic", None)
            st.session_state.pop("just_analyzed_tic", None)
            st.session_state.spotlight_index = 0
            st.rerun()

spotlight_cands = pd.DataFrame()
if has_data and "A" in reanalysis.columns:
    if focused_tic:
        clean_reanalysis_tics = reanalysis["tic_id"].astype(str).str.replace(".0", "", regex=False)
        star_matches = reanalysis[clean_reanalysis_tics == str(focused_tic)]
        if not star_matches.empty:
            def sort_priority(row):
                cat = row.get("category_code", "")
                if cat == "strong":
                    return 0
                if row.get("dip_found_bool", False):
                    return 1
                return 2
            star_matches = star_matches.copy()
            star_matches["_prio"] = star_matches.apply(sort_priority, axis=1)
            spotlight_cands = star_matches.sort_values(["_prio", "A"], ascending=[True, False]).reset_index(drop=True)
            spotlight_cands.drop(columns=["_prio"], inplace=True)
        else:
            strong_df = reanalysis[reanalysis["category_code"] == "strong"]
            spotlight_cands = strong_df.sort_values("A", ascending=False).reset_index(drop=True) if not strong_df.empty else reanalysis.reset_index(drop=True)
    else:
        strong_df = reanalysis[reanalysis["category_code"] == "strong"]
        if not strong_df.empty:
            spotlight_cands = strong_df.sort_values("A", ascending=False).reset_index(drop=True)
        else:
            dips_df = reanalysis[reanalysis.get("dip_found_bool", False) == True]
            if not dips_df.empty:
                spotlight_cands = dips_df.sort_values("A", ascending=False).reset_index(drop=True)
            else:
                spotlight_cands = reanalysis.reset_index(drop=True)

num_comets = len(spotlight_cands)

if "spotlight_index" not in st.session_state:
    st.session_state.spotlight_index = 0

top_cand = None
if num_comets > 0:
    st.session_state.spotlight_index = max(0, min(st.session_state.spotlight_index, num_comets - 1))
    top_cand = spotlight_cands.iloc[st.session_state.spotlight_index]


@st.dialog(t("dialog_stars_title"), width="large")
def show_scanned_stars_dialog():
    st.caption(t("dialog_stars_caption"))
    df_stars = get_scanned_stars_table()
    if df_stars.empty:
        st.info(t("dialog_stars_empty"))
    else:
        st.dataframe(
            df_stars,
            width="stretch",
            hide_index=True,
        )


@st.dialog(t("dialog_dips_title"), width="large")
def show_dips_dialog():
    st.caption(t("dialog_dips_caption"))
    df_dips = get_dips_table()
    if df_dips.empty:
        st.info(t("dialog_dips_empty"))
    else:
        st.dataframe(
            df_dips,
            width="stretch",
            hide_index=True,
        )


@st.dialog(t("dialog_comets_title"), width="large")
def show_comets_dialog():
    st.caption(t("dialog_comets_caption"))
    df_comets = get_comets_table()
    if df_comets.empty:
        st.info(t("dialog_comets_empty"))
    else:
        st.dataframe(
            df_comets,
            width="stretch",
            hide_index=True,
        )


@st.dialog(t("dialog_review_title"), width="large")
def show_review_dialog():
    st.caption(t("dialog_review_caption"))
    df_rev = get_review_table()
    if df_rev.empty:
        st.info(t("dialog_review_empty"))
    else:
        st.dataframe(
            df_rev,
            width="stretch",
            hide_index=True,
        )


stats = compute_dashboard_stats()
kpi_cols = st.columns(4)

stars_count = stats.get("stars_analyzed", 0)
stars_label = f"{stars_count} {t('kpi_unit_star_singular')}" if stars_count == 1 else f"{stars_count} {t('kpi_unit_star_plural')}"
dips_count = stats.get("dips_detected", 0)
dips_label = f"{dips_count} {t('kpi_unit_dip_singular')}" if dips_count == 1 else f"{dips_count} {t('kpi_unit_dip_plural')}"
strong_count = stats.get("strong_candidates", 0)
strong_label = f"{strong_count} {t('kpi_unit_comet_singular')}" if strong_count == 1 else f"{strong_count} {t('kpi_unit_comet_plural')}"
review_count = stats.get("needs_review", 0)
review_label = f"{review_count} {t('kpi_unit_review')}"

with kpi_cols[0]:
    if st.button(f"⭐ {t('kpi_scanned_stars')}\n\n**{stars_label}**", key="kpi_btn_star", width="stretch", help="View surveyed stars"):
        show_scanned_stars_dialog()

with kpi_cols[1]:
    if st.button(f"📉 {t('kpi_flux_dips')}\n\n**{dips_label}**", key="kpi_btn_dips", width="stretch", help="View detected flux dips"):
        show_dips_dialog()

with kpi_cols[2]:
    if st.button(f"☄️ {t('kpi_strong_candidates')}\n\n**{strong_label}**", key="kpi_btn_strong", width="stretch", help="View comet candidates"):
        show_comets_dialog()

with kpi_cols[3]:
    if st.button(f"🔬 {t('kpi_pending_review')}\n\n**{review_label}**", key="kpi_btn_review", width="stretch", help="View pending review targets"):
        show_review_dialog()

# Active target status banner
if top_cand is not None:
    active_tic = str(int(top_cand["tic_id"]))
    active_sector = int(top_cand.get("sector", 7))
    star_name = get_star_name(active_tic, lang="en" if is_en else "ar")

    banner_bg = "#ffffff" if is_light else "rgba(15,23,42,0.65)"
    banner_border = "1px solid #cbd5e1" if is_light else "1px solid rgba(56,189,248,0.25)"
    banner_shadow = "box-shadow: 0 2px 10px rgba(0,0,0,0.04);" if is_light else ""
    label_color = "#475569" if is_light else "#94a3b8"
    tic_color = "#0284c7" if is_light else "#38bdf8"
    star_color = "#0f172a" if is_light else "#cbd5e1"
    dot_color = "#94a3b8" if is_light else "#64748b"
    pill_sec_bg = "#e0f2fe" if is_light else "rgba(56,189,248,0.12)"
    pill_sec_color = "#0369a1" if is_light else "#38bdf8"
    pill_sec_border = "border: 1px solid #bae6fd;" if is_light else ""
    pill_done_bg = "#dcfce7" if is_light else "rgba(16,185,129,0.15)"
    pill_done_color = "#15803d" if is_light else "#10b981"
    pill_done_border = "border: 1px solid #bbf7d0;" if is_light else ""

    sector_str = f"Sector {active_sector}" if is_en else f"قطاع {active_sector}"

    st.markdown(
        f"""
        <div style="background: {banner_bg}; border: {banner_border}; {banner_shadow} border-radius: 10px; padding: 10px 16px; margin: 12px 0 16px 0; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.25rem;">🔭</span>
                <span style="color: {label_color}; font-size: 0.88rem; font-weight: 600;">{t('active_target_label')}</span>
                <span style="color: {tic_color}; font-weight: 800; font-size: 1.05rem;">TIC {active_tic}</span>
                <span style="color: {dot_color};">•</span>
                <span style="color: {star_color}; font-size: 0.88rem; font-weight: 600;">{star_name}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="background: {pill_sec_bg}; color: {pill_sec_color}; {pill_sec_border} padding: 3px 10px; border-radius: 6px; font-size: 0.78rem; font-weight: 700;">
                    {sector_str}
                </span>
                <span style="background: {pill_done_bg}; color: {pill_done_color}; {pill_done_border} padding: 3px 10px; border-radius: 6px; font-size: 0.78rem; font-weight: 700;">
                    {t('scan_completed_badge')}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── 3. Continuous Simulation Section ───────────────────────────────
render_transit_scene(key="dashboard_continuous_sim")


# ── 4. Spotlight on Top Candidate ──────────────────────────────────────
st.markdown("---")

spot_col1, spot_col2 = st.columns([2, 1])

with spot_col1:
    with st.container(border=True):
        if top_cand is not None:
            tic_id = int(top_cand["tic_id"])
            sector = int(top_cand["sector"])

            # Clean header distinguishing Host Star vs Comet
            host_sub_col = "#0284c7" if is_light else "#38bdf8"
            host_title_col = "#0f172a" if is_light else "#f8fafc"
            cand_badge_bg = "#fee2e2" if is_light else "rgba(239,68,68,0.15)"
            cand_badge_col = "#b91c1c" if is_light else "#f87171"
            cand_badge_border = "1px solid #fca5a5" if is_light else "1px solid rgba(239,68,68,0.4)"

            cand_tag = f"{t('sector_label')} {sector}"
            counter_tag = f" • {st.session_state.spotlight_index + 1}/{num_comets}" if num_comets > 1 else ""

            st.markdown(
                f"""
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <div style="display:flex;align-items:center;gap:8px;">
                        <span style="font-size:1.4rem;">⭐</span>
                        <div>
                            <span style="font-size:0.75rem;color:{host_sub_col};font-weight:700;">{t('host_star_label')}</span>
                            <div style="font-size:1.3rem;font-weight:900;line-height:1.1;color:{host_title_col};">TIC {tic_id}</div>
                        </div>
                    </div>
                    <span style="background:{cand_badge_bg};color:{cand_badge_col};border:{cand_badge_border};padding:3px 10px;border-radius:12px;font-size:0.78rem;font-weight:700;">
                        ☄️ {t('transiting_comet_badge')} ({cand_tag}){counter_tag}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Display real plot image
            plots = get_candidate_plots(tic_id, sector)
            if plots:
                try:
                    from PIL import Image
                    img = Image.open(plots[0])
                    w, h = img.size
                    crop_h = min(h, 450)
                    cropped = img.crop((0, 0, w, crop_h))
                    st.image(cropped, width="stretch", caption=t("spotlight_plot_preview_caption"))
                except Exception:
                    st.image(plots[0], width="stretch")

                @st.dialog(t("spotlight_dialog_plot_title"), width="large")
                def show_full_plot_dialog(img_path):
                    st.image(img_path, width="stretch")

                if st.button(f"🔍 {t('spotlight_view_full_plot')}", width="stretch"):
                    show_full_plot_dialog(plots[0])
            else:
                lc_data = load_lightcurve(tic_id, sector, flat=True)
                if not lc_data.empty and "flux_flat" in lc_data.columns:
                    import matplotlib.pyplot as plt
                    import tempfile
                    
                    fig, ax = plt.subplots(figsize=(10, 4))
                    ax.plot(lc_data["time"], lc_data["flux_flat"], "k.", ms=1.5, alpha=0.5, label="Detrended Flux")
                    ax.axhline(1.0, color="gray", ls="--", lw=1)
                    
                    s_t = top_cand.get("start_time")
                    e_t = top_cand.get("end_time")
                    import pandas as pd
                    if pd.notna(s_t) and pd.notna(e_t):
                        ax.axvspan(s_t, e_t, color="red", alpha=0.25, label="Detected Dip")
                        
                    ax.set_title(f"TIC {tic_id} — Sector {sector} (Detrended)", fontsize=12)
                    ax.set_xlabel("Time (BJD)", fontsize=10)
                    ax.set_ylabel("Normalized Flux", fontsize=10)
                    ax.legend(loc="upper right", fontsize=9)
                    fig.tight_layout()
                    
                    tmp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
                    fig.savefig(tmp_img, dpi=150, bbox_inches="tight", facecolor="white")
                    plt.close(fig)
                    
                    cap_str = f"Photometric Cadence for TIC {tic_id}" if is_en else f"المنحنى الضوئي للنجم TIC {tic_id}"
                    st.image(tmp_img, width="stretch", caption=cap_str)
                else:
                    st.info(t("no_data"))

            # Bottom badge bar
            bot_bg = "#f8fafc" if is_light else "rgba(15,23,42,0.6)"
            bot_border = "border: 1px solid #e2e8f0;" if is_light else ""
            asym_col = "#b45309" if is_light else "#fbbf24"
            cand_cls_text = top_cand["classification_en"] if is_en else top_cand["classification_ar"]

            st.markdown(
                f"""
                <div style="display:flex;align-items:center;justify-content:space-between;background:{bot_bg};{bot_border}padding:8px 12px;border-radius:8px;margin-top:6px;">
                    <span style="font-weight:700;color:{top_cand['badge_color']};">
                        {cand_cls_text}
                    </span>
                    <span style="font-family:monospace;color:{asym_col};font-weight:800;">
                        {t('metric_asymmetry')}: {top_cand['asym_display']}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.subheader(t("lightcurve_title"), anchor=False)
            st.info(t("no_data"))

with spot_col2:
    with st.container(border=True):
        st.subheader(f"🔍 {t('spotlight_signal_details')}", anchor=False)
        if top_cand is not None:
            if num_comets > 1:
                nav_prev, nav_count, nav_next = st.columns([1, 1.4, 1], vertical_alignment="center")
                with nav_prev:
                    if st.button(f"◀ {t('spotlight_prev')}", key="spot_prev_btn", width="stretch", disabled=(st.session_state.spotlight_index == 0)):
                        st.session_state.spotlight_index -= 1
                        st.rerun()
                with nav_count:
                    counter_bg = "#e0f2fe" if is_light else "rgba(56,189,248,0.1)"
                    counter_color = "#0369a1" if is_light else "#38bdf8"
                    counter_border = "1px solid #bae6fd" if is_light else "1px solid rgba(56,189,248,0.25)"
                    st.markdown(
                        f"""
                        <div style="text-align:center;font-weight:800;font-size:0.85rem;color:{counter_color};background:{counter_bg};padding:5px 0;border-radius:6px;border:{counter_border};">
                            {st.session_state.spotlight_index + 1} {t('spotlight_of')} {num_comets}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with nav_next:
                    if st.button(f"{t('spotlight_next')} ▶", key="spot_next_btn", width="stretch", disabled=(st.session_state.spotlight_index >= num_comets - 1)):
                        st.session_state.spotlight_index += 1
                        st.rerun()

            egress_val = top_cand.get("egress_display_en" if is_en else "egress_display_ar", top_cand["egress_display"])
            st.metric(t("metric_dip_depth"), top_cand["depth_display"])
            st.metric(t("metric_egress_time"), egress_val)
            st.metric(t("metric_asymmetry"), top_cand["asym_display"])
            st.metric(t("col_source"), t("spotlight_source_val"))

            if st.button(
                f"🔬 {t('spotlight_inspect_btn')}",
                key="spotlight_inspect_btn",
                type="primary",
            ):
                st.session_state.selected_candidate = top_cand.to_dict()
                st.switch_page("app_pages/candidate_detail.py")
        else:
            st.info(t("no_data"))

# ── 5. Interactive Candidate Explorer (Linked to KPI Cards) ──────────
st.markdown("---")

with st.container(border=True):
    st.subheader(f"✨ {t('latest_signals_title')}", anchor=False)

    all_results = get_all_results()

    if not all_results.empty:
        filter_col1, filter_col2, _ = st.columns([2, 1.5, 4.5], vertical_alignment="center")

        CATEGORY_MAP = {
            "all": "all",
            "strong": "strong",
            "symmetric": "symmetric",
            "reverse": "reverse",
            "no_dip": "no_dip",
            "جميع الإشارات الرصدية": "all",
            "مرشحات مذنبات خارجية (لاتماثل قوي)": "strong",
            "انخفاضات متماثلة (كواكب / كاذبة)": "symmetric",
            "لاتماثل معكوس": "reverse",
            "لا يوجد انخفاض (ضجيج / هادئ)": "no_dip",
            "All Signals": "all",
            "Exocomet Candidates (Strong Asymmetry)": "strong",
            "Symmetric Dips (Exoplanets / False Positives)": "symmetric",
            "Reverse Asymmetry": "reverse",
            "No Dip Found (Noise / Quiescent)": "no_dip",
        }

        VIEW_MAP = {
            "cards": "cards",
            "table": "table",
            "عرض البطاقات الذكية": "cards",
            "عرض الجدول الرصدي": "table",
            "Smart Cards": "cards",
            "Observational Table": "table",
        }

        raw_filter = st.session_state.get("signals_active_filter", "all")
        active_cat = CATEGORY_MAP.get(raw_filter, "all")

        raw_view = st.session_state.get("signals_view_mode", "cards")
        active_view = VIEW_MAP.get(raw_view, "cards")

        cat_codes = ["all", "strong", "symmetric", "reverse", "no_dip"]
        cat_labels = {
            "all": t("filter_all"),
            "strong": t("filter_strong"),
            "symmetric": t("filter_symmetric"),
            "reverse": t("filter_reverse"),
            "no_dip": t("filter_no_dip"),
        }
        cat_idx = cat_codes.index(active_cat) if active_cat in cat_codes else 0

        with filter_col1:
            category_filter = st.selectbox(
                t("cand_filter_cat_label"),
                options=cat_codes,
                index=cat_idx,
                format_func=lambda c: cat_labels.get(c, c),
                key=f"signals_category_selectbox_{'en' if is_en else 'ar'}",
                label_visibility="collapsed",
            )

        view_codes = ["cards", "table"]
        view_labels = {
            "cards": t("view_mode_cards"),
            "table": t("view_mode_table"),
        }
        view_idx = view_codes.index(active_view) if active_view in view_codes else 0

        with filter_col2:
            view_mode = st.selectbox(
                "View Mode",
                options=view_codes,
                index=view_idx,
                format_func=lambda v: view_labels.get(v, v),
                key=f"signals_view_mode_selectbox_{'en' if is_en else 'ar'}",
                label_visibility="collapsed",
            )

        st.session_state["signals_active_filter"] = category_filter
        st.session_state["signals_view_mode"] = view_mode

        # Reset pagination on filter change
        if "prev_cat" not in st.session_state or st.session_state.prev_cat != category_filter or st.session_state.prev_view != view_mode:
            st.session_state.prev_cat = category_filter
            st.session_state.prev_view = view_mode
            st.session_state.visible_items_count = 6

        filtered_results = all_results.copy()
        if focused_tic:
            target_matches = filtered_results[filtered_results["tic_id"].astype(str) == str(focused_tic)]
            if not target_matches.empty:
                filtered_results = target_matches

        if category_filter == "strong":
            filtered_results = filtered_results[filtered_results["category_code"] == "strong"]
        elif category_filter == "symmetric":
            filtered_results = filtered_results[filtered_results["category_code"] == "symmetric"]
        elif category_filter == "reverse":
            filtered_results = filtered_results[filtered_results["category_code"] == "reverse"]
        elif category_filter == "no_dip":
            filtered_results = filtered_results[filtered_results["category_code"] == "no_dip"]

        if view_mode == "cards":
            if filtered_results.empty:
                st.info(t("cand_no_matching"))
            else:
                visible_count = st.session_state.visible_items_count
                items_to_show = filtered_results.head(visible_count)

                def render_cand_card(idx, row):
                    tic = int(row.get("tic_id", 0))
                    sector = int(row.get("sector", 0))
                    cls_text = row.get("classification_en" if is_en else "classification_ar", row.get("classification_ar", ""))
                    badge_color = row.get("badge_color", "#64748b")
                    asym = row.get("asym_display", "")
                    depth = row.get("depth_display", "")
                    egress = row.get("egress_display_en" if is_en else "egress_display_ar", row.get("egress_display", ""))
                    is_comet = row.get("category_code") == "strong"
                    card_tic_col = "#0f172a" if is_light else "#f8fafc"
                    card_sub_col = "#475569" if is_light else "#94a3b8"
                    card_asym_col = "#b45309" if is_light else "#fbbf24"
                    card_depth_col = "#0f172a" if is_light else "#f8fafc"
                    
                    sec_label = f"Sector {sector}" if is_en else f"قطاع {sector}"
                    depth_label = "Depth:" if is_en else "العمق:"
                    egress_label = "Egress:" if is_en else "الخروج:"
                    asym_label = "Asymmetry:" if is_en else "اللاتماثل:"
                    inspect_label = "🔬 Review Signal" if is_en else "🔍 فحص الإشارة"

                    with st.container(border=True):
                        c_col1, c_col2, c_col3, c_col4 = st.columns([2.2, 2.5, 2.5, 1.8], vertical_alignment="center")

                        with c_col1:
                            st.markdown(
                                f"""
                                <div style="display:flex;align-items:center;gap:10px;">
                                    <span style="font-size:1.5rem;">{'☄️' if is_comet else ('⚠️' if row.get('category_code')=='reverse' else ('🪐' if row.get('category_code')=='symmetric' else '⭐'))}</span>
                                    <div>
                                        <div style="font-weight:800;font-size:1.05rem;color:{card_tic_col};">TIC {tic}</div>
                                        <div style="font-size:0.75rem;color:{card_sub_col};">{sec_label}</div>
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                        with c_col2:
                            st.markdown(
                                f"""
                                <span style="background:{badge_color}22;color:{badge_color};border:1px solid {badge_color}55;padding:3px 10px;border-radius:10px;font-size:0.75rem;font-weight:700;">
                                    {cls_text}
                                </span>
                                <div style="font-size:0.75rem;color:{card_sub_col};margin-top:4px;">
                                    {depth_label} <b style="color:{card_depth_col};">{depth}</b>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                        with c_col3:
                            st.markdown(
                                f"""
                                <div style="font-size:0.75rem;color:{card_sub_col};">{egress_label} <b style="color:{card_depth_col};">{egress}</b></div>
                                <div style="font-size:0.8rem;color:{card_asym_col};font-weight:700;">{asym_label} {asym}</div>
                                """,
                                unsafe_allow_html=True,
                            )

                        with c_col4:
                            if st.button(
                                inspect_label,
                                key=f"inspect_btn_{idx}_{tic}_{sector}",
                                type="primary" if is_comet else "secondary",
                            ):
                                st.session_state.selected_candidate = row.to_dict()
                                st.switch_page("app_pages/candidate_detail.py")

                for idx, row in items_to_show.iterrows():
                    render_cand_card(idx, row)

                total_cards = len(filtered_results)
                if total_cards > 6:
                    cur_visible = min(visible_count, total_cards)
                    remaining_expand = max(0, total_cards - cur_visible)
                    remaining_collapse = max(0, cur_visible - 6)

                    col_more, col_less = st.columns(2)
                    with col_more:
                        if is_en:
                            btn_more_label = f"Load More ({remaining_expand} remaining) ↓" if remaining_expand > 0 else "All Signals Loaded ↓"
                        else:
                            btn_more_label = f"عرض المزيد (متبقي {remaining_expand}) ↓" if remaining_expand > 0 else "عرض المزيد (مكتمل) ↓"
                        if st.button(btn_more_label, width="stretch", key="expand_cards", disabled=(remaining_expand == 0)):
                            st.session_state.visible_items_count = min(cur_visible + 6, total_cards)
                            st.rerun()

                    with col_less:
                        if is_en:
                            btn_less_label = f"Show Less ({remaining_collapse} collapsible) ↑" if remaining_collapse > 0 else "Show Less ↑"
                        else:
                            btn_less_label = f"عرض أقل (متبقي {remaining_collapse}) ↑" if remaining_collapse > 0 else "عرض أقل ↑"
                        if st.button(btn_less_label, width="stretch", key="collapse_cards", disabled=(remaining_collapse == 0)):
                            st.session_state.visible_items_count = max(6, cur_visible - 6)
                            st.rerun()
        else:
            dip_col_name = "dip_found_en" if is_en else "dip_found_ar"
            cls_col_name = "classification_en" if is_en else "classification_ar"
            ing_col_name = "ingress_display_en" if is_en else "ingress_display_ar"
            egr_col_name = "egress_display_en" if is_en else "egress_display_ar"

            table_display_df = filtered_results[[
                "tic_id", "sector", dip_col_name, "depth_display",
                ing_col_name, egr_col_name, "asym_display", cls_col_name
            ]].copy()

            table_display_df.columns = [
                t("col_tic_id"),
                t("col_sector"),
                t("col_dip_found"),
                t("col_depth"),
                t("col_ingress"),
                t("col_egress"),
                t("col_asymmetry"),
                t("col_classification"),
            ]

            visible_count = st.session_state.visible_items_count
            items_to_show = table_display_df.head(visible_count)

            event = st.dataframe(
                items_to_show,
                hide_index=True,
                selection_mode="single-row",
                on_select="rerun",
                key="clean_dashboard_table",
            )

            if event.selection and event.selection.rows:
                sel_row_idx = event.selection.rows[0]
                st.session_state.selected_candidate = filtered_results.iloc[sel_row_idx].to_dict()
                st.switch_page("app_pages/candidate_detail.py")

            total_table_rows = len(table_display_df)
            if total_table_rows > 6:
                cur_visible = min(visible_count, total_table_rows)
                remaining_expand = max(0, total_table_rows - cur_visible)
                remaining_collapse = max(0, cur_visible - 6)

                col_t_more, col_t_less = st.columns(2)
                with col_t_more:
                    if is_en:
                        btn_more_label = f"Load More ({remaining_expand} remaining) ↓" if remaining_expand > 0 else "All Rows Loaded ↓"
                    else:
                        btn_more_label = f"عرض المزيد (متبقي {remaining_expand}) ↓" if remaining_expand > 0 else "عرض المزيد (مكتمل) ↓"
                    if st.button(btn_more_label, width="stretch", key="expand_table", disabled=(remaining_expand == 0)):
                        st.session_state.visible_items_count = min(cur_visible + 6, total_table_rows)
                        st.rerun()

                with col_t_less:
                    if is_en:
                        btn_less_label = f"Show Less ({remaining_collapse} collapsible) ↑" if remaining_collapse > 0 else "Show Less ↑"
                    else:
                        btn_less_label = f"عرض أقل (متبقي {remaining_collapse}) ↑" if remaining_collapse > 0 else "عرض أقل ↑"
                    if st.button(btn_less_label, width="stretch", key="collapse_table", disabled=(remaining_collapse == 0)):
                        st.session_state.visible_items_count = max(6, cur_visible - 6)
                        st.rerun()
    else:
        st.info(t("no_data"))
