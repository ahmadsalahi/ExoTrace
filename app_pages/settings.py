"""
app_pages/settings.py — System Configuration & Administrative Controls for ExoTrace.

Features:
  - Analysis algorithm parameter defaults.
  - Account security & password management.
  - Survey data registry management and database reset.
  - 100% Bilingual (Arabic & English).
"""

import time
import os
import importlib
import streamlit as st
from lib.i18n import t, inject_antifill_script, get_lang
import lib.scan_history
importlib.reload(lib.scan_history)
from lib.scan_history import get_scan_history, clear_all_scan_data, restore_baseline_data
from lib.data_loader import load_reanalysis_results
from lib.settings_manager import (
    load_analysis_settings,
    save_analysis_settings,
    reset_analysis_settings,
    DEFAULT_ANALYSIS_SETTINGS,
)

is_en = (get_lang() == "en")

# ── Analysis Defaults ──────────────────────────────────────────────
st.subheader(t("settings_analysis_defaults"), anchor=False)
with st.container(border=True):
    if "analysis_settings" not in st.session_state:
        st.session_state.analysis_settings = load_analysis_settings()

    defaults = st.session_state.analysis_settings
    form_ver = st.session_state.get("analysis_settings_ver", 0)

    with st.form(f"settings_form_{form_ver}"):
        col1, col2 = st.columns(2)

        with col1:
            sigma_threshold = st.number_input(
                t("settings_sigma_threshold"),
                value=float(defaults.get("sigma_threshold", 3.0)),
                min_value=1.0,
                max_value=10.0,
                step=0.5,
                key=f"st_sigma_{form_ver}",
            )
            min_duration = st.number_input(
                t("settings_min_duration"),
                value=float(defaults.get("min_duration", 1.0)),
                min_value=0.1,
                max_value=12.0,
                step=0.5,
                key=f"st_min_dur_{form_ver}",
            )
            detrend_window = st.number_input(
                t("settings_detrend_window"),
                value=float(defaults.get("detrend_window", 2.0)),
                min_value=0.5,
                max_value=10.0,
                step=0.5,
                key=f"st_detrend_{form_ver}",
            )

        with col2:
            max_duration = st.number_input(
                t("settings_max_duration"),
                value=float(defaults.get("max_duration", 24.0)),
                min_value=1.0,
                max_value=72.0,
                step=1.0,
                key=f"st_max_dur_{form_ver}",
            )
            asymmetry_min = st.number_input(
                t("settings_asymmetry_min"),
                value=float(defaults.get("asymmetry_min", 0.05)),
                min_value=0.0,
                max_value=1.0,
                step=0.01,
                format="%.2f",
                key=f"st_asym_{form_ver}",
            )

        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
        col_b1, col_b2, _ = st.columns([1.5, 2.2, 3.0])
        with col_b1:
            save_clicked = st.form_submit_button(
                t("btn_save"),
                type="primary",
                icon=":material/save:",
                width="stretch",
            )
        with col_b2:
            reset_clicked = st.form_submit_button(
                t("settings_reset"),
                icon=":material/restart_alt:",
                width="stretch",
            )

        if save_clicked:
            new_settings = {
                "sigma_threshold": float(sigma_threshold),
                "min_duration": float(min_duration),
                "max_duration": float(max_duration),
                "asymmetry_min": float(asymmetry_min),
                "detrend_window": float(detrend_window),
            }
            save_analysis_settings(new_settings)
            st.session_state.analysis_settings = new_settings
            st.toast(t("settings_saved_toast"), icon="✅")
            st.success(t("settings_saved_success"))

        if reset_clicked:
            reset_analysis_settings()
            st.session_state.analysis_settings = DEFAULT_ANALYSIS_SETTINGS.copy()
            st.session_state.analysis_settings_ver = form_ver + 1
            st.toast(t("settings_restored_toast"), icon="ℹ️")
            st.rerun()


