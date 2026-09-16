"""
app_pages/new_analysis.py — Astronomical Mission Console for ExoTrace.

Refactored Flow:
1. Star List & Search (Selection)
2. Calibration & Confirmation
3. Live Telemetry Analysis (5 Stages)
4. Automatic Redirect to Dashboard
100% Bilingual (Arabic & English).
"""

import time
import streamlit as st
import pandas as pd
from lib.i18n import t, is_rtl, get_theme, get_lang
from lib.data_loader import get_all_results
from lib.settings_manager import load_analysis_settings
from lib.analysis_runner import run_single_analysis, run_sector_survey

is_en = (get_lang() == "en")
is_light = (get_theme() == "light")

# ── Curated TESS Stars Catalog (10 Curated Stars + Custom/Other) ──────
CURATED_TESS_CATALOG = [
    {
        "tic": "110969638",
        "name_ar": "مرشح مذنّب بارز (Exocomet Candidate)",
        "name_en": "Exocomet Benchmark Candidate",
        "label_ar": "⭐ TIC 110969638 — مرشح مذنّب بارز (قطاع 7, 34)",
        "label_en": "⭐ TIC 110969638 — Exocomet Benchmark (Sector 7, 34)",
        "sectors": "7, 34",
        "type_ar": "نجم متطور (Evolved Star)",
        "type_en": "Evolved Star (Active Dust Tail)",
        "desc_ar": "نجم متطور يحتوي على إشارات انخفاض غير متماثلة واضحة المعالم، يُشتبه بوجود ذيل غباري ممتد له.",
        "desc_en": "Evolved giant star exhibiting deep asymmetric photometric dips consistent with an extended cometary dust tail.",
    },
    {
        "tic": "229790952",
        "name_ar": "Beta Pictoris (بيتا بيكتوريس)",
        "name_en": "Beta Pictoris (Circumstellar Disk)",
        "label_ar": "⭐ TIC 229790952 — Beta Pictoris (بيتا بيكتوريس - قطاع 13, 27)",
        "label_en": "⭐ TIC 229790952 — Beta Pictoris (Sector 13, 27)",
        "sectors": "13, 27",
        "type_ar": "A6V Star (قرص حطام نشط)",
        "type_en": "A6V Star (Circumstellar Debris Disk)",
        "desc_ar": "نجم شاب شهير بقرص غباري كثيف ومذنبات خارجية عابرة مكتشفة حديثاً.",
        "desc_en": "Famous young A-type star hosting a prominent debris disk and historically confirmed transiting exocomets.",
    },
    {
        "tic": "245792896",
        "name_ar": "قرص حطام نجمي (Debris Disk System)",
        "name_en": "Debris Disk System",
        "label_ar": "⭐ TIC 245792896 — هدف رصدي نشط (قطاع 70)",
        "label_en": "⭐ TIC 245792896 — Active Target (Sector 70)",
        "sectors": "70",
        "type_ar": "قرص حطام نجمي",
        "type_en": "Circumstellar Debris System",
        "desc_ar": "نجم مسجل في أرشيف TESS مع انخفاضات ضوئية حطامية مرصودة محلياً.",
        "desc_en": "TESS target with recorded circumstellar debris and transient dust occultations.",
    },
    {
        "tic": "264306713",
        "name_ar": "HD 172555",
        "name_en": "HD 172555",
        "label_ar": "⭐ TIC 264306713 — HD 172555 (قطاع 60)",
        "label_en": "⭐ TIC 264306713 — HD 172555 (Sector 60)",
        "sectors": "60",
        "type_ar": "A7V Star",
        "type_en": "A7V Star (Debris Belt)",
        "desc_ar": "نظام نجمي شهير بنشاط مذنبي وتصادمات كويكبية موثقة بأجهزة الرصد.",
        "desc_en": "A-type star with documented hypervelocity impacts and variable circumstellar cometary absorption.",
    },
    {
        "tic": "341705353",
        "name_ar": "قزم نجمي متطور (DWARF)",
        "name_en": "Evolved Dwarf Star (DWARF)",
        "label_ar": "⭐ TIC 341705353 — قزم نجمي متطور (قطاع 40)",
        "label_en": "⭐ TIC 341705353 — Evolved Dwarf (Sector 40)",
        "sectors": "40",
        "type_ar": "F/G-type Star",
        "type_en": "F/G-type Star",
        "desc_ar": "هدف فلكي ضمن عينة المسح المرجعية لمرصد ExoTrace.",
        "desc_en": "Reference target within the ExoTrace photometric survey calibration catalogue.",
    },
    {
        "tic": "353304732",
        "name_ar": "نظام مسح دوري (DWARF)",
        "name_en": "Periodic Survey System (DWARF)",
        "label_ar": "⭐ TIC 353304732 — نظام مسح دوري (قطاع 60)",
        "label_en": "⭐ TIC 353304732 — Periodic Survey System (Sector 60)",
        "sectors": "60",
        "type_ar": "DWARF Target",
        "type_en": "DWARF Survey Target",
        "desc_ar": "نجم ذو سطوع منتظم مسجل في كتالوج TESS للنجوم المتطورة.",
        "desc_en": "High photometric stability star monitored for transient non-periodic transit dips.",
    },
    {
        "tic": "51904828",
        "name_ar": "HD 131488",
        "name_en": "HD 131488",
        "label_ar": "⭐ TIC 51904828 — HD 131488 (قطاع 40)",
        "label_en": "⭐ TIC 51904828 — HD 131488 (Sector 40)",
        "sectors": "40",
        "type_ar": "A-type Star",
        "type_en": "A-type Star (CO Gas Rich)",
        "desc_ar": "نظام غني بغبار أول أكسيد الكربون الحطامي حول النجم.",
        "desc_en": "Circumstellar debris disk host with dense circumstellar carbon monoxide and icy dust belts.",
    },
    {
        "tic": "261136679",
        "name_ar": "HD 209458 (Osiris)",
        "name_en": "HD 209458 (Osiris)",
        "label_ar": "⭐ TIC 261136679 — HD 209458 (Osiris - قطاع 5)",
        "label_en": "⭐ TIC 261136679 — HD 209458 (Osiris - Sector 5)",
        "sectors": "5",
        "type_ar": "G0V Star",
        "type_en": "G0V Star (Benchmark Transit)",
        "desc_ar": "أحد أشهر الأهداف الفلكية لدراسة العبور النجمي والأغلفة الجوية.",
        "desc_en": "Primary benchmark star for high-precision exoplanet transit and atmospheric evaporation studies.",
    },
    {
        "tic": "149603524",
        "name_ar": "نجم فائق السطوع",
        "name_en": "High-Luminosity Benchmark",
        "label_ar": "⭐ TIC 149603524 — نجم فائق السطوع (قطاع 14)",
        "label_en": "⭐ TIC 149603524 — High-Luminosity Star (Sector 14)",
        "sectors": "14",
        "type_ar": "A-type Bright Star",
        "type_en": "A-type Bright Star",
        "desc_ar": "نجم عالي الدقة في القياس الضوئي مناسب لرصد الانخفاضات العميقة.",
        "desc_en": "Ultra-bright target optimized for ultra-low noise light curve extraction and shallow transit profiling.",
    },
    {
        "tic": "25155310",
        "name_ar": "WASP-121",
        "name_en": "WASP-121",
        "label_ar": "⭐ TIC 25155310 — WASP-121 (نظام كوكبي متطرف - قطاع 7)",
        "label_en": "⭐ TIC 25155310 — WASP-121 (Extreme Planetary System - Sector 7)",
        "sectors": "7",
        "type_ar": "F6V Star",
        "type_en": "F6V Star (Ultra-Hot System)",
        "desc_ar": "نظام فلكي شهير بظواهره المتطرفة وتدفقات الغاز النيزكية.",
        "desc_en": "Extreme exoplanetary system exhibiting extreme hydrodynamic atmospheric escape and cometary-like tails.",
    },
]

