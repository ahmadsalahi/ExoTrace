"""
lib/i18n.py — Centralized internationalization, theme toggling, and RTL styling for ExoTrace.

Uses 'IBM Plex Sans Arabic' for maximum crispness, readability, and scientific UI quality.
Supports Arabic (RTL) and English (LTR).
Manages Dark/Light mode theme state.
Responsive mobile button rules (collapses text to icons on mobile).
Provides flawless sidebar collapsing with zero lines or artifacts when closed.
"""

import json
import os
import streamlit as st

_I18N_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "i18n")


@st.cache_data
def _load_translations(lang: str) -> dict:
    """Load and cache translation JSON for a given language code."""
    path = os.path.join(_I18N_DIR, f"{lang}.json")
    if not os.path.exists(path):
        path = os.path.join(_I18N_DIR, "en.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _ensure_state():
    """Ensure language and theme are initialized in session state with persistence."""
    token = st.query_params.get("session_id") or st.session_state.get("session_id")

    # 1. Initialize Language with 3-tier persistence
    if "lang" not in st.session_state:
        url_lang = st.query_params.get("lang")
        if url_lang in ("ar", "en"):
            st.session_state.lang = url_lang
        else:
            saved_lang = None
            if token:
                try:
                    from lib.auth import get_session_lang
                    saved_lang = get_session_lang(token)
                except Exception:
                    pass
            if saved_lang in ("ar", "en"):
                st.session_state.lang = saved_lang
                st.query_params["lang"] = saved_lang
            else:
                st.session_state.lang = "ar"

    # 2. Initialize Theme with 3-tier persistence
    if "app_theme" not in st.session_state:
        url_theme = st.query_params.get("theme")
        if url_theme in ("light", "dark"):
            st.session_state.app_theme = url_theme
        else:
            saved_theme = None
            if token:
                try:
                    from lib.auth import get_session_theme
                    saved_theme = get_session_theme(token)
                except Exception:
                    pass
            if saved_theme in ("light", "dark"):
                st.session_state.app_theme = saved_theme
                st.query_params["theme"] = saved_theme
            else:
                st.session_state.app_theme = "dark"


def get_lang() -> str:
    """Return current language code ('ar' or 'en')."""
    _ensure_state()
    url_lang = st.query_params.get("lang")
    if url_lang in ("ar", "en") and url_lang != st.session_state.lang:
        st.session_state.lang = url_lang
    return st.session_state.lang


def set_lang(lang_code: str):
    """Set language in session state and persist across refreshes."""
    _ensure_state()
    if lang_code in ("ar", "en"):
        st.session_state.lang = lang_code
        st.query_params["lang"] = lang_code
        token = st.query_params.get("session_id") or st.session_state.get("session_id")
        if token:
            try:
                from lib.auth import set_session_lang
                set_session_lang(token, lang_code)
            except Exception:
                pass


def get_theme() -> str:
    """Return current theme ('dark' or 'light')."""
    _ensure_state()
    url_theme = st.query_params.get("theme")
    if url_theme in ("light", "dark") and url_theme != st.session_state.app_theme:
        st.session_state.app_theme = url_theme
    return st.session_state.app_theme


def toggle_theme():
    """Toggle between dark and light mode and persist immediately."""
    _ensure_state()
    new_theme = "light" if st.session_state.app_theme == "dark" else "dark"
    st.session_state.app_theme = new_theme
    st.query_params["theme"] = new_theme
    token = st.query_params.get("session_id") or st.session_state.get("session_id")
    if token:
        try:
            from lib.auth import set_session_theme
            set_session_theme(token, new_theme)
        except Exception:
            pass


def is_rtl() -> bool:
    """Return True if current language is right-to-left."""
    return get_lang() == "ar"


def t(key: str, **kwargs) -> str:
    """
    Get translated string for the given key.
    Falls back to English, then to the key itself.
    """
    lang = get_lang()
    translations = _load_translations(lang)

    text = translations.get(key)
    if text is None and lang != "en":
        en_translations = _load_translations("en")
        text = en_translations.get(key)
    if text is None:
        return key

    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass

    return text


def get_direction() -> str:
    """Return 'rtl' or 'ltr' based on current language."""
    return "rtl" if is_rtl() else "ltr"


def inject_rtl_css():
    """Inject comprehensive CSS for RTL, IBM Plex Sans Arabic, Light/Dark mode, and mobile rules."""
    rtl_flag = is_rtl()
    theme = get_theme()
    is_light = (theme == "light")

    direction = "rtl" if rtl_flag else "ltr"
    align = "right" if rtl_flag else "left"

    # Theme palettes
    if is_light:
        bg_main = "#e9edf4"
        bg_card = "#ffffff"
        text_main = "#0f172a"
        text_sub = "#475569"
        border_col = "#cbd5e1"
        border_card = "#cbd5e1"
        sidebar_bg = "#f1f5f9"
        sidebar_border = "#cbd5e1"
        card_shadow = "box-shadow: 0 3px 12px rgba(15, 23, 42, 0.05) !important;"

        # Light Mode Contrast Overrides
        kpi_dips_color = "#b45309"
        kpi_strong_color = "#dc2626"
        kpi_review_color = "#7c3aed"
        kpi_star_color = "#0f172a"

        nav_inactive_color = "#1e293b"
        nav_hover_bg = "#e2e8f0"
        nav_hover_color = "#0284c7"
        nav_active_bg = "linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%)"
        nav_active_border = "#0284c7"
        nav_active_color = "#0369a1"
        nav_active_shadow = "box-shadow: 0 2px 10px rgba(2, 132, 199, 0.15) !important;"

        hamburger_bg = "#ffffff"
        hamburger_border = "#cbd5e1"
        hamburger_icon = "#0284c7"
        hamburger_shadow = "0 2px 10px rgba(0, 0, 0, 0.08)"

        collapse_btn_bg = "#ffffff"
        collapse_btn_border = "#cbd5e1"
        collapse_btn_arrow = "#0284c7"
    else:
        bg_main = "radial-gradient(circle at 80% 20%, rgba(14, 165, 233, 0.04) 0%, transparent 40%), radial-gradient(circle at 20% 80%, rgba(168, 85, 247, 0.04) 0%, transparent 50%), #080c14"
        bg_card = "rgba(15, 23, 42, 0.75)"
        text_main = "#f8fafc"
        text_sub = "#94a3b8"
        border_col = "rgba(56, 189, 248, 0.15)"
        border_card = "rgba(56, 189, 248, 0.15)"
        sidebar_bg = "linear-gradient(180deg, #070b14 0%, #0b1120 100%)"
        sidebar_border = "rgba(56, 189, 248, 0.12)"
        card_shadow = "box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4) !important;"

        # Dark Mode Colors
        kpi_dips_color = "#fbbf24"
        kpi_strong_color = "#ef4444"
        kpi_review_color = "#a78bfa"
        kpi_star_color = text_main

        nav_inactive_color = text_main
        nav_hover_bg = "rgba(56, 189, 248, 0.12)"
        nav_hover_color = "#38bdf8"
        nav_active_bg = "linear-gradient(90deg, rgba(14, 165, 233, 0.2) 0%, rgba(99, 102, 241, 0.1) 100%)"
        nav_active_border = "rgba(56, 189, 248, 0.4)"
        nav_active_color = "#38bdf8"
        nav_active_shadow = "box-shadow: 0 0 15px rgba(14, 165, 233, 0.2) !important;"

        hamburger_bg = "rgba(15, 23, 42, 0.9)"
        hamburger_border = "rgba(56, 189, 248, 0.4)"
        hamburger_icon = "#38bdf8"
        hamburger_shadow = "0 4px 15px rgba(0, 0, 0, 0.5)"

        collapse_btn_bg = "rgba(56, 189, 248, 0.12)"
        collapse_btn_border = "rgba(56, 189, 248, 0.35)"
        collapse_btn_arrow = "#38bdf8"

    css = f"""<style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

        /* High-Definition Typography & Global Direction */
        html, body, [class*="css"], .stApp {{
            font-family: 'IBM Plex Sans Arabic', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
            direction: {direction};
            text-align: {align};
            -webkit-font-smoothing: antialiased !important;
            -moz-osx-font-smoothing: grayscale !important;
            text-rendering: optimizeLegibility !important;
        }}

        /* App Background & Base Colors */
        .stApp {{
            background: {bg_main} !important;
            color: {text_main} !important;
        }}

        /* Clean Numbers & Code LTR */
        code, pre, .stMetric [data-testid="stMetricValue"], [data-testid="stMetricDelta"] {{
            font-family: 'JetBrains Mono', monospace !important;
            direction: ltr !important;
            unicode-bidi: embed;
        }}

        /* ══════════════════════════════════════════════════════════════════
           SIDEBAR ARCHITECTURE (Desktop Pinned + Mobile Drawer + Hamburger)
           ══════════════════════════════════════════════════════════════════ */

        /* 1. Header & Toolbar: Completely Hidden */
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        .stAppDeployButton,
        [data-testid="stMainMenu"] {{
            display: none !important;
            visibility: hidden !important;
        }}

        /* 3. The Hamburger Menu Button (Streamlit 1.63 stExpandSidebarButton) */
        [data-testid="stExpandSidebarButton"] {{
            position: fixed !important;
            top: 12px !important;
            {'right: 14px !important; left: auto !important;' if rtl_flag else 'left: 14px !important; right: auto !important;'}
            z-index: 9999999 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            width: 42px !important;
            height: 42px !important;
            min-width: 42px !important;
            min-height: 42px !important;
            background: {hamburger_bg} !important;
            border: 1px solid {hamburger_border} !important;
            border-radius: 10px !important;
            box-shadow: {hamburger_shadow} !important;
            cursor: pointer !important;
            pointer-events: auto !important;
            transition: all 0.2s ease !important;
        }}
        [data-testid="stExpandSidebarButton"]:hover {{
            background: {'#f1f5f9' if is_light else 'rgba(56, 189, 248, 0.25)'} !important;
            border-color: {'#0284c7' if is_light else '#38bdf8'} !important;
            transform: scale(1.05);
        }}
        /* Hide default Streamlit SVG chevron */
        [data-testid="stExpandSidebarButton"] svg,
        [data-testid="stExpandSidebarButton"] span {{
            display: none !important;
        }}
        /* Insert clear 3-line Hamburger Menu Icon ☰ */
        [data-testid="stExpandSidebarButton"]::before {{
            content: "☰" !important;
            font-size: 24px !important;
            line-height: 1 !important;
            color: {hamburger_icon} !important;
            font-weight: 700 !important;
            display: block !important;
            pointer-events: none !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        }}

        /* 4. When Sidebar is COLLAPSED (Mobile or Desktop): Completely zero out to eliminate lines & overlaps */
        [data-testid="stSidebar"][aria-expanded="false"] {{
            display: none !important;
            width: 0 !important;
            min-width: 0 !important;
            max-width: 0 !important;
            border: none !important;
            box-shadow: none !important;
            transform: none !important;
            pointer-events: none !important;
        }}

        /* 5. Close Button Inside the Sidebar Header (stSidebarCollapseButton) */
        [data-testid="stSidebarCollapseButton"] {{
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            opacity: 1 !important;
            visibility: visible !important;
        }}
        [data-testid="stSidebarCollapseButton"] button {{
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            width: 36px !important;
            height: 36px !important;
            min-width: 36px !important;
            min-height: 36px !important;
            border-radius: 8px !important;
            background: {collapse_btn_bg} !important;
            border: 1px solid {collapse_btn_border} !important;
            cursor: pointer !important;
            pointer-events: auto !important;
            opacity: 1 !important;
            visibility: visible !important;
            transition: all 0.2s ease !important;
        }}
        [data-testid="stSidebarCollapseButton"] button:hover {{
            background: {'#e2e8f0' if is_light else 'rgba(56, 189, 248, 0.28)'} !important;
            border-color: {'#0284c7' if is_light else '#38bdf8'} !important;
            transform: scale(1.05);
        }}
        [data-testid="stSidebarCollapseButton"] button svg,
        [data-testid="stSidebarCollapseButton"] button span {{
            display: none !important;
        }}
        [data-testid="stSidebarCollapseButton"] button::before {{
            content: "{'»' if rtl_flag else '«'}" !important;
            font-size: 20px !important;
            line-height: 1 !important;
            color: {collapse_btn_arrow} !important;
            font-weight: 700 !important;
            display: block !important;
            pointer-events: none !important;
            font-family: sans-serif !important;
        }}

        /* 6. Desktop Sidebar: Pinned to the side when open */
        @media (min-width: 769px) {{
            [data-testid="stSidebar"][aria-expanded="true"] {{
                background: {sidebar_bg} !important;
                {'border-left: 1px solid ' + sidebar_border + ' !important; border-right: none !important;' if rtl_flag else 'border-right: 1px solid ' + sidebar_border + ' !important; border-left: none !important;'}
                box-shadow: {card_shadow} !important;
            }}
        }}

        /* 7. Mobile Sidebar: Modern overlay drawer sliding in when open */
        @media (max-width: 768px) {{
            [data-testid="stSidebar"][aria-expanded="true"] {{
                position: fixed !important;
                top: 0 !important;
                bottom: 0 !important;
                {'right: 0 !important; left: auto !important;' if rtl_flag else 'left: 0 !important; right: auto !important;'}
                width: 85vw !important;
                max-width: 320px !important;
                z-index: 1000005 !important;
                background: {sidebar_bg} !important;
                {'border-left: 1px solid ' + sidebar_border + ' !important; border-right: none !important;' if rtl_flag else 'border-right: 1px solid ' + sidebar_border + ' !important; border-left: none !important;'}
                box-shadow: 0 0 50px rgba(0, 0, 0, 0.5) !important;
                display: flex !important;
                flex-direction: column !important;
                transform: none !important;
            }}
        }}

        /* Reorder Sidebar: Place Brand/Status ABOVE Navigation Links */
        [data-testid="stSidebar"] > div:first-child {{
            display: flex !important;
            flex-direction: column !important;
        }}
        [data-testid="stSidebarUserContent"] {{
            order: 1 !important;
            padding-bottom: 0.5rem !important;
        }}
        [data-testid="stSidebarNav"] {{
            order: 2 !important;
            border-top: 1px solid {sidebar_border} !important;
            padding-top: 1rem !important;
            margin-top: 0.5rem !important;
        }}

        /* Sidebar Navigation Items - Flawless Contrast in Both Light & Dark Modes */
        [data-testid="stSidebarNav"] ul {{
            padding: 0 !important;
            list-style: none !important;
        }}
        [data-testid="stSidebarNav"] li a {{
            border-radius: 10px !important;
            margin-bottom: 4px !important;
            transition: all 0.2s ease-in-out !important;
            padding: 10px 14px !important;
            border: 1px solid transparent !important;
            color: {nav_inactive_color} !important;
            font-weight: 600 !important;
        }}
        [data-testid="stSidebarNav"] li a span,
        [data-testid="stSidebarNav"] li a svg,
        [data-testid="stSidebarNavItems"] li a span {{
            color: {nav_inactive_color} !important;
            font-weight: 600 !important;
            transition: color 0.2s ease-in-out !important;
        }}
        [data-testid="stSidebarNav"] li a:hover {{
            background: {nav_hover_bg} !important;
            border-color: {border_card} !important;
            transform: translateX({'-4px' if rtl_flag else '4px'});
        }}
        [data-testid="stSidebarNav"] li a:hover span,
        [data-testid="stSidebarNav"] li a:hover svg {{
            color: {nav_hover_color} !important;
        }}
        [data-testid="stSidebarNav"] li a[aria-current="page"],
        [data-testid="stSidebarNav"] li a[aria-current="page"]:hover {{
            background: {nav_active_bg} !important;
            border: 1.5px solid {nav_active_border} !important;
            {nav_active_shadow}
            font-weight: 800 !important;
        }}
        [data-testid="stSidebarNav"] li a[aria-current="page"] span,
        [data-testid="stSidebarNav"] li a[aria-current="page"] svg,
        [data-testid="stSidebarNav"] li a[aria-current="page"]:hover span,
        [data-testid="stSidebarNav"] li a[aria-current="page"]:hover svg {{
            color: {nav_active_color} !important;
            font-weight: 800 !important;
        }}

        /* Containers & Cards (Adapted for Light & Dark Mode) */
        [data-testid="stVerticalBlock"] > div[data-testid="stContainer"][border="true"] {{
            background: {bg_card} !important;
            border: 1px solid {border_card} !important;
            border-radius: 14px !important;
            {card_shadow}
            transition: transform 0.2s ease, border-color 0.2s ease;
        }}

        /* Interactive Clickable KPI Metric Cards Hover */
        [data-testid="stVerticalBlock"] > div[data-testid="stContainer"][border="true"]:hover {{
            border-color: {'#0284c7' if is_light else 'rgba(56, 189, 248, 0.5)'} !important;
            transform: translateY(-2px);
        }}

        /* Pulse Animations for Live Telemetry */
        @keyframes pulse-green {{
            0% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(74, 222, 128, 0.7); }}
            70% {{ transform: scale(1); box-shadow: 0 0 0 6px rgba(74, 222, 128, 0); }}
            100% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(74, 222, 128, 0); }}
        }}

        .pulse-dot-green {{
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: {'#16a34a' if is_light else '#4ade80'};
            animation: pulse-green 2s infinite;
            margin-left: 6px;
            margin-right: 6px;
        }}

        .pulse-dot-cyan {{
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #38bdf8;
            animation: pulse-cyan 2s infinite;
            margin-left: 6px;
            margin-right: 6px;
        }}

        /* Primary Buttons */
        .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, #0284c7 0%, #0369a1 50%, #075985 100%) !important;
            border: 1px solid rgba(56, 189, 248, 0.5) !important;
            box-shadow: 0 4px 15px rgba(2, 132, 199, 0.35) !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            color: #ffffff !important;
            transition: all 0.25s ease-in-out !important;
        }}
        .stButton > button[kind="primary"]:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 25px rgba(56, 189, 248, 0.5) !important;
            border-color: #38bdf8 !important;
        }}

        /* KPI Full-Card Buttons */
        [class*="st-key-kpi_btn_"] button {{
            height: 110px !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
            align-items: flex-start !important;
            padding: 16px !important;
            background: {bg_card} !important;
            border: 1px solid {border_card} !important;
            border-radius: 14px !important;
            {card_shadow}
            transition: transform 0.2s ease, border-color 0.2s ease !important;
        }}
        [class*="st-key-kpi_btn_"] button:hover {{
            border-color: {'#0284c7' if is_light else 'rgba(56, 189, 248, 0.4)'} !important;
            transform: translateY(-3px) !important;
            background: {bg_card} !important;
            color: inherit !important;
        }}
        [class*="st-key-kpi_btn_"] button p {{
            text-align: {align} !important;
            margin: 0 !important;
            font-size: 0.9rem !important;
            color: {text_sub} !important;
            font-weight: 600 !important;
        }}
        [class*="st-key-kpi_btn_"] button strong {{
            display: block !important;
            font-size: 1.5rem !important;
            margin-top: 6px !important;
            font-weight: 800 !important;
        }}
        [class*="st-key-kpi_btn_strong"] button strong {{
            color: {kpi_strong_color} !important;
        }}
        [class*="st-key-kpi_btn_dips"] button strong {{
            color: {kpi_dips_color} !important;
        }}
        [class*="st-key-kpi_btn_review"] button strong {{
            color: {kpi_review_color} !important;
        }}
        [class*="st-key-kpi_btn_star"] button strong {{
            color: {kpi_star_color} !important;
        }}

        /* Light Mode Specific Enhancements */
        {f'''
        /* 0. Primary Buttons: Force pure white text, icons, and labels */
        .stButton button[kind="primary"],
        .stButton button[data-testid="baseButton-primary"],
        [data-testid="baseButton-primary"],
        button[kind="primary"],
        button[data-testid="baseButton-primary"],
        div[class*="st-key-"] button[kind="primary"],
        div[class*="st-key-"] button[data-testid="baseButton-primary"] {{
            background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
            background-color: #0284c7 !important;
            border: 1px solid rgba(56, 189, 248, 0.4) !important;
            color: #ffffff !important;
            box-shadow: 0 3px 12px rgba(2, 132, 199, 0.3) !important;
        }}
        .stButton button[kind="primary"] *,
        .stButton button[data-testid="baseButton-primary"] *,
        [data-testid="baseButton-primary"] *,
        button[kind="primary"] *,
        button[data-testid="baseButton-primary"] *,
        div[class*="st-key-"] button[kind="primary"] *,
        div[class*="st-key-"] button[data-testid="baseButton-primary"] * {{
            color: #ffffff !important;
            fill: #ffffff !important;
            stroke: #ffffff !important;
        }}

        /* 1. All Secondary & Default Buttons (including inside forms, columns, tooltips) */
        .stButton button:not([kind="primary"]):not([data-testid="baseButton-primary"]),
        .stFormSubmitButton button:not([kind="primary"]):not([data-testid="baseButton-primary"]),
        [data-testid="baseButton-secondary"],
        button[kind="secondary"],
        [data-testid="stTooltipHoverTarget"] button:not([kind="primary"]):not([data-testid="baseButton-primary"]),
        div[class*="st-key-"] button:not([kind="primary"]):not([data-testid="baseButton-primary"]) {{
            background: #ffffff !important;
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            color: #0f172a !important;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04) !important;
        }}
        .stButton button:not([kind="primary"]):not([data-testid="baseButton-primary"]):hover,
        .stFormSubmitButton button:not([kind="primary"]):not([data-testid="baseButton-primary"]):hover,
        [data-testid="baseButton-secondary"]:hover,
        button[kind="secondary"]:hover,
        [data-testid="stTooltipHoverTarget"] button:not([kind="primary"]):not([data-testid="baseButton-primary"]):hover,
        div[class*="st-key-"] button:not([kind="primary"]):not([data-testid="baseButton-primary"]):hover {{
            border-color: #0284c7 !important;
            color: #0284c7 !important;
            background: #f1f5f9 !important;
            background-color: #f1f5f9 !important;
            box-shadow: 0 2px 6px rgba(2, 132, 199, 0.12) !important;
        }}

        /* 2. Disabled Buttons */
        button:disabled,
        button[disabled],
        .stButton button:disabled,
        [data-testid="baseButton-secondary"]:disabled,
        .stFormSubmitButton button:disabled {{
            background: #f1f5f9 !important;
            background-color: #f1f5f9 !important;
            border: 1px solid #e2e8f0 !important;
            color: #94a3b8 !important;
            opacity: 0.65 !important;
            cursor: not-allowed !important;
            box-shadow: none !important;
        }}

        /* 3. Number Input Stepper (+ / -) Buttons */
        .stNumberInput button,
        div[data-testid="stNumberInput"] button,
        [data-testid="stNumberInputStepUp"],
        [data-testid="stNumberInputStepDown"] {{
            background: #f1f5f9 !important;
            background-color: #f1f5f9 !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
        }}
        .stNumberInput button:hover,
        div[data-testid="stNumberInput"] button:hover,
        [data-testid="stNumberInputStepUp"]:hover,
        [data-testid="stNumberInputStepDown"]:hover {{
            background: #e2e8f0 !important;
            background-color: #e2e8f0 !important;
            color: #0284c7 !important;
            border-color: #94a3b8 !important;
        }}
        .stNumberInput button svg,
        [data-testid="stNumberInputStepUp"] svg,
        [data-testid="stNumberInputStepDown"] svg {{
            fill: #334155 !important;
            color: #334155 !important;
            stroke: #334155 !important;
        }}

        /* 4. Password Visibility Toggle (Eye Icon) */
        .stTextInput button,
        .stTextInput button[aria-label*="password" i],
        .stTextInput button[aria-label*="Show" i],
        .stTextInput button[aria-label*="Hide" i],
        div[data-baseweb="input"] button {{
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }}
        .stTextInput button svg,
        div[data-baseweb="input"] button svg {{
            fill: #475569 !important;
            color: #475569 !important;
            stroke: #475569 !important;
        }}
        .stTextInput button:hover svg,
        div[data-baseweb="input"] button:hover svg {{
            fill: #0284c7 !important;
            color: #0284c7 !important;
        }}

        /* 5. Inputs, Numbers, Textareas */
        .stTextInput input,
        .stNumberInput input,
        .stTextArea textarea {{
            background-color: #ffffff !important;
            background: #ffffff !important;
            color: #0f172a !important;
            border-color: #cbd5e1 !important;
        }}
        .stTextInput input:focus,
        .stNumberInput input:focus,
        .stTextArea textarea:focus {{
            border-color: #0284c7 !important;
            box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.2) !important;
        }}

        /* 6. BaseWeb Selectbox & Dropdowns */
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        div[data-baseweb="select"] > div,
        div[data-baseweb="select"] input {{
            background-color: #ffffff !important;
            background: #ffffff !important;
            color: #0f172a !important;
            border-color: #cbd5e1 !important;
        }}
        div[data-baseweb="select"] span,
        div[data-baseweb="select"] div {{
            color: #0f172a !important;
        }}
        div[data-baseweb="select"] svg {{
            fill: #475569 !important;
            color: #475569 !important;
        }}
        div[data-baseweb="popover"],
        div[data-baseweb="menu"],
        ul[data-baseweb="menu"] {{
            background-color: #ffffff !important;
            background: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
            box-shadow: 0 6px 24px rgba(15, 23, 42, 0.12) !important;
            border-radius: 10px !important;
        }}
        li[data-baseweb="menu-item"] {{
            background-color: #ffffff !important;
            background: #ffffff !important;
            color: #0f172a !important;
        }}
        li[data-baseweb="menu-item"]:hover,
        li[data-baseweb="menu-item"][aria-selected="true"] {{
            background-color: #f1f5f9 !important;
            background: #f1f5f9 !important;
            color: #0284c7 !important;
        }}

        /* 7. Segmented Controls */
        div[data-testid="stSegmentedControl"] {{
            background: #ffffff !important;
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04) !important;
            padding: 3px !important;
            border-radius: 10px !important;
        }}
        div[data-testid="stSegmentedControl"] button {{
            background: transparent !important;
            background-color: transparent !important;
            color: #475569 !important;
            border: none !important;
            box-shadow: none !important;
            font-weight: 600 !important;
            transition: all 0.15s ease !important;
        }}
        div[data-testid="stSegmentedControl"] button[aria-checked="false"],
        div[data-testid="stSegmentedControl"] button:not([aria-checked="true"]) {{
            background: transparent !important;
            background-color: transparent !important;
            color: #475569 !important;
        }}
        div[data-testid="stSegmentedControl"] button[aria-checked="true"] {{
            background: #0284c7 !important;
            background-color: #0284c7 !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            box-shadow: 0 1px 4px rgba(2, 132, 199, 0.3) !important;
            border-radius: 8px !important;
        }}
        div[data-testid="stSegmentedControl"] button:hover {{
            color: #0284c7 !important;
            background: #f1f5f9 !important;
            background-color: #f1f5f9 !important;
        }}
        div[data-testid="stSegmentedControl"] button[aria-checked="true"]:hover {{
            background: #0369a1 !important;
            background-color: #0369a1 !important;
            color: #ffffff !important;
        }}

        /* 8. Text & Headings */
        h1, h2, h3, h4, h5, h6 {{
            color: #0f172a !important;
        }}
        p, label, span[data-testid="stWidgetLabel"] p {{
            color: #334155 !important;
        }}
        [data-testid="stMetricValue"] {{
            color: #0f172a !important;
            font-weight: 800 !important;
            font-size: 1.55rem !important;
            white-space: normal !important;
            word-break: normal !important;
            line-height: 1.25 !important;
        }}
        [data-testid="stMetricLabel"] p {{
            color: #475569 !important;
            font-weight: 600 !important;
        }}

        /* 9. Dialogs, DataFrames, Expanders */
        [data-testid="stDialog"] {{
            background-color: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
            box-shadow: 0 10px 40px rgba(15, 23, 42, 0.12) !important;
        }}
        [data-testid="stDialog"] h2,
        [data-testid="stDialog"] h3 {{
            color: #0f172a !important;
        }}
        [data-testid="stDataFrame"] {{
            border: 1px solid #cbd5e1 !important;
            border-radius: 10px !important;
            background: #ffffff !important;
        }}
        [data-testid="stExpander"] {{
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 10px !important;
        }}
        [data-testid="stExpander"] summary {{
            color: #0f172a !important;
            font-weight: 600 !important;
        }}

        /* 10. Global Alerts in Light Mode */
        [data-testid="stAlert"],
        .stAlert {{
            background-color: #f0f9ff !important;
            background: #f0f9ff !important;
            color: #0369a1 !important;
            border: 1px solid #bae6fd !important;
            border-radius: 10px !important;
        }}
        [data-testid="stAlert"] * {{
            color: #0f172a !important;
        }}
        [data-testid="stAlert"] svg {{
            fill: #0284c7 !important;
            color: #0284c7 !important;
        }}

        /* 11. Metric Delta Badges in Light Mode */
        [data-testid="stMetricDelta"] {{
            background: #dcfce7 !important;
            border: 1px solid #bbf7d0 !important;
            border-radius: 6px !important;
            padding: 2px 8px !important;
            font-weight: 700 !important;
            font-size: 0.78rem !important;
            display: inline-flex !important;
            align-items: center !important;
            gap: 4px !important;
        }}
        [data-testid="stMetricDelta"] * {{
            color: #15803d !important;
        }}
        [data-testid="stMetricDelta"] svg {{
            fill: #15803d !important;
        }}
        ''' if is_light else ''}

        /* ── MAX WIDTH & LAYOUT CONSTRAINT (MODERN CENTERED) ── */
        [data-testid="stAppViewBlockContainer"],
        [data-testid="block-container"] {{
            max-width: 1600px !important;
            margin-left: auto !important;
            margin-right: auto !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }}

        @media (max-width: 1024px) {{
            [data-testid="stAppViewBlockContainer"],
            [data-testid="block-container"] {{
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }}
        }}

        /* ── Top Bar Action Buttons Styling ── */
        .st-key-top_new_analysis_btn button {{
            background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
            border: 1px solid rgba(56, 189, 248, 0.4) !important;
            border-radius: 9px !important;
            font-weight: 700 !important;
            color: #ffffff !important;
            padding: 7px 14px !important;
            margin-top: 6px !important;
            box-shadow: 0 2px 10px rgba(2, 132, 199, 0.25) !important;
            white-space: nowrap !important;
            transition: all 0.2s ease !important;
        }}
        .st-key-top_new_analysis_btn button:hover {{
            background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%) !important;
            border-color: #38bdf8 !important;
            box-shadow: 0 4px 16px rgba(56, 189, 248, 0.45) !important;
            transform: translateY(-1px);
        }}
        .st-key-top_bar_lang_btn button,
        .st-key-top_bar_theme_btn button {{
            border-radius: 9px !important;
            border: 1px solid {border_card} !important;
            background: {bg_card} !important;
            font-weight: 600 !important;
            padding: 6px 10px !important;
            white-space: nowrap !important;
            transition: all 0.2s ease !important;
        }}
        .st-key-top_bar_lang_btn button:hover,
        .st-key-top_bar_theme_btn button:hover {{
            border-color: rgba(56, 189, 248, 0.5) !important;
            background: rgba(56, 189, 248, 0.1) !important;
            transform: translateY(-1px);
        }}

        /* 📱 MOBILE RESPONSIVENESS 📱 */
        @media (max-width: 768px) {{
            /* Leave room for the fixed hamburger menu button on mobile */
            .st-key-top_header_container {{
                {'padding-right: 54px !important;' if rtl_flag else 'padding-left: 54px !important;'}
            }}

            /* 1. Outer columns: stack Brand on top, and Actions below with clear spacing */
            .st-key-top_header_container [data-testid="stHorizontalBlock"]:first-of-type,
            .st-key-top_header_container [data-testid="stColumns"]:first-of-type {{
                flex-direction: column !important;
                gap: 16px !important;
            }}
            .st-key-top_header_container [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"],
            .st-key-top_header_container [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"] {{
                width: 100% !important;
                min-width: 100% !important;
            }}
            .st-key-top_header_container [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child,
            .st-key-top_header_container [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:first-child {{
                margin-bottom: 12px !important;
            }}

            /* 2. Inner row (Language & Theme buttons): force side-by-side at 50% / 50% */
            .st-key-top_header_container [data-testid="stColumn"] [data-testid="stHorizontalBlock"],
            .st-key-top_header_container [data-testid="stColumn"] [data-testid="stColumns"] {{
                display: flex !important;
                flex-direction: row !important;
                flex-wrap: nowrap !important;
                align-items: center !important;
                gap: 8px !important;
                width: 100% !important;
            }}
            .st-key-top_header_container [data-testid="stColumn"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
            .st-key-top_header_container [data-testid="stColumn"] [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
                width: 50% !important;
                min-width: 0 !important;
                flex: 1 1 50% !important;
                padding: 0 !important;
            }}

            /* 3. Small, compact, beautifully matched buttons */
            .st-key-top_bar_lang_btn,
            .st-key-top_bar_theme_btn {{
                width: 100% !important;
            }}
            .st-key-top_bar_lang_btn button,
            .st-key-top_bar_theme_btn button {{
                width: 100% !important;
                height: 34px !important;
                padding: 4px 6px !important;
                font-size: 0.80rem !important;
                border-radius: 8px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }}

            /* 4. The new analysis button directly below them */
            .st-key-top_new_analysis_btn {{
                width: 100% !important;
            }}
            .st-key-top_new_analysis_btn button {{
                width: 100% !important;
                height: 38px !important;
                margin-top: 6px !important;
                padding: 6px 12px !important;
                font-size: 0.86rem !important;
                border-radius: 8px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }}

            .mobile-hide {{
                display: none !important;
            }}
        }}

        /* ── Permanently hide 'Press Enter to submit form' and input instructions ── */
        [data-testid="InputInstructions"],
        div[data-testid="InputInstructions"],
        span[data-testid="InputInstructions"],
        small[data-testid="InputInstructions"],
        .stTextInput [data-testid="InputInstructions"],
        .stNumberInput [data-testid="InputInstructions"],
        .stTextArea [data-testid="InputInstructions"] {{
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
        }}

        /* ── Suppress browser password suggestions & autofill icons ── */
        input::-webkit-credentials-auto-fill-button,
        input::-webkit-strong-password-auto-fill-button,
        input::-webkit-contacts-auto-fill-button,
        input::-webkit-caps-lock-indicator {{
            visibility: hidden !important;
            display: none !important;
            pointer-events: none !important;
            position: absolute !important;
            right: -9999px !important;
            width: 0 !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }}
        input::-ms-reveal,
        input::-ms-clear {{
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            height: 0 !important;
        }}

        /* ── Zero-height iframe cleaner (keeps background script active) ── */
        iframe[height="0"],
        iframe[width="0"],
        .element-container:has(> iframe[height="0"]) {{
            position: absolute !important;
            width: 0 !important;
            height: 0 !important;
            min-height: 0 !important;
            max-height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            border: none !important;
            opacity: 0 !important;
            pointer-events: none !important;
            overflow: hidden !important;
        }}
    </style>
    <script>
    (function() {{
        try {{
            // 1. Sync theme with localStorage and URL for refresh persistence
            var curTheme = "{theme}";
            localStorage.setItem("exotrace_theme", curTheme);
            var url = new URL(window.location.href);
            if (url.searchParams.get("theme") !== curTheme) {{
                url.searchParams.set("theme", curTheme);
                window.history.replaceState({{}}, "", url.toString());
            }}
            if (window.parent && window.parent !== window) {{
                try {{
                    var pUrl = new URL(window.parent.location.href);
                    if (pUrl.searchParams.get("theme") !== curTheme) {{
                        pUrl.searchParams.set("theme", curTheme);
                        window.parent.history.replaceState({{}}, "", pUrl.toString());
                    }}
                }} catch(err) {{}}
            }}

            // 2. Sync lang with localStorage and URL for refresh persistence
            var curLang = "{'ar' if rtl_flag else 'en'}";
            localStorage.setItem("exotrace_lang", curLang);
            if (url.searchParams.get("lang") !== curLang) {{
                url.searchParams.set("lang", curLang);
                window.history.replaceState({{}}, "", url.toString());
            }}
            if (window.parent && window.parent !== window) {{
                try {{
                    var pUrl = new URL(window.parent.location.href);
                    if (pUrl.searchParams.get("lang") !== curLang) {{
                        pUrl.searchParams.set("lang", curLang);
                        window.parent.history.replaceState({{}}, "", pUrl.toString());
                    }}
                }} catch(err) {{}}
            }}

            // 2. Clear sidebar collapsed flag on desktop
            if (window.innerWidth > 768) {{
                for (let i = 0; i < localStorage.length; i++) {{
                    let k = localStorage.key(i);
                    if (k && k.indexOf("stSidebarCollapsed") !== -1 && localStorage.getItem(k) === "true") {{
                        localStorage.removeItem(k);
                    }}
                }}
            }}
        }} catch(e) {{}}
    }})();
    </script>
    """
    st.html(css)
    inject_antifill_script()


def inject_antifill_script():
    """Inject background script to disable browser password suggestions and remove input instructions."""
    try:
        import streamlit as st
        st.html(
            """
            <script>
            (function() {
                try {
                    const parentDoc = window.parent.document;
                    if (!parentDoc) return;

                    function sanitize() {
                        try {
                            // 1. Remove all 'Press Enter to submit form' instruction elements
                            parentDoc.querySelectorAll('[data-testid="InputInstructions"]').forEach(function(el) {
                                el.style.display = 'none';
                                el.style.visibility = 'hidden';
                                el.style.height = '0px';
                            });

                            // 2. Set autocomplete="off" on all forms
                            parentDoc.querySelectorAll('form').forEach(function(form) {
                                form.setAttribute('autocomplete', 'off');
                            });

                            // 3. Disable password suggestions and managers on inputs
                            parentDoc.querySelectorAll('input').forEach(function(inp) {
                                const t = (inp.getAttribute('type') || '').toLowerCase();
                                if (t === 'password') {
                                    inp.setAttribute('autocomplete', 'one-time-code');
                                } else {
                                    inp.setAttribute('autocomplete', 'off');
                                }
                                inp.setAttribute('autocorrect', 'off');
                                inp.setAttribute('autocapitalize', 'off');
                                inp.setAttribute('spellcheck', 'false');
                                inp.setAttribute('data-lpignore', 'true');
                                inp.setAttribute('data-1p-ignore', 'true');
                                inp.setAttribute('data-bwignore', 'true');
                                inp.setAttribute('data-form-type', 'other');
                                inp.setAttribute('aria-autocomplete', 'none');
                            });
                        } catch(e) {}
                    }

                    sanitize();

                    // Listen to capture phase focusin & pointerdown
                    parentDoc.addEventListener('focusin', function(e) {
                        if (e.target && e.target.tagName === 'INPUT') {
                            const inp = e.target;
                            const t = (inp.getAttribute('type') || '').toLowerCase();
                            if (t === 'password') {
                                inp.setAttribute('autocomplete', 'one-time-code');
                            } else {
                                inp.setAttribute('autocomplete', 'off');
                            }
                            inp.setAttribute('data-lpignore', 'true');
                            inp.setAttribute('data-1p-ignore', 'true');
                            inp.setAttribute('data-bwignore', 'true');
                            inp.setAttribute('data-form-type', 'other');
                        }
                    }, true);

                    // Observe dynamic DOM changes in Streamlit
                    const observer = new MutationObserver(sanitize);
                    observer.observe(parentDoc.body, { childList: true, subtree: true });
                } catch(e) {}
            })();
            </script>
            """,
            height=0,
            width=0,
        )
    except Exception:
        pass