# ── Security & Password Management ──────────────────────────────────
st.subheader(f"🔐 {t('settings_security_title')}", anchor=False)
with st.container(border=True):
    st.caption(t("settings_security_caption"))
    with st.form("change_password_form", clear_on_submit=True):
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            curr_pw = st.text_input(t("settings_curr_password"), type="password", placeholder="••••••••")
        with col_p2:
            new_pw = st.text_input(t("settings_new_password"), type="password", placeholder="••••••••")
        with col_p3:
            confirm_pw = st.text_input(t("settings_confirm_password"), type="password", placeholder="••••••••")

        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
        change_pw_btn = st.form_submit_button(
            t("settings_save_password_btn"),
            type="primary",
            icon=":material/lock_reset:",
        )

        if change_pw_btn:
            if not curr_pw or not new_pw or not confirm_pw:
                st.error("Please fill in all password fields." if is_en else "يرجى ملء جميع حقول كلمة المرور.")
            elif new_pw != confirm_pw:
                st.error("Passwords do not match." if is_en else "كلمتا المرور غير متطابقتين.")
            else:
                from lib.auth import change_password
                ok, msg = change_password(curr_pw, new_pw)
                if ok:
                    msg_txt = "Password updated successfully!" if is_en else msg
                    st.success(msg_txt)
                    time.sleep(1)
                    st.rerun()
                else:
                    msg_txt = "Current password is incorrect." if is_en else msg
                    st.error(msg_txt)

    inject_antifill_script()


# ── Data & Scan Results Management ──────────────────────────────────
st.subheader(f"💾 {t('settings_data_mgmt_title')}", anchor=False)
with st.container(border=True):
    history_records = get_scan_history()
    reanalysis_df = load_reanalysis_results()

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        val_stars = f"{len(history_records)} {'Stars' if is_en else 'نجوم'}"
        st.metric(t("settings_data_scanned_stars"), val_stars)
    with col_s2:
        val_recs = f"{len(reanalysis_df)} {'Records' if is_en else 'سجل'}"
        st.metric(t("settings_data_logged_records"), val_recs)

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # Red styling for danger delete button
    st.html("""
    <style>
    .st-key-danger_delete_btn button,
    div[class*="st-key-danger_delete_btn"] button,
    .st-key-dialog_danger_btn button,
    div[class*="st-key-dialog_danger_btn"] button {
        background-color: #dc2626 !important;
        background-image: none !important;
        border-color: #b91c1c !important;
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    .st-key-danger_delete_btn button:hover,
    div[class*="st-key-danger_delete_btn"] button:hover,
    .st-key-dialog_danger_btn button:hover,
    div[class*="st-key-dialog_danger_btn"] button:hover {
        background-color: #b91c1c !important;
        border-color: #991b1b !important;
        color: #ffffff !important;
    }
    .st-key-danger_delete_btn button:active,
    div[class*="st-key-danger_delete_btn"] button:active,
    .st-key-dialog_danger_btn button:active,
    div[class*="st-key-dialog_danger_btn"] button:active {
        background-color: #991b1b !important;
    }
    </style>
    """)

    @st.dialog(t("settings_purge_dialog_title"))
    def confirm_reset_dialog():
        st.warning(t("settings_purge_dialog_warning"))
        del_lc = st.checkbox(t("settings_purge_del_lc"), value=False)
        d_col1, d_col2 = st.columns(2)
        with d_col1:
            with st.container(key="dialog_danger_btn"):
                if st.button(t("settings_purge_confirm_btn"), type="primary", width="stretch", icon=":material/delete_forever:"):
                    clear_all_scan_data()
                    if del_lc:
                        _p_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        lc_p = os.path.join(_p_root, "data", "lightcurves")
                        if os.path.exists(lc_p):
                            for f in os.listdir(lc_p):
                                if f.endswith(".csv"):
                                    try:
                                        os.remove(os.path.join(lc_p, f))
                                    except Exception:
                                        pass
                    st.cache_data.clear()
                    st.session_state.analysis_history = []
                    st.session_state.running_analyses = 0
                    st.session_state.pop("dashboard_focused_tic", None)
                    st.session_state.pop("just_analyzed_tic", None)
                    st.session_state.spotlight_index = 0
                    st.success(t("settings_purge_success"))
                    time.sleep(1)
                    st.rerun()
        with d_col2:
            if st.button(t("settings_purge_cancel_btn"), width="stretch"):
                st.rerun()

    with st.container(key="danger_delete_btn"):
        if st.button(
            t("settings_purge_btn"),
            type="primary",
            width="stretch",
            icon=":material/delete_sweep:",
            help=t("settings_purge_help"),
        ):
            confirm_reset_dialog()