OTHER_CATALOG_OPTION = "Other: Enter Custom Target TIC ID" if is_en else "خيار آخر: إدخال رقم نجم مخصص (Other / Custom TIC ID)"

# ── State Machine Initialization ─────────────────────────────────────
if "analysis_stage" not in st.session_state:
    st.session_state.analysis_stage = "selection"
if "selected_tic" not in st.session_state:
    st.session_state.selected_tic = None
if "run_mode" not in st.session_state:
    st.session_state.run_mode = "single"
if "sector_list" not in st.session_state:
    st.session_state.sector_list = []
if "sigma_val" not in st.session_state:
    st.session_state.sigma_val = 3.0
if "min_asym_val" not in st.session_state:
    st.session_state.min_asym_val = 0.05
if "detrend_win" not in st.session_state:
    st.session_state.detrend_win = 2.0

# ── Master Container ──────────────────────────────────────────────
master_container = st.empty()

with master_container.container():
    # ── STATE 1: SELECTION (Manual Search as Primary + Suggestions as Secondary) ──
    if st.session_state.analysis_stage == "selection":
        st.markdown(f"### 🔭 {t('new_analysis_title')}")
        st.caption(t("new_analysis_subtitle"))

        # 1. PRIMARY SECTION: Manual Search Container
        with st.container(border=True):
            header_color = "#0284c7" if is_light else "#38bdf8"
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px;">
                    <span style="font-size:1.4rem;">🎯</span>
                    <h3 style="margin:0; font-size:1.15rem; font-weight:700; color:{header_color};">{t('manual_search_heading')}</h3>
                </div>
                """,
                unsafe_allow_html=True,
            )

            mode_opts = [t("mode_single"), t("mode_multiple"), t("mode_sectors")]
            search_mode = st.segmented_control(
                t("input_mode_label"),
                options=mode_opts,
                default=mode_opts[0],
                key="manual_search_mode",
            )

            tic_to_run = None
            sectors_to_run = []
            valid_input = False

            if search_mode == t("mode_single"):
                cat_labels = [c["label_en" if is_en else "label_ar"] for c in CURATED_TESS_CATALOG] + [OTHER_CATALOG_OPTION]
                selected_choice = st.selectbox(
                    t("input_single_label"),
                    options=cat_labels,
                    index=0,
                    help=t("input_single_help"),
                    key="input_catalog_select"
                )

                if selected_choice == OTHER_CATALOG_OPTION:
                    custom_tic_in = st.text_input(
                        t("input_custom_tic_label"),
                        placeholder=t("input_custom_placeholder"),
                        help=t("input_custom_tic_help"),
                        key="input_custom_tic"
                    )
                    clean_tic = custom_tic_in.strip().replace("TIC", "").strip()
                    if clean_tic.isdigit():
                        tic_to_run = clean_tic
                        valid_input = True
                else:
                    target_match = next((c for c in CURATED_TESS_CATALOG if c["label_en" if is_en else "label_ar"] == selected_choice), None)
                    if target_match:
                        tic_to_run = target_match["tic"]
                        valid_input = True

            elif search_mode == t("mode_multiple"):
                raw_tics = st.text_input(
                    t("input_multi_label"),
                    placeholder=t("input_multi_placeholder"),
                    help=t("input_multi_help"),
                    key="input_multiple_tics"
                )
                if raw_tics:
                    tokens = [x.strip().replace("TIC", "").strip() for x in raw_tics.split(",") if x.strip()]
                    valid_tokens = [x for x in tokens if x.isdigit()]
                    if valid_tokens:
                        tic_to_run = valid_tokens[0]
                        valid_input = True
                        if is_en:
                            st.info(f"Loaded {len(valid_tokens)} targets. Starting analysis with target TIC {tic_to_run}.")
                        else:
                            st.info(f"تم إدخال {len(valid_tokens)} نجوم. سيتم البدء بالنجم TIC {tic_to_run}.")

            elif search_mode == t("mode_sectors"):
                sectors_to_run = st.multiselect(
                    t("input_sectors_label"),
                    options=list(range(1, 100)),
                    default=[7, 34],
                    key="input_sectors"
                )
                if sectors_to_run:
                    valid_input = True
                    if is_en:
                        st.success(f"✅ Selected {len(sectors_to_run)} sector(s) for survey scan.")
                    else:
                        st.success(f"✅ تم تحديد {len(sectors_to_run)} قطاع للمسح الشامل.")

            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

            if st.button(
                t("btn_start_calibration"),
                type="primary",
                width="stretch",
                disabled=not valid_input,
                key="btn_run_manual_search"
            ):
                if search_mode == t("mode_sectors"):
                    st.session_state.run_mode = "sector"
                    st.session_state.sector_list = sectors_to_run
                    st.session_state.selected_tic = "Survey"
                else:
                    st.session_state.run_mode = "single"
                    st.session_state.selected_tic = tic_to_run

                st.session_state.analysis_stage = "calibration"
                st.rerun()

        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

        # 2. SECONDARY SECTION: Suggested Candidates (Examples)
        st.markdown(f"### ⭐ {t('suggested_stars_title')}")
        st.caption(t("suggested_stars_caption"))

        all_res = get_all_results()
        analyzed_tics = all_res["tic_id"].astype(str).tolist() if not all_res.empty else []

        col1, col2 = st.columns(2)

        sug_title_col = "#0284c7" if is_light else "#38bdf8"
        sug_sub_col = "#64748b" if is_light else "#94a3b8"
        sug_desc_col = "#334155" if is_light else "#cbd5e1"
        badge_done_bg = "#dcfce7" if is_light else "rgba(16,185,129,0.1)"
        badge_done_col = "#15803d" if is_light else "#10b981"
        badge_wait_bg = "#f1f5f9" if is_light else "rgba(148,163,184,0.1)"
        badge_wait_col = "#64748b" if is_light else "#94a3b8"

        with col1:
            c1_data = CURATED_TESS_CATALOG[0]
            is_110_analyzed = "110969638" in analyzed_tics
            badge_text = t("suggested_analyzed_badge") if is_110_analyzed else t("suggested_ready_badge")
            with st.container(border=True):
                st.markdown(
                    f"""
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="font-size:1.6rem;">⭐</span>
                            <div>
                                <div style="font-size:1.15rem; font-weight:800; color:{sug_title_col};">TIC 110969638</div>
                                <div style="font-size:0.8rem; color:{sug_sub_col};">{c1_data['name_en' if is_en else 'name_ar']}</div>
                            </div>
                        </div>
                        <span style="background:{badge_done_bg if is_110_analyzed else badge_wait_bg}; color:{badge_done_col if is_110_analyzed else badge_wait_col}; padding:3px 8px; border-radius:8px; font-size:0.75rem; font-weight:700;">
                            {badge_text}
                        </span>
                    </div>
                    <p style="color:{sug_desc_col}; font-size:0.85rem; line-height:1.5; margin:0 0 12px 0;">
                        {c1_data['desc_en' if is_en else 'desc_ar']}
                    </p>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(t("suggested_analyze_btn"), key="btn_suggest_110", width="stretch", type="secondary"):
                    st.session_state.selected_tic = "110969638"
                    st.session_state.run_mode = "single"
                    st.session_state.analysis_stage = "calibration"
                    st.rerun()

        with col2:
            c2_data = CURATED_TESS_CATALOG[1]
            is_beta_analyzed = "229790952" in analyzed_tics
            badge_text_beta = t("suggested_analyzed_badge") if is_beta_analyzed else t("suggested_ready_badge")
            with st.container(border=True):
                st.markdown(
                    f"""
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="font-size:1.6rem;">⭐</span>
                            <div>
                                <div style="font-size:1.15rem; font-weight:800; color:{sug_title_col};">TIC 229790952</div>
                                <div style="font-size:0.8rem; color:{sug_sub_col};">{c2_data['name_en' if is_en else 'name_ar']}</div>
                            </div>
                        </div>
                        <span style="background:{badge_done_bg if is_beta_analyzed else badge_wait_bg}; color:{badge_done_col if is_beta_analyzed else badge_wait_col}; padding:3px 8px; border-radius:8px; font-size:0.75rem; font-weight:700;">
                            {badge_text_beta}
                        </span>
                    </div>
                    <p style="color:{sug_desc_col}; font-size:0.85rem; line-height:1.5; margin:0 0 12px 0;">
                        {c2_data['desc_en' if is_en else 'desc_ar']}
                    </p>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(t("suggested_analyze_btn"), key="btn_suggest_beta", width="stretch", type="secondary"):
                    st.session_state.selected_tic = "229790952"
                    st.session_state.run_mode = "single"
                    st.session_state.analysis_stage = "calibration"
                    st.rerun()

    # ── STATE 2: CALIBRATION & CONFIRMATION ────────────────────────────
    elif st.session_state.analysis_stage == "calibration":
        st.markdown(f"### {t('calib_target_title')}")

        target_display = f"Sector Survey ({len(st.session_state.sector_list)} Sectors)" if st.session_state.run_mode == "sector" else f"TIC {st.session_state.selected_tic}"

        tgt_bg = "#ffffff" if is_light else "rgba(15,23,42,0.8)"
        tgt_border = "1px solid #cbd5e1" if is_light else "1px solid rgba(56,189,248,0.3)"
        tgt_shadow = "box-shadow: 0 4px 14px rgba(0,0,0,0.04);" if is_light else ""
        tgt_lbl_color = "#475569" if is_light else "#94a3b8"
        tgt_val_color = "#0284c7" if is_light else "#38bdf8"
        calib_bg = "#f0fdf4" if is_light else "rgba(16, 185, 129, 0.05)"
        calib_border = "#86efac" if is_light else "#10b981"
        calib_text = "#1e293b" if is_light else "#cbd5e1"

        st.markdown(
            f"""
            <div style="background:{tgt_bg}; padding:20px; border-radius:12px; border:{tgt_border}; {tgt_shadow} margin-bottom:20px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="color:{tgt_lbl_color}; font-size:0.9rem; font-weight:600; margin-bottom:4px;">{t('calib_target_label')}</div>
                        <div style="color:{tgt_val_color}; font-size:2rem; font-weight:900;">{target_display}</div>
                    </div>
                    <div style="font-size:3rem; opacity:0.8;">🔭</div>
                </div>
            </div>
            """, unsafe_allow_html=True
        )

        st.markdown(f"#### {t('calib_system_status')}")
        st.markdown(
            f"""
            <div style="background:{calib_bg}; padding:16px; border-radius:10px; border-left:4px solid {calib_border}; margin-bottom:20px;">
                <ul style="list-style-type:none; padding:0; margin:0; line-height:1.8; color:{calib_text};">
                    <li>✅ {t('calib_db_conn')}</li>
                    <li>✅ {t('calib_data_stream')}</li>
                    <li>✅ {t('calib_algo_ready')}</li>
                </ul>
            </div>
            """, unsafe_allow_html=True
        )

        with st.expander(t("calib_advanced_expander")):
            _cfg = load_analysis_settings()
            p_col1, p_col2, p_col3 = st.columns(3)
            with p_col1:
                st.session_state.sigma_val = st.slider(t("settings_sigma_threshold"), 2.0, 6.0, float(_cfg["sigma_threshold"]), 0.5)
            with p_col2:
                st.session_state.min_asym_val = st.slider(t("settings_asymmetry_min"), 0.0, 0.5, float(_cfg["asymmetry_min"]), 0.01)
            with p_col3:
                st.session_state.detrend_win = st.slider(t("settings_detrend_window"), 0.5, 5.0, float(_cfg["detrend_window"]), 0.5)

        st.markdown("<br>", unsafe_allow_html=True)
        btn_col1, btn_col2 = st.columns([1.5, 1])

        with btn_col1:
            if st.button(t("btn_launch_astronomical_analysis"), type="primary", width="stretch"):
                st.session_state.analysis_stage = "executing"
                master_container.empty()
                st.rerun()

        with btn_col2:
            if st.button(t("btn_cancel_return"), width="stretch"):
                st.session_state.analysis_stage = "selection"
                st.session_state.selected_tic = None
                st.rerun()

    # ── STATE 3: EXECUTING (Live Telemetry & Auto-Redirect) ────────────
    elif st.session_state.analysis_stage == "executing":
        st.markdown(f"### {t('telemetry_title')}")

        reveal_slot = st.empty()
        phase_bg = "#ffffff" if is_light else "rgba(15,23,42,0.9)"
        phase_shadow = "box-shadow: 0 10px 35px rgba(0,0,0,0.08);" if is_light else "box-shadow: 0 10px 30px rgba(0,0,0,0.3);"
        phase_p_color = "#475569" if is_light else "#94a3b8"

        p1_title_color = "#0284c7" if is_light else "#38bdf8"
        p1_border = "1px solid #7dd3fc" if is_light else "1px solid rgba(56,189,248,0.4)"

        p2_title_color = "#7c3aed" if is_light else "#a78bfa"
        p2_border = "1px solid #c4b5fd" if is_light else "1px solid rgba(167,139,250,0.4)"

        p3_title_color = "#d97706" if is_light else "#fbbf24"
        p3_border = "1px solid #fde68a" if is_light else "1px solid rgba(251,191,36,0.4)"

        p4_title_color = "#dc2626" if is_light else "#f87171"
        p4_border = "1px solid #fca5a5" if is_light else "1px solid rgba(239,68,68,0.4)"

        # Phase 1: Ingestion
        reveal_slot.markdown(
            f"""
            <div style="background:{phase_bg};border:{p1_border};border-radius:14px;padding:30px;text-align:center;{phase_shadow}">
                <div style="font-size:3rem;animation:pulse-cyan 1.5s infinite;">🛰️</div>
                <h3 style="color:{p1_title_color};margin:16px 0 8px 0;">{t('telemetry_phase1_title')}</h3>
                <p style="color:{phase_p_color};font-size:1rem;">{t('telemetry_phase1_desc')}</p>
                <div style="width:70%;height:6px;background:rgba(56,189,248,0.2);margin:20px auto;border-radius:3px;overflow:hidden;">
                    <div style="width:30%;height:100%;background:#38bdf8;animation:pulse-cyan 1s infinite;"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        time.sleep(1.0)

        # Phase 2: Detrending Wave
        reveal_slot.markdown(
            f"""
            <div style="background:{phase_bg};border:{p2_border};border-radius:14px;padding:30px;text-align:center;{phase_shadow}">
                <div style="font-size:3rem;">📉</div>
                <h3 style="color:{p2_title_color};margin:16px 0 8px 0;">{t('telemetry_phase2_title')}</h3>
                <p style="color:{phase_p_color};font-size:1rem;">{t('telemetry_phase2_desc')}</p>
                <div style="width:70%;height:6px;background:rgba(167,139,250,0.2);margin:20px auto;border-radius:3px;overflow:hidden;">
                    <div style="width:60%;height:100%;background:#a78bfa;"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        time.sleep(1.0)

        # Phase 3: Dip Detection
        reveal_slot.markdown(
            f"""
            <div style="background:{phase_bg};border:{p3_border};border-radius:14px;padding:30px;text-align:center;{phase_shadow}">
                <div style="font-size:3rem;">🔍</div>
                <h3 style="color:{p3_title_color};margin:16px 0 8px 0;">{t('telemetry_phase3_title')}</h3>
                <p style="color:{phase_p_color};font-size:1rem;">{t('telemetry_phase3_desc')}</p>
                <div style="width:70%;height:6px;background:rgba(251,191,36,0.2);margin:20px auto;border-radius:3px;overflow:hidden;">
                    <div style="width:85%;height:100%;background:#fbbf24;"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        time.sleep(1.0)

        # Phase 4: Modeling
        reveal_slot.markdown(
            f"""
            <div style="background:{phase_bg};border:{p4_border};border-radius:14px;padding:30px;text-align:center;{phase_shadow}">
                <div style="font-size:3rem;">⚖️</div>
                <h3 style="color:{p4_title_color};margin:16px 0 8px 0;">{t('telemetry_phase4_title')}</h3>
                <p style="color:{phase_p_color};font-size:1rem;">{t('telemetry_phase4_desc')}</p>
                <div style="width:70%;height:6px;background:rgba(239,68,68,0.2);margin:20px auto;border-radius:3px;overflow:hidden;">
                    <div style="width:100%;height:100%;background:#ef4444;"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        time.sleep(1.2)

        # Execute backend analysis and stop the UI flow on failure.
        analysis_result = None
        try:
            if st.session_state.run_mode == "sector" and st.session_state.sector_list:
                sectors_str = ",".join(map(str, st.session_state.sector_list))
                analysis_result = run_sector_survey(sectors_str, max_stars=50)
            else:
                analysis_result = run_single_analysis(st.session_state.selected_tic)
        except Exception as exc:
            analysis_result = {"success": False, "message": str(exc)}

        if not analysis_result or not analysis_result.get("success", False):
            err_msg = (analysis_result or {}).get("message", "Unknown analysis failure")
            st.error(("Analysis failed: " if is_en else "فشل التحليل: ") + str(err_msg))
            st.session_state.analysis_stage = "selection"
            st.stop()

        # Automatically log a single-star scan to persistent history only after success.
        if st.session_state.run_mode != "sector":
            try:
                from lib.scan_history import log_scan, get_star_name
                from lib.data_loader import load_reanalysis_results
                analyzed_id = str(st.session_state.selected_tic)
                star_lbl = get_star_name(analyzed_id, lang="ar")

                st.cache_data.clear()
                df_curr = load_reanalysis_results()
                if not df_curr.empty and "tic_id" in df_curr.columns:
                    df_curr["tic_str"] = df_curr["tic_id"].astype(str).str.replace(".0", "", regex=False)
                    star_rows = df_curr[df_curr["tic_str"] == analyzed_id]
                else:
                    star_rows = pd.DataFrame()

                s_count = int(star_rows["sector"].nunique()) if not star_rows.empty and "sector" in star_rows.columns else 0
                d_count = int((star_rows["dip_found_bool"] == True).sum()) if not star_rows.empty and "dip_found_bool" in star_rows.columns else 0
                c_count = int((star_rows["category_code"] == "strong").sum()) if not star_rows.empty and "category_code" in star_rows.columns else 0

                log_scan(
                    tic_id=analyzed_id,
                    star_name=star_lbl,
                    sectors_count=s_count,
                    dips_count=d_count,
                    comets_count=c_count,
                    status="مكتمل بنجاح ✓"
                )
            except Exception as exc:
                # Analysis succeeded; a history-write failure must not falsify the scientific result.
                st.warning(("Analysis succeeded but history logging failed: " if is_en else "نجح التحليل لكن تعذر حفظ سجل الفحص: ") + str(exc))

        # Phase 5: Success & Auto Redirect
        reveal_slot.markdown(
            f"""
            <div style="background:rgba(16,185,129,0.1);border:1px solid #10b981;border-radius:14px;padding:30px;text-align:center;box-shadow:0 10px 30px rgba(16,185,129,0.2);">
                <div style="font-size:4rem; margin-bottom:10px;">🎉</div>
                <h2 style="color:#34d399;margin:0 0 10px 0;">{t('telemetry_phase5_title')}</h2>
                <p style="color:#cbd5e1;font-size:1.1rem;font-weight:600;">{t('telemetry_phase5_desc')}</p>
                <div style="margin-top: 15px; font-size:2rem; animation: pulse-green 1s infinite;">⏳</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        time.sleep(1.0)

        # Trigger redirect via Session State
        if st.session_state.run_mode != "sector":
            st.session_state.just_analyzed_tic = st.session_state.selected_tic

        st.session_state.analysis_stage = "selection"
        st.switch_page("app_pages/dashboard.py")
