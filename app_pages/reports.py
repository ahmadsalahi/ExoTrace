"""
app_pages/reports.py — Comprehensive Scientific Reports & Export Suite for ExoTrace.

Provides two dedicated reporting tools:
  1. Star Scan Discovery Dossier (Single Star PDF with embedded light curve plot & metrics).
  2. Tabular Signals & Comets Export (Filterable table for single, multiple, or all stars exported to Excel, CSV, or PDF).
100% Bilingual (Arabic & English).
"""

import os
import io
import time
import pandas as pd
import streamlit as st
from lib.i18n import t, get_theme, get_lang
from lib.data_loader import (
    get_all_results,
    get_candidate_plots,
    load_lightcurve,
)
from lib.scan_history import get_scan_history, get_star_name
from lib.pdf_generator import generate_star_report_pdf, generate_table_report_pdf
from lib.excel_generator import generate_styled_excel

is_en = (get_lang() == "en")
is_light = (get_theme() == "light")

# ── 1. Page Header ────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="margin-bottom: 16px;">
        <h1 style="margin: 0; font-size: 1.85rem; font-weight: 700; display: flex; align-items: center; gap: 10px;">
            <span>📄</span> <span>{t("reports_title")}</span>
        </h1>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── 2. Data Retrieval ─────────────────────────────────────────────────────
scans = get_scan_history()
scanned_dict = {str(s.get("tic_id")): s for s in scans}
df_all = get_all_results()

if not scans and df_all.empty:
    with st.container(border=True):
        st.info(t("reports_empty_state"))
        st.caption(t("reports_empty_caption"))
        if st.button(t("history_start_first_scan"), type="primary"):
            st.session_state.analysis_stage = "selection"
            st.switch_page("app_pages/new_analysis.py")
    st.stop()

# Build list of scanned stars available for reporting
available_stars = []
unique_tics = df_all["tic_id"].dropna().unique() if not df_all.empty else []

for raw_t_id in unique_tics:
    t_id = str(int(float(raw_t_id)))
    s_name = get_star_name(t_id, lang="en" if is_en else "ar").split("(")[0].strip()
    
    # Calculate truth from dataframe directly
    sub = df_all[df_all["tic_id"].astype(str).str.replace(".0", "", regex=False) == t_id]
    c_count = int((sub["category_code"] == "strong").sum())
    d_count = int((sub["dip_found_bool"] == True).sum())
    s_count = sub["sector"].nunique() if "sector" in sub.columns else 1
    
    # Get metadata from the latest scan if available
    s = scanned_dict.get(t_id, {})
    
    if is_en:
        label = f"⭐ {s_name} (TIC {t_id}) — {c_count} Comet{'s' if c_count != 1 else ''} | {d_count} Dip{'s' if d_count != 1 else ''}"
    else:
        label = f"⭐ {s_name} (TIC {t_id}) — {c_count} مذنّب مرشح | {d_count} إشارة هبوط"
        
    available_stars.append({
        "tic_id": t_id,
        "star_name": s_name,
        "label": label,
        "history": {
            "tic_id": t_id,
            "star_name": s_name,
            "timestamp": s.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S")),
            "sectors_count": s_count,
            "dips_count": d_count,
            "comets_count": c_count,
            "status": s.get("status", "Completed ✓" if is_en else "مكتمل بنجاح ✓"),
            "summary": (f"Detected {d_count} dip(s) and {c_count} comet candidate(s) in {s_count} sector(s)." if is_en else f"تم رصد {d_count} إشارة هبوط و {c_count} مذنّب مرشح ضمن {s_count} قطاع."),
        },
    })

# ── 3. Two Main Report Tabs ───────────────────────────────────────────────
tab_single_star, tab_table_export = st.tabs([
    t("reports_tab_single"),
    t("reports_tab_table"),
])

