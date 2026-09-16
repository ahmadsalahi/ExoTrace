"""
app_pages/history.py — Persistent Observation & Analysis History Log for ExoTrace.

Displays an audit record of all past astronomical scans and pipeline jobs,
providing scientific KPIs, status badges, search/category filters,
and seamless navigation to the observatory dashboard or new analysis console.
100% Bilingual (Arabic & English).
"""

import streamlit as st
import pandas as pd
from lib.i18n import t, get_theme, get_lang
from lib.analysis_runner import get_analysis_history
from lib.scan_history import get_star_name

is_en = (get_lang() == "en")
is_light = (get_theme() == "light")

# ── 1. Page Header ────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="margin-bottom: 12px;">
        <h1 style="margin: 0; font-size: 1.85rem; font-weight: 700; display: flex; align-items: center; gap: 10px;">
            <span>📜</span> <span>{t("history_title")}</span>
        </h1>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── 2. Data Retrieval ─────────────────────────────────────────────────────
history = get_analysis_history()

if not history:
    with st.container(border=True):
        st.info(t("history_empty_state"))
        st.caption(t("history_empty_caption"))
        if st.button(t("history_start_first_scan"), type="primary"):
            st.session_state.analysis_stage = "selection"
            st.switch_page("app_pages/new_analysis.py")
