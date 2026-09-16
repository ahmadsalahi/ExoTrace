"""
streamlit_app.py — ExoTrace main entry point.

Multi-page navigation with clean sidebar architecture,
primary 'New Analysis' action, top-bar Dark/Light + Language toggles,
and minimal, zero-clutter layout.
"""

import os
import base64
import streamlit as st
from lib.i18n import (
    t,
    get_lang,
    set_lang,
    get_theme,
    toggle_theme,
    is_rtl,
    inject_rtl_css,
    inject_antifill_script,
)

# ── Logo & Brand Asset Helper ──────────────────────────────────────
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_LOGO_ICON_PATH = os.path.join(_APP_DIR, "assets", "logo_icon.png")
_LOGO_SMALL_PATH = os.path.join(_APP_DIR, "assets", "logo_small.png")


@st.cache_data
def get_logo_base64() -> str:
    """Return base64-encoded logo image for fast zero-latency rendering."""
    if os.path.exists(_LOGO_SMALL_PATH):
        with open(_LOGO_SMALL_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""


# ── Page config (must be first Streamlit call) ─────────────────────
_current_lang = get_lang()
_is_en = (_current_lang == "en")
st.set_page_config(
    page_title="ExoTrace | Exocomet Analysis Observatory" if _is_en else "ExoTrace | مرصد تحليل المذنبات الخارجية",
    page_icon=_LOGO_ICON_PATH if os.path.exists(_LOGO_ICON_PATH) else "🔭",
    layout="wide",
    initial_sidebar_state="auto",
)


# ── Session state initialization ───────────────────────────────────
if "lang" not in st.session_state:
    st.session_state.lang = "ar"
if "app_theme" not in st.session_state:
    st.session_state.app_theme = get_theme()
if "selected_candidate" not in st.session_state:
    st.session_state.selected_candidate = None
if "analysis_history" not in st.session_state:
    st.session_state.analysis_history = []
if "running_analyses" not in st.session_state:
    st.session_state.running_analyses = 0
from lib.settings_manager import load_analysis_settings

if "analysis_settings" not in st.session_state:
    st.session_state.analysis_settings = load_analysis_settings()

# ── RTL/LTR & Theme CSS injection ──────────────────────────────────
inject_rtl_css()

# ── Authentication & Persistent Session Gate ───────────────────────
import time
from lib.auth import (
    verify_login,
    create_session,
    validate_and_refresh_session,
    destroy_session,
)

# 1. Validate session token from URL query params or session_state
token = st.query_params.get("session_id") or st.session_state.get("session_id")
session_expired_notice = False

if token:
    is_valid, user_or_reason = validate_and_refresh_session(token)
    if is_valid:
        st.session_state.authenticated = True
        st.session_state.logged_in_user = user_or_reason
        st.session_state.session_id = token
        st.query_params["session_id"] = token
    else:
        st.session_state.authenticated = False
        st.session_state.logged_in_user = None
        st.session_state.session_id = None
        if "session_id" in st.query_params:
            del st.query_params["session_id"]
        if user_or_reason == "expired":
            session_expired_notice = True
else:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.html("""
    <style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="stSidebarNav"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
    .stApp {
        background: radial-gradient(circle at 50% 18%, #0f1f38 0%, #060a12 100%) !important;
    }
    /* Suppress 'Press Enter to submit form' */
    [data-testid="InputInstructions"],
    div[data-testid="InputInstructions"],
    span[data-testid="InputInstructions"],
    small[data-testid="InputInstructions"],
    .stTextInput [data-testid="InputInstructions"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        max-height: 0 !important;
        min-height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        opacity: 0 !important;
        overflow: hidden !important;
        pointer-events: none !important;
        line-height: 0 !important;
        font-size: 0 !important;
    }
    input::-webkit-credentials-auto-fill-button,
    input::-webkit-strong-password-auto-fill-button,
    input::-webkit-contacts-auto-fill-button,
    input::-webkit-caps-lock-indicator {
        visibility: hidden !important;
        display: none !important;
        pointer-events: none !important;
        position: absolute !important;
        right: -9999px !important;
        width: 0 !important;
        height: 0 !important;
    }
    input::-ms-reveal,
    input::-ms-clear {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
    }
    iframe[height="0"] {
        position: absolute !important;
        height: 0 !important;
        width: 0 !important;
        border: none !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }
    </style>
    """)

    st.markdown("<div style='height: 5vh;'></div>", unsafe_allow_html=True)
    _, login_col, _ = st.columns([1, 1.4, 1])

    with login_col:
        # Language Switcher at Login Gate
        l_col1, l_col2 = st.columns([4, 1], vertical_alignment="center")
        with l_col2:
            lang_label = "EN 🌐" if get_lang() == "ar" else "AR 🌐"
            if st.button(lang_label, key="login_gate_lang_btn", help=t("toggle_lang_tip"), width="stretch"):
                set_lang("en" if get_lang() == "ar" else "ar")
                st.rerun()

        logo_b64 = get_logo_base64()
        logo_html = (
            f'<img src="data:image/png;base64,{logo_b64}" style="width: 105px; height: 105px; border-radius: 22px; box-shadow: 0 0 35px rgba(56, 189, 248, 0.45); border: 2px solid rgba(56, 189, 248, 0.35); object-fit: cover;">'
            if logo_b64
            else '<div style="font-size: 3.6rem; filter: drop-shadow(0 0 25px rgba(56, 189, 248, 0.85));">🔭</div>'
        )
        st.markdown(
            f"""
            <div style="text-align: center; margin-bottom: 24px;">
                <div style="display: flex; justify-content: center; margin-bottom: 14px;">
                    {logo_html}
                </div>
                <h1 style="color: #38bdf8; font-weight: 900; font-size: 2.5rem; margin: 0; letter-spacing: -0.5px;">
                    ExoTrace
                </h1>
                <div style="color: #94a3b8; font-size: 0.95rem; margin-top: 6px; font-weight: 500;">
                    {t('login_subtitle')}
                </div>
                <div style="display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 10px;">
                    <span style="height: 1px; width: 45px; background: rgba(56, 189, 248, 0.4);"></span>
                    <span style="font-size: 0.72rem; color: #38bdf8; letter-spacing: 1.2px; font-family: monospace;">{t('login_mission_tag')}</span>
                    <span style="height: 1px; width: 45px; background: rgba(56, 189, 248, 0.4);"></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if session_expired_notice:
            st.warning(t("login_session_expired"))

        with st.container(border=True):
            st.markdown(f"### 🔐 {t('login_title')}")

            with st.form("login_form", clear_on_submit=False):
                username_input = st.text_input(
                    t("login_username_label"),
                    placeholder=t("login_username_placeholder"),
                )
                password_input = st.text_input(
                    t("login_password_label"),
                    type="password",
                    placeholder=t("login_password_placeholder"),
                )

                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                login_btn = st.form_submit_button(
                    t("login_btn"),
                    type="primary",
                    width="stretch",
                )

                if login_btn:
                    if verify_login(username_input, password_input):
                        new_token = create_session(username_input.strip())
                        cur_theme = get_theme()
                        cur_lang = get_lang()
                        st.session_state.authenticated = True
                        st.session_state.logged_in_user = username_input.strip()
                        st.session_state.session_id = new_token
                        st.query_params["session_id"] = new_token
                        st.query_params["theme"] = cur_theme
                        st.query_params["lang"] = cur_lang
                        from lib.auth import set_session_theme, set_session_lang
                        set_session_theme(new_token, cur_theme)
                        set_session_lang(new_token, cur_lang)
                        st.success(t("login_success"))
                        time.sleep(0.4)
                        st.rerun()
                    else:
                        st.error(t("login_error"))

            inject_antifill_script()

        st.markdown(
            f"""
            <div style="text-align: center; color: #64748b; font-size: 0.78rem; margin-top: 22px;">
                {t('login_footer')}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.stop()



# ── Navigation Definition ──────────────────────────────────────────
page = st.navigation(
    [
        st.Page(
            "app_pages/dashboard.py",
            title=t("nav_dashboard"),
            icon=":material/dashboard:",
            default=True,
        ),
        st.Page(
            "app_pages/new_analysis.py",
            title=t("nav_new_analysis"),
            icon=":material/rocket_launch:",
        ),
        st.Page(
            "app_pages/candidates.py",
            title=t("nav_candidates"),
            icon=":material/star:",
        ),
        st.Page(
            "app_pages/candidate_detail.py",
            title=t("detail_title"),
            icon=":material/travel_explore:",
            visibility="hidden",
        ),
        st.Page(
            "app_pages/history.py",
            title=t("nav_history"),
            icon=":material/history:",
        ),
        st.Page(
            "app_pages/reports.py",
            title=t("nav_reports"),
            icon=":material/description:",
        ),
        st.Page(
            "app_pages/settings.py",
            title=t("nav_settings"),
            icon=":material/settings:",
        ),
    ],
    position="sidebar",
)

# ── Sidebar Brand, Telemetry & Controls ────────────────────────────
with st.sidebar:
    # 1. Brand Header (Logo image alone without redundant ExoTrace text)
    logo_b64 = get_logo_base64()
    if logo_b64:
        st.markdown(
            f"""
            <div style="text-align: center; padding: 4px 0 10px 0;">
                <img src="data:image/png;base64,{logo_b64}" style="width: 105px; height: 105px; border-radius: 22px; box-shadow: 0 0 25px rgba(56, 189, 248, 0.4); border: 1.5px solid rgba(56, 189, 248, 0.3); object-fit: cover; display: inline-block;">
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style="text-align: center; padding: 6px 0;">
                <span style="font-size: 2.2rem; filter: drop-shadow(0 0 12px rgba(56, 189, 248, 0.7));">🔭</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. Live NASA MAST Connection Status
    is_light = (get_theme() == "light")
    badge_bg = "#f0fdf4" if is_light else "rgba(15, 23, 42, 0.6)"
    badge_border = "1px solid #86efac" if is_light else "1px solid rgba(74, 222, 128, 0.2)"
    badge_text_color = "#15803d" if is_light else "#86efac"
    badge_sub_color = "#16a34a" if is_light else "#64748b"
    badge_shadow = "box-shadow: 0 1px 4px rgba(0,0,0,0.03);" if is_light else ""
    st.markdown(
        f"""
        <div style="background: {badge_bg}; border: {badge_border}; {badge_shadow} border-radius: 8px; padding: 6px 10px; margin: 6px 0 10px 0; display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center;">
                <span class="pulse-dot-green"></span>
                <span style="font-size: 0.78rem; color: {badge_text_color}; font-weight: 700;">{t('mast_connected')}</span>
            </div>
            <span style="font-size: 0.7rem; color: {badge_sub_color}; font-family: monospace; font-weight: 600;">TESS LIVE</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3. Log Out Button (Red)
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    st.html("""
    <style>
    .st-key-sidebar_logout_btn button,
    div[class*="st-key-sidebar_logout_btn"] button {
        background-color: #dc2626 !important;
        background-image: none !important;
        border-color: #b91c1c !important;
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    .st-key-sidebar_logout_btn button:hover,
    div[class*="st-key-sidebar_logout_btn"] button:hover {
        background-color: #b91c1c !important;
        border-color: #991b1b !important;
        color: #ffffff !important;
    }
    .st-key-sidebar_logout_btn button:active,
    div[class*="st-key-sidebar_logout_btn"] button:active {
        background-color: #991b1b !important;
    }
    </style>
    """)

    with st.container(key="sidebar_logout_btn"):
        if st.button(
            f"🚪 {t('sign_out')}",
            type="primary",
            width="stretch",
            help=t("sign_out_help"),
        ):
            cur_token = st.session_state.get("session_id") or st.query_params.get("session_id")
            destroy_session(cur_token)
            st.session_state.authenticated = False
            st.session_state.logged_in_user = None
            st.session_state.session_id = None
            if "session_id" in st.query_params:
                del st.query_params["session_id"]
            st.rerun()



# ── Top Bar: Breadcrumb + Global Actions ───────────
with st.container(key="top_header_container"):
    col_brand, col_actions = st.columns([7.5, 2.5], vertical_alignment="center")
    
    with col_brand:
        brand_title_color = "#0284c7" if is_light else "#38bdf8"
        brand_shadow = "box-shadow: 0 2px 8px rgba(2, 132, 199, 0.25);" if is_light else "box-shadow: 0 0 12px rgba(56, 189, 248, 0.5);"
        brand_icon_html = (
            f'<img src="data:image/png;base64,{logo_b64}" style="width: 36px; height: 36px; border-radius: 9px; {brand_shadow} border: 1px solid rgba(56, 189, 248, 0.4); object-fit: cover;">'
            if logo_b64
            else '<span style="font-size: 1.6rem;">🔭</span>'
        )
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 10px;">
                {brand_icon_html}
                <span style="color: {brand_title_color}; font-weight: 800; font-size: 1.35rem; letter-spacing: -0.3px;">ExoTrace</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
    with col_actions:
        # Row 1: Language and Theme buttons side-by-side
        c_lang, c_theme = st.columns([1, 1], vertical_alignment="center")

        with c_lang:
            lang_label = "EN 🌐" if get_lang() == "ar" else "AR 🌐"
            if st.button(lang_label, key="top_bar_lang_btn", width="stretch"):
                set_lang("en" if get_lang() == "ar" else "ar")
                st.rerun()

        with c_theme:
            theme_icon = "☀️" if get_theme() == "dark" else "🌙"
            if st.button(theme_icon, key="top_bar_theme_btn", width="stretch"):
                toggle_theme()
                st.rerun()

        # Row 2: New Analysis button directly under them, matching their width
        if st.button(
            "🚀 " + t("nav_new_analysis"),
            key="top_new_analysis_btn",
            width="stretch",
            type="primary",
        ):
            st.switch_page("app_pages/new_analysis.py")

# ── Run Current Page ───────────────────────────────────────────────
page.run()