# ═══════════════════════════════════════════════════════════════════════════
# TAB 1: Single Star Scan Discovery Dossier
# ═══════════════════════════════════════════════════════════════════════════
with tab_single_star:
    selected_star = st.selectbox(
        t("reports_select_star"),
        options=available_stars,
        format_func=lambda x: x["label"],
        key="report_selected_star",
    )

    if selected_star:
        sel_tic = selected_star["tic_id"]
        sel_name = selected_star["star_name"]
        hist = selected_star["history"]
        star_df = df_all[df_all["tic_id"].astype(str).str.replace(".0", "", regex=False) == sel_tic].copy() if not df_all.empty else pd.DataFrame()

        plots = get_candidate_plots(int(sel_tic))
        chosen_plot = None
        
        # Generate dynamic matplotlib plot for the report (without taking permanent storage)
        event_rows = star_df[star_df.get("dip_found_bool", False) == True].copy() if not star_df.empty and "dip_found_bool" in star_df.columns else pd.DataFrame()
        best_sector = None
        if not event_rows.empty:
            score_col = "morphology_score" if "morphology_score" in event_rows.columns else "depth"
            best = event_rows.sort_values(score_col, ascending=False).iloc[0]
            best_sector = int(best.get("sector", 0))
        elif not star_df.empty:
            best_sector = int(star_df.iloc[0].get("sector", 0))
            
        if best_sector is not None:
            lc_data = load_lightcurve(int(sel_tic), best_sector, flat=True)
            if not lc_data.empty and "flux_flat" in lc_data.columns:
                import matplotlib.pyplot as plt
                import tempfile
                
                fig, ax = plt.subplots(figsize=(10, 4))
                ax.plot(lc_data["time"], lc_data["flux_flat"], "k.", ms=1.5, alpha=0.5, label="Detrended Flux")
                
                # Highlight detected dips
                sector_events = event_rows[event_rows["sector"] == best_sector]
                added_label = False
                for _, ev in sector_events.iterrows():
                    s_t = ev.get("start_time")
                    e_t = ev.get("end_time")
                    if pd.notna(s_t) and pd.notna(e_t):
                        lbl = "Detected Dip" if not added_label else ""
                        ax.axvspan(s_t, e_t, color="red", alpha=0.25, label=lbl)
                        added_label = True

                ax.axhline(1.0, color="gray", ls="--", lw=1)
                ax.set_title(f"TIC {sel_tic} — Sector {best_sector} (Detrended)", fontsize=12)
                ax.set_xlabel("Time (BJD)", fontsize=10)
                ax.set_ylabel("Normalized Flux", fontsize=10)
                ax.legend(loc="upper right", fontsize=9)
                fig.tight_layout()
                
                tmp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
                fig.savefig(tmp_img, dpi=150, bbox_inches="tight", facecolor="white")
                plt.close(fig)
                chosen_plot = tmp_img

        with st.container(border=True):
            col_title, col_badge = st.columns([3, 1], vertical_alignment="center")
            rep_title_col = "#0284c7" if is_light else "#38bdf8"
            rep_date_col = "#475569" if is_light else "#94a3b8"
            status_bg = "#dcfce7" if is_light else "rgba(34, 197, 94, 0.15)"
            status_col = "#15803d" if is_light else "#4ade80"
            status_border = "1px solid #86efac" if is_light else "1px solid rgba(34, 197, 94, 0.3)"

            dossier_title = f"Survey Dossier: {sel_name} (TIC {sel_tic})" if is_en else f"تقرير الفحص الرصدي: {sel_name} (TIC {sel_tic})"
            
            # Use dynamic history from selected_star (which is perfectly in sync with df_all)
            obs_ts = str(hist.get("timestamp", pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")))
            status_str = ("Completed ✓" if hist.get("status") in ["مكتمل بنجاح ✓", "complete", "Completed ✓"] else hist.get("status", "Completed ✓")) if is_en else hist.get("status", "مكتمل بنجاح ✓")

            with col_title:
                st.markdown(
                    f"""
                    <div style="margin-bottom: 8px;">
                        <h2 style="margin: 0; font-size: 1.5rem; font-weight: 800; color: {rep_title_col};">
                            {dossier_title}
                        </h2>
                        <div style="color: {rep_date_col}; font-size: 0.88rem; margin-top: 3px;">
                            {t('reports_scan_date')} <b>{obs_ts}</b>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col_badge:
                st.markdown(
                    f"""
                    <div style="text-align: {'right' if is_en else 'left'};">
                        <span style="display: inline-block; padding: 6px 14px; background: {status_bg}; color: {status_col}; border: {status_border}; border-radius: 8px; font-weight: 700; font-size: 0.88rem;">
                            {status_str}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Action Buttons at the TOP
            default_sum = "Analysis and light curve transit modeling executed successfully." if is_en else "تم إنجاز الفحص وتحليل المنحنى الضوئي بدقة وتسجيل النتائج."
            summary_text = hist.get("summary_en" if is_en else "summary", hist.get("summary", default_sum))
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                try:
                    pdf_bytes = generate_star_report_pdf(
                        sel_tic=str(sel_tic),
                        star_name=str(sel_name),
                        scan_time=obs_ts,
                        status=status_str,
                        sectors=int(hist.get("sectors_count", 1) or 1),
                        dips=int(hist.get("dips_count", 0) or 0),
                        comets=int(hist.get("comets_count", 0) or 0),
                        summary=str(summary_text),
                        star_df_records=star_df.to_dict("records") if not star_df.empty else [],
                        plot_path=chosen_plot,
                        lang="en" if is_en else "ar",
                    )
                    st.download_button(
                        label=t("reports_pdf_download_btn"),
                        data=pdf_bytes,
                        file_name=f"ExoTrace_Report_TIC_{sel_tic}_{time.strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        width="stretch",
                        icon=":material/picture_as_pdf:",
                        type="primary",
                    )
                except Exception as e:
                    st.error(f"Error generating PDF: {e}" if is_en else f"تعذر توليد ملف PDF: {e}")

            with btn_col2:
                if chosen_plot and os.path.exists(chosen_plot):
                    try:
                        with open(chosen_plot, "rb") as f:
                            img_bytes = f.read()
                        btn_img_lbl = "Download Plot (PNG)" if is_en else "تنزيل المخطط البياني (PNG)"
                        st.download_button(
                            label=btn_img_lbl,
                            data=img_bytes,
                            file_name=f"Plot_TIC_{sel_tic}.png",
                            mime="image/png",
                            width="stretch",
                            icon=":material/image:",
                        )
                    except Exception:
                        st.button("Plot unavailable" if is_en else "المخطط غير متوفر", disabled=True, width="stretch")
                else:
                    st.button("No plot available" if is_en else "لا توجد صورة", disabled=True, width="stretch")

            hr_border = "1px solid #e2e8f0" if is_light else "1px solid rgba(255,255,255,0.08)"
            st.markdown(f"<hr style='border:none; border-top:{hr_border}; margin:12px 0 16px 0;'>", unsafe_allow_html=True)

            # 4 Macro KPIs
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                with st.container(border=True):
                    st.metric("Survey Date" if is_en else "📅 تاريخ الفحص", obs_ts.split(" ")[0])
            with k2:
                with st.container(border=True):
                    st.metric("Surveyed Sectors" if is_en else "🔭 القطاعات المفحوصة", f"{hist.get('sectors_count', 1)} {'Sectors' if is_en else 'قطاع'}")
            with k3:
                with st.container(border=True):
                    st.metric("Flux Dips" if is_en else "📉 إشارات الهبوط", f"{hist.get('dips_count', 0)} {'Dips' if is_en else 'إشارة'}")
            with k4:
                with st.container(border=True):
                    st.metric("Comet Candidates" if is_en else "☄️ المذنبات المرشحة", f"{hist.get('comets_count', 0)} {'Comets' if is_en else 'مذنّب'}")

            # Light Curve Plot Section
            if chosen_plot and os.path.exists(chosen_plot):
                st.markdown("#### " + ("Photometric Light Curve" if is_en else "📈 المنحنى الضوئي الرصدي"))
                cap_str = f"Photometric Cadence for {sel_name} (TIC {sel_tic})" if is_en else f"المنحنى الضوئي للنجم {sel_name} (TIC {sel_tic})"
                st.image(
                    chosen_plot,
                    width="stretch",
                    caption=cap_str,
                )


# ═══════════════════════════════════════════════════════════════════════════
# TAB 2: Filterable Tabular Data Export (Single, Multiple, or All Stars)
# ═══════════════════════════════════════════════════════════════════════════
with tab_table_export:
    st.markdown("### " + ("📊 Candidates & Signals Dataset Export" if is_en else "📊 تصدير جدول المذنبات والإشارات الرصدية"))

    with st.container(border=True):
        f_scope, f_sig = st.columns([1.5, 1.5], vertical_alignment="center")

        scope_opts = ["All Surveyed Stars", "Specific Star", "Multiple Stars"] if is_en else ["كل النجوم المفحوصة", "نجم محدد", "تحديد عدة نجوم"]

        with f_scope:
            scope_choice = st.radio(
                "Target Scope:" if is_en else "نطاق النجوم المطلوب تضمينها في الجدول:",
                options=scope_opts,
                horizontal=True,
                key="tbl_scope_radio",
            )

        signal_opts = [
            "☄️ Exocomet Candidates Only",
            "📉 All Detected Flux Dips",
            "⭐ All Surveyed Targets",
        ] if is_en else [
            "☄️ المذنبات المرشحة فقط (Comet Candidates)",
            "📉 جميع انخفاضات السطوع المرصودة (All Dips)",
            "⭐ كافة السجلات والأرصاد (All Records)",
        ]

        with f_sig:
            signal_choice = st.selectbox(
                "Signal Type:" if is_en else "نوع الإشارات الرصدية المطلوب تصديرها:",
                options=signal_opts,
                key="tbl_signal_choice",
            )

    selected_target_tics = []
    if scope_choice in ["Specific Star", "نجم محدد"]:
        single_pick = st.selectbox(
            "Select Target Star:" if is_en else "اختر النجم:",
            options=available_stars,
            format_func=lambda x: x["label"],
            key="tbl_single_picker",
        )
        if single_pick:
            selected_target_tics = [str(single_pick["tic_id"])]
    elif scope_choice in ["Multiple Stars", "تحديد عدة نجوم"]:
        multi_pick = st.multiselect(
            "Select Target Stars:" if is_en else "اختر النجوم المراد جمعها في التقرير:",
            options=available_stars,
            default=available_stars[:min(2, len(available_stars))],
            format_func=lambda x: x["label"],
            key="tbl_multi_picker",
        )
        selected_target_tics = [str(s["tic_id"]) for s in multi_pick]
    else:
        selected_target_tics = [str(s["tic_id"]) for s in available_stars]

    df_filtered = df_all.copy()

    if selected_target_tics:
        df_filtered = df_filtered[df_filtered["tic_id"].astype(str).str.replace(".0", "", regex=False).isin(selected_target_tics)]
    else:
        df_filtered = pd.DataFrame()

    if not df_filtered.empty:
        if signal_choice.startswith("☄️"):
            df_filtered = df_filtered[df_filtered["category_code"] == "strong"]
        elif signal_choice.startswith("📉"):
            df_filtered = df_filtered[df_filtered["dip_found_bool"] == True]

        df_filtered["star_name"] = df_filtered["tic_id"].astype(str).apply(
            lambda x: get_star_name(x, lang="en" if is_en else "ar").split("(")[0].strip()
        )

        if is_en:
            disp_cols = {
                "tic_id": "Star (TIC)",
                "star_name": "Star Name",
                "sector": "Sector",
                "classification_en": "Classification",
                "depth_display": "Dip Depth %",
                "asym_display": "Asymmetry (A)",
                "ingress_display_en": "Ingress Time",
                "egress_display_en": "Egress Time",
                "duration_display_en": "Duration",
            }
            # Fallback if _en column absent
            for col, fb in [("ingress_display_en", "ingress_display"), ("egress_display_en", "egress_display"), ("duration_display_en", "duration_display"), ("classification_en", "classification_ar")]:
                if col not in df_filtered.columns and fb in df_filtered.columns:
                    disp_cols[fb] = disp_cols.pop(col)
        else:
            disp_cols = {
                "tic_id": "رقم النجم (TIC)",
                "star_name": "اسم النجم",
                "sector": "القطاع",
                "classification_ar": "التصنيف الرصدي",
                "depth_display": "عمق الهبوط %",
                "asym_display": "اللاتماثل (A)",
                "ingress_display": "زمن الدخول",
                "egress_display": "زمن الخروج",
                "duration_display": "مدة العبور",
            }

        valid_cols = [c for c in disp_cols.keys() if c in df_filtered.columns]
        sort_col = "Star (TIC)" if is_en else "رقم النجم (TIC)"
        sector_sort_col = "Sector" if is_en else "القطاع"
        tbl_to_show = df_filtered[valid_cols].rename(columns=disp_cols).sort_values(by=[sort_col, sector_sort_col]).reset_index(drop=True)

        b_c1, b_c2 = st.columns(2)

        scope_label = scope_choice
        if scope_choice in ["Specific Star", "نجم محدد"] and selected_target_tics:
            scope_label = f"Target TIC {selected_target_tics[0]}" if is_en else f"النجم TIC {selected_target_tics[0]}"
        elif scope_choice in ["Multiple Stars", "تحديد عدة نجوم"]:
            scope_label = f"{len(selected_target_tics)} Selected Stars" if is_en else f"{len(selected_target_tics)} نجوم مختارة"

        # Styled Excel Export
        with b_c1:
            try:
                rep_title = "Exocomet Candidates & Signals Registry" if is_en else "جدول المذنبات والإشارات الرصدية"
                xlsx_styled_bytes = generate_styled_excel(
                    df_records=tbl_to_show.to_dict("records"),
                    report_title=rep_title,
                    scope_desc=f"{scope_label} • {signal_choice.split('(')[0].strip()}",
                    lang="en" if is_en else "ar",
                )
                btn_excel_lbl = "Export Dataset to Styled Excel (.xlsx)" if is_en else "تصدير الجدول إلى Excel منسق (.xlsx)"
                st.download_button(
                    label=btn_excel_lbl,
                    data=xlsx_styled_bytes,
                    file_name=f"ExoTrace_Table_Export_{time.strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width="stretch",
                    icon=":material/table:",
                    type="primary",
                )
            except Exception as e:
                st.error(f"Error generating Excel file: {e}" if is_en else f"تعذر توليد ملف Excel: {e}")

        # PDF Table Export
        with b_c2:
            try:
                pdf_table_bytes = generate_table_report_pdf(
                    report_title="📊 Candidates & Signals Dataset" if is_en else "📊 جدول المذنبات والإشارات الرصدية",
                    scope_description=f"{scope_label} • {signal_choice.split('(')[0].strip()}",
                    records=df_filtered.to_dict("records"),
                    lang="en" if is_en else "ar",
                )
                btn_pdf_lbl = "Export Table to A4 PDF" if is_en else "تصدير الجدول كملف (PDF)"
                st.download_button(
                    label=btn_pdf_lbl,
                    data=pdf_table_bytes,
                    file_name=f"ExoTrace_Table_Export_{time.strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    width="stretch",
                    icon=":material/picture_as_pdf:",
                )
            except Exception as e:
                st.error(f"Error generating PDF file: {e}" if is_en else f"تعذر توليد ملف الـ PDF: {e}")

        caption_msg = f"Found {len(tbl_to_show)} photometric records matching selected criteria:" if is_en else f"تم العثور على {len(tbl_to_show)} سجل رصدي يطابق المعايير المحددة:"
        st.caption(caption_msg)
        st.dataframe(tbl_to_show, width="stretch", hide_index=True)
    else:
        st.info("No records matching the selected filters." if is_en else "لا توجد سجلات تطابق الفلاتر المحددة حالياً.")
