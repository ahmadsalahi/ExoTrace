"""
app_pages/candidates.py — Interactive Candidate Registry for ExoTrace.

Features:
  - Interactive Filter Bar (Search by TIC ID, filter by category, sector, sort order).
  - Dual View Modes:
      1. Smart Visual Cards with glowing badges, asymmetry comparison bars, and quick actions.
      2. Clean Scientific Table with full localization and zero 'None' leaks.
  - Seamless navigation to candidate detail upon selection.
  - 100% Internationalization (Arabic & English).
"""

import streamlit as st
import pandas as pd
from lib.i18n import t, get_theme, get_lang
from lib.data_loader import get_all_results

is_en = (get_lang() == "en")
is_light = (get_theme() == "light")

df = get_all_results()

if df is None or df.empty:
    st.info(t("no_candidates"))
else:
    # ── Search & Filter Controls ───────────────────────────────────
    with st.container(border=True):
        f_col1, f_col2, f_col3, f_col4 = st.columns([2.5, 2.5, 2, 2])

        with f_col1:
            prefill_tic = str(st.session_state.pop("filter_tic", "") or "")
            search_tic = st.text_input(
                t("btn_search"),
                value=prefill_tic,
                label_visibility="collapsed",
                placeholder=t("cand_search_placeholder"),
            )

        with f_col2:
            category_options = [
                t("cand_filter_all"),
                t("cand_filter_strong"),
                t("cand_filter_symmetric"),
                t("cand_filter_reverse"),
                t("cand_filter_nodip"),
            ]
            filter_cat = st.selectbox(
                t("cand_filter_cat_label"),
                options=category_options,
                label_visibility="collapsed",
            )

        with f_col3:
            sectors = sorted(df["sector"].dropna().unique().astype(int).tolist()) if "sector" in df.columns else []
            filter_sector = st.multiselect(
                t("col_sector"),
                options=sectors,
                placeholder=t("cand_sector_placeholder"),
                label_visibility="collapsed",
            )

        with f_col4:
            sort_by = st.selectbox(
                t("sort_by"),
                options=[t("sort_asymmetry"), t("sort_depth")],
                label_visibility="collapsed",
            )

    # Apply Filters
    filtered_df = df.copy()

    if search_tic:
        filtered_df = filtered_df[filtered_df["tic_id"].astype(str).str.contains(search_tic.strip(), case=False, na=False)]

    if filter_cat == t("cand_filter_strong"):
        filtered_df = filtered_df[filtered_df["category_code"] == "strong"]
    elif filter_cat == t("cand_filter_symmetric"):
        filtered_df = filtered_df[filtered_df["category_code"] == "symmetric"]
    elif filter_cat == t("cand_filter_reverse"):
        filtered_df = filtered_df[filtered_df["category_code"] == "reverse"]
    elif filter_cat == t("cand_filter_nodip"):
        filtered_df = filtered_df[filtered_df["category_code"] == "no_dip"]

    if filter_sector:
        filtered_df = filtered_df[filtered_df["sector"].isin(filter_sector)]

    # Sorting
    if sort_by == t("sort_asymmetry") and "A" in filtered_df.columns:
        filtered_df = filtered_df.sort_values("A", ascending=False)
    elif sort_by == t("sort_depth") and "depth" in filtered_df.columns:
        filtered_df = filtered_df.sort_values("depth", ascending=False)

    # ── View Mode Switcher ─────────────────────────────────────────
    seg_bg = "#ffffff" if is_light else "rgba(15, 23, 42, 0.85)"
    seg_border = "1px solid #cbd5e1" if is_light else "1px solid rgba(56, 189, 248, 0.3)"
    seg_color = "#1e293b" if is_light else "#cbd5e1"
    seg_inactive_color = "#64748b" if is_light else "#94a3b8"
    seg_hover_color = "#0284c7" if is_light else "#ffffff"
    seg_hover_bg = "#f1f5f9" if is_light else "rgba(56, 189, 248, 0.15)"

    st.markdown(
        f"""
        <style>
        div[data-testid="stSegmentedControl"] {{
            background: {seg_bg} !important;
            border: {seg_border} !important;
            border-radius: 10px !important;
            padding: 3px !important;
            width: 100% !important;
        }}
        div[data-testid="stSegmentedControl"] button {{
            border-radius: 8px !important;
            font-weight: 700 !important;
            font-size: 0.88rem !important;
            padding: 6px 14px !important;
            color: {seg_color} !important;
            transition: all 0.2s ease !important;
        }}
        div[data-testid="stSegmentedControl"] button[aria-checked="true"] {{
            background: #0284c7 !important;
            color: #ffffff !important;
            font-weight: 800 !important;
            box-shadow: 0 0 12px rgba(2, 132, 199, 0.45) !important;
        }}
        div[data-testid="stSegmentedControl"] button[aria-checked="false"] {{
            color: {seg_inactive_color} !important;
            background: transparent !important;
        }}
        div[data-testid="stSegmentedControl"] button:hover {{
            color: {seg_hover_color} !important;
            background: {seg_hover_bg} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    count_bg = "#e0f2fe" if is_light else "rgba(56,189,248,0.12)"
    count_color = "#0369a1" if is_light else "#38bdf8"
    count_border = "1px solid #bae6fd" if is_light else "1px solid rgba(56,189,248,0.25)"
    count_label_color = "#334155" if is_light else "#cbd5e1"

    found_msg = (
        f'Found <strong style="color:{count_color};font-size:1.15rem;font-family:monospace;background:{count_bg};padding:2px 8px;border-radius:6px;border:{count_border};">{len(filtered_df)}</strong> matching photometric signals'
        if is_en
        else f'تم العثور على <strong style="color:{count_color};font-size:1.15rem;font-family:monospace;background:{count_bg};padding:2px 8px;border-radius:6px;border:{count_border};">{len(filtered_df)}</strong> إشارة رصدية مطابقة'
    )

    view_col1, view_col2 = st.columns([2.4, 1.4], vertical_alignment="center")
    with view_col1:
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:8px;font-size:0.95rem;font-weight:600;color:{count_label_color};padding:6px 0;">
                <span style="font-size:1.15rem;">🔭</span>
                <span>{found_msg}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with view_col2:
        cand_view_keys = ["cards", "table"]
        cand_view_labels = {
            "cards": t("cand_view_mode_cards"),
            "table": t("cand_view_mode_table"),
        }
        cand_view_mode = st.segmented_control(
            "View Mode",
            options=cand_view_keys,
            default="cards",
            format_func=lambda k: cand_view_labels.get(k, k),
            key=f"candidates_view_mode_toggle_{'en' if is_en else 'ar'}",
            label_visibility="collapsed",
        )

    # ── View 1: Visual Candidate Cards ─────────────────────────────
    if cand_view_mode == "cards" or cand_view_mode == t("cand_view_mode_cards"):
        if filtered_df.empty:
            st.info(t("cand_no_matching"))
        else:
            card_tic_col = "#0f172a" if is_light else "#f8fafc"
            card_sub_col = "#475569" if is_light else "#94a3b8"
            card_depth_col = "#b45309" if is_light else "#fbbf24"
            card_ingress_col = "#0369a1" if is_light else "#38bdf8"
            card_asym_col = "#dc2626" if is_light else "#f87171"

            for idx, row in filtered_df.iterrows():
                tic = int(row.get("tic_id", 0))
                sector = int(row.get("sector", 0))
                cls_text = row.get("classification_en" if is_en else "classification_ar", "—")
                badge_color = row.get("badge_color", "#64748b")
                asym = row.get("asym_display", "—")
                depth = row.get("depth_display", "—")
                ingress = row.get("ingress_display_en" if is_en else "ingress_display_ar", row.get("ingress_display", "—"))
                egress = row.get("egress_display_en" if is_en else "egress_display_ar", row.get("egress_display", "—"))
                duration = row.get("duration_display_en" if is_en else "duration_display_ar", row.get("duration_display", "—"))
                is_comet = row.get("category_code") == "strong"

                depth_title = "Dip Depth:" if is_en else "عمق انخفاض السطوع:"
                ing_lbl = "Ingress:" if is_en else "الدخول:"
                egr_lbl = "Egress:" if is_en else "الخروج:"

                with st.container(border=True):
                    card_c1, card_c2, card_c3, card_c4 = st.columns([2.2, 2.5, 2.5, 1.8], vertical_alignment="center")

                    with card_c1:
                        st.markdown(
                            f"""
                            <div style="display:flex;align-items:center;gap:12px;">
                                <span style="font-size:1.8rem;">{'☄️' if is_comet else ('⚠️' if row.get('category_code')=='reverse' else ('🪐' if row.get('category_code')=='symmetric' else '⭐'))}</span>
                                <div>
                                    <div style="font-weight:900;font-size:1.2rem;color:{card_tic_col};">
                                        TIC {tic}
                                    </div>
                                    <div style="font-size:0.75rem;color:{card_sub_col};">
                                        {t('sector_label')} {sector} · {t('cand_transit_duration')} {duration}
                                    </div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    with card_c2:
                        st.markdown(
                            f"""
                            <div>
                                <span style="background:{badge_color}22;color:{badge_color};border:1px solid {badge_color}55;padding:4px 12px;border-radius:12px;font-size:0.78rem;font-weight:700;">
                                    {cls_text}
                                </span>
                                <div style="font-size:0.78rem;color:{card_sub_col};margin-top:6px;">
                                    {depth_title} <b style="color:{card_depth_col};">{depth}</b>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    with card_c3:
                        st.markdown(
                            f"""
                            <div style="font-size:0.78rem;line-height:1.4;">
                                <div style="color:{card_ingress_col};">
                                    {ing_lbl} <b>{ingress}</b> | {egr_lbl} <b>{egress}</b>
                                </div>
                                <div style="color:{card_asym_col};font-weight:700;margin-top:4px;">
                                    {t('metric_asymmetry')}: {asym}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    with card_c4:
                        if st.button(
                            t("cand_inspect_btn"),
                            key=f"cand_inspect_{idx}_{tic}_{sector}",
                            type="primary" if is_comet else "secondary",
                        ):
                            st.session_state.selected_candidate = row.to_dict()
                            st.switch_page("app_pages/candidate_detail.py")

    # ── View 2: Clean Localized Table ──────────────────────────────
    else:
        dip_col_name = "dip_found_en" if is_en else "dip_found_ar"
        cls_col_name = "classification_en" if is_en else "classification_ar"
        ing_col_name = "ingress_display_en" if is_en else "ingress_display_ar"
        egr_col_name = "egress_display_en" if is_en else "egress_display_ar"

        table_df = filtered_df[[
            "tic_id", "sector", dip_col_name, "depth_display",
            ing_col_name, egr_col_name, "asym_display", cls_col_name
        ]].copy()

        table_df.columns = [
            t("col_tic_id"),
            t("col_sector"),
            t("col_dip_found"),
            t("col_depth"),
            t("col_ingress"),
            t("col_egress"),
            t("col_asymmetry"),
            t("col_classification"),
        ]

        event = st.dataframe(
            table_df,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="candidates_clean_dataframe",
        )

        if event.selection and event.selection.rows:
            selected_idx = event.selection.rows[0]
            selected_row = filtered_df.iloc[selected_idx].to_dict()
            st.session_state.selected_candidate = selected_row
            st.switch_page("app_pages/candidate_detail.py")