else:
    # ── 3. Scientific KPI Overview Cards ──────────────────────────────────
    total_jobs = len(history)
    completed_jobs = sum(1 for j in history if j.get("status") == "complete")
    total_dips = sum(int(j.get("dips_count", 0) or 0) for j in history)
    total_comets = sum(int(j.get("comets_count", 0) or 0) for j in history)

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        with st.container(border=True):
            st.metric(
                label=f"🛰️ {t('history_kpi_total')}",
                value=f"{total_jobs} {'runs' if is_en else 'جلسة'}",
                help=t("history_kpi_total_help"),
            )

    with kpi2:
        with st.container(border=True):
            st.metric(
                label=f"✅ {t('history_kpi_completed')}",
                value=f"{completed_jobs} {'runs' if is_en else 'جلسة'}",
                help=t("history_kpi_completed_help"),
            )

    with kpi3:
        with st.container(border=True):
            st.metric(
                label=f"📉 {t('history_kpi_dips')}",
                value=f"{total_dips} {'signals' if is_en else 'إشارة'}",
                help=t("history_kpi_dips_help"),
            )

    with kpi4:
        with st.container(border=True):
            st.metric(
                label=f"☄️ {t('history_kpi_comets')}",
                value=f"{total_comets} {'comets' if is_en else 'مذنّب'}",
                help=t("history_kpi_comets_help"),
            )

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # ── 4. Search & Filter Bar ────────────────────────────────────────────
    with st.container(border=True):
        search_col, filter_col = st.columns([1.6, 2], vertical_alignment="center")

        with search_col:
            search_query = st.text_input(
                "Search History",
                placeholder=t("history_search_placeholder"),
                label_visibility="collapsed",
                key="history_search_query",
            )

        with filter_col:
            filter_opts = [
                t("history_filter_all"),
                t("history_filter_comets"),
                t("history_filter_dips"),
                t("history_filter_completed"),
            ]
            selected_filter = st.segmented_control(
                "Filter History",
                options=filter_opts,
                default=filter_opts[0],
                label_visibility="collapsed",
                key="history_filter_segmented",
            )

    # ── 5. Filter History Records ─────────────────────────────────────────
    filtered_history = []
    for job in history:
        target_str = str(job.get("target", "")).lower()
        star_str = str(job.get("star_name", "")).lower()
        tic_str = str(job.get("tic_id", "")).lower()
        summary_str = str(job.get("summary", "")).lower()

        if search_query:
            sq = search_query.strip().lower()
            if (
                sq not in target_str
                and sq not in star_str
                and sq not in tic_str
                and sq not in summary_str
            ):
                continue

        comets_cnt = int(job.get("comets_count", 0) or 0)
        dips_cnt = int(job.get("dips_count", 0) or 0)
        status_val = job.get("status", "complete")

        if selected_filter == t("history_filter_comets") and comets_cnt == 0:
            continue
        elif selected_filter == t("history_filter_dips") and dips_cnt == 0:
            continue
        elif selected_filter == t("history_filter_completed") and status_val != "complete":
            continue

        filtered_history.append(job)

    # ── 6. Results List ───────────────────────────────────────────────────
    cnt_lbl_col = "#475569" if is_light else "#94a3b8"
    cnt_val_col = "#0284c7" if is_light else "#38bdf8"
    found_count_str = (
        f'Found <b style="color: {cnt_val_col};">{len(filtered_history)}</b> matching observation sessions'
        if is_en
        else f'تم العثور على <b style="color: {cnt_val_col};">{len(filtered_history)}</b> جلسة رصدية مطابقة'
    )

    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin: 12px 0 10px 0;">
            <span style="font-size: 0.95rem; font-weight: 600; color: {cnt_lbl_col};">
                {found_count_str}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not filtered_history:
        with st.container(border=True):
            st.info(t("history_no_results"))
            if st.button(t("history_reset_filters")):
                st.session_state["history_search_query"] = ""
                st.session_state["history_filter_segmented"] = filter_opts[0]
                st.rerun()
    else:
        for idx, job in enumerate(filtered_history):
            tic_id = str(job.get("tic_id", "")).replace("TIC", "").strip()
            star_name = get_star_name(tic_id, lang="en" if is_en else "ar")
            start_time = job.get("start_time", job.get("timestamp", "—"))
            job_status = job.get("status", "complete")
            job_type = job.get("type", "single")
            sectors_cnt = int(job.get("sectors_count", 1) or 1)
            dips_cnt = int(job.get("dips_count", 0) or 0)
            comets_cnt = int(job.get("comets_count", 0) or 0)

            summary_txt = job.get("summary_en" if is_en else "summary", job.get("summary", ""))
            if is_en and not job.get("summary_en"):
                if comets_cnt > 0:
                    summary_txt = f"Confirmed {comets_cnt} comet candidate(s) with steep ingress and elongated dust tails."
                elif dips_cnt > 0:
                    summary_txt = f"Detected {dips_cnt} symmetric brightness dips matching planetary or binary transits."
                else:
                    summary_txt = "High photometric stability observed — zero dips exceeding statistical threshold."

            with st.container(border=True):
                h_col1, h_col2 = st.columns([3, 1], vertical_alignment="center")
                card_tic_col = "#0284c7" if is_light else "#38bdf8"
                card_star_col = "#0f172a" if is_light else "#f1f5f9"

                with h_col1:
                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                            <span style="font-size: 1.25rem; font-weight: 700; color: {card_tic_col};">⭐ TIC {tic_id}</span>
                            <span style="color: #64748b; font-size: 1rem;">•</span>
                            <span style="font-weight: 600; font-size: 1.05rem; color: {card_star_col};">{star_name}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if is_en:
                        mission_lbl = "Sector Cadence Survey" if job_type == "survey" else "Target Reanalysis"
                        obs_meta_html = f"📅 Observation Date: <span style='font-weight:600;'>{start_time}</span> • 🔭 Mission Mode: <span style='font-weight:600;'>{mission_lbl}</span>"
                    else:
                        mission_lbl = "مسح شامل للقطاعات (Sector Survey)" if job_type == "survey" else "تحليل نجم فردي مخصص (Target Reanalysis)"
                        obs_meta_html = f"📅 تاريخ الرصد: <span style='font-weight:600;'>{start_time}</span> • 🔭 نمط المهمة: <span style='font-weight:600;'>{mission_lbl}</span>"

                    cap_col = "#475569" if is_light else "#94a3b8"
                    st.markdown(
                        f"""
                        <div style="color:{cap_col}; font-size:0.83rem; margin-top:2px;">
                            {obs_meta_html}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with h_col2:
                    if job_status == "running":
                        run_bg = "#e0f2fe" if is_light else "rgba(56,189,248,0.15)"
                        run_col = "#0369a1" if is_light else "#38bdf8"
                        run_bdr = "#7dd3fc" if is_light else "#38bdf8"
                        status_lbl = "🔵 Running..." if is_en else "🔵 قيد المعالجة..."
                        st.markdown(
                            f"""
                            <div style="display: flex; justify-content: flex-end;">
                                <span style="background: {run_bg}; color: {run_col}; border: 1px solid {run_bdr}; padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 0.85rem;">
                                    {status_lbl}
                                </span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    elif job_status == "complete":
                        done_bg = "#dcfce7" if is_light else "rgba(16,185,129,0.15)"
                        done_col = "#15803d" if is_light else "#34d399"
                        done_bdr = "#86efac" if is_light else "#10b981"
                        status_lbl = "🟢 Completed ✓" if is_en else "🟢 مكتمل بنجاح ✓"
                        st.markdown(
                            f"""
                            <div style="display: flex; justify-content: flex-end;">
                                <span style="background: {done_bg}; color: {done_col}; border: 1px solid {done_bdr}; padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 0.85rem;">
                                    {status_lbl}
                                </span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    else:
                        err_bg = "#fee2e2" if is_light else "rgba(239,68,68,0.15)"
                        err_col = "#b91c1c" if is_light else "#f87171"
                        err_bdr = "#fca5a5" if is_light else "#ef4444"
                        status_lbl = "🔴 Failed" if is_en else "🔴 تعذر الفحص"
                        st.markdown(
                            f"""
                            <div style="display: flex; justify-content: flex-end;">
                                <span style="background: {err_bg}; color: {err_col}; border: 1px solid {err_bdr}; padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 0.85rem;">
                                    {status_lbl}
                                </span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                # Row 2: Scientific Metrics Strip
                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    lbl1 = "🔭 Surveyed Sectors" if is_en else "🔭 القطاعات المفحوصة"
                    val1 = f"{sectors_cnt} Sectors" if is_en else f"{sectors_cnt} قطاع"
                    st.metric(label=lbl1, value=val1)
                with m2:
                    lbl2 = "📉 Flux Dips" if is_en else "📉 انخفاضات السطوع"
                    val2 = f"{dips_cnt} Dips" if is_en else f"{dips_cnt} هبوط"
                    st.metric(label=lbl2, value=val2)
                with m3:
                    lbl3 = "☄️ Comet Candidates" if is_en else "☄️ المذنبات المرشحة"
                    val3 = f"{comets_cnt} Comets" if is_en else f"{comets_cnt} مذنّب"
                    delta3 = ("Validated" if is_en else "مرشح مؤكد") if comets_cnt > 0 else None
                    st.metric(label=lbl3, value=val3, delta=delta3, delta_color="normal")
                with m4:
                    lbl4 = "📊 Result Classification" if is_en else "📊 النتيجة الرصدية"
                    if is_en:
                        val4 = "Cometary Activity" if comets_cnt > 0 else ("Symmetric Transit" if dips_cnt > 0 else "Photometric Stability")
                    else:
                        val4 = "نشاط مذنبي" if comets_cnt > 0 else ("عبور متماثل" if dips_cnt > 0 else "استقرار ضوئي")
                    st.metric(label=lbl4, value=val4)

                # Row 3: Scientific Summary Quote
                if summary_txt:
                    sum_bg = "#f0f9ff" if is_light else "rgba(15,23,42,0.65)"
                    sum_border = "1px solid #bae6fd" if is_light else "1px solid rgba(56,189,248,0.25)"
                    sum_title_col = "#0284c7" if is_light else "#38bdf8"
                    sum_txt_col = "#1e293b" if is_light else "#cbd5e1"
                    sum_head = "Scientific Summary:" if is_en else "أهم المخرجات والنتائج:"
                    st.markdown(
                        f"""
                        <div style="background:{sum_bg}; border:{sum_border}; border-radius:10px; padding:10px 14px; margin:10px 0 12px 0; display:flex; align-items:center; gap:10px;">
                            <span style="font-size:1.25rem;">🔬</span>
                            <div style="font-size:0.88rem; line-height:1.5;">
                                <strong style="color:{sum_title_col};">{sum_head}</strong>
                                <span style="color:{sum_txt_col}; margin-right:4px; margin-left:4px;">{summary_txt}</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # Row 4: Action Buttons
                btn1, btn2, btn3 = st.columns([1.6, 1.4, 1.2])

                with btn1:
                    btn1_label = "View in Dashboard" if is_en else "عرض النتائج في المرصد"
                    if st.button(
                        btn1_label,
                        key=f"hist_dash_{tic_id}_{idx}",
                        width="stretch",
                        type="primary",
                        icon=":material/visibility:",
                    ):
                        clean_target = int(tic_id) if tic_id.isdigit() else tic_id
                        st.session_state.selected_tic = clean_target
                        st.session_state.dashboard_focused_tic = str(clean_target)
                        st.session_state.just_analyzed_tic = str(clean_target)
                        st.session_state.spotlight_index = 0
                        st.switch_page("app_pages/dashboard.py")

                with btn2:
                    btn2_label = "Explore Signals" if is_en else "استعراض المرشحين"
                    if st.button(
                        btn2_label,
                        key=f"hist_cand_{tic_id}_{idx}",
                        width="stretch",
                        icon=":material/travel_explore:",
                    ):
                        st.session_state.filter_tic = str(tic_id)
                        st.switch_page("app_pages/candidates.py")

                with btn3:
                    btn3_label = "Re-analyze" if is_en else "إعادة الفحص"
                    if st.button(
                        btn3_label,
                        key=f"hist_rerun_{tic_id}_{idx}",
                        width="stretch",
                        icon=":material/refresh:",
                    ):
                        clean_target = int(tic_id) if tic_id.isdigit() else tic_id
                        st.session_state.selected_tic = clean_target
                        st.session_state.analysis_stage = "selection"
                        st.switch_page("app_pages/new_analysis.py")
