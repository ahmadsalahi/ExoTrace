"""
lib/settings_manager.py — Persistent configuration manager for ExoTrace.

Handles loading, saving, and resetting detection algorithm settings
to/from data/settings.json.
"""

import json
import os
import streamlit as st
import config

_SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "settings.json",
)

DEFAULT_ANALYSIS_SETTINGS = config.DEFAULT_ANALYSIS_SETTINGS.copy()


def load_analysis_settings() -> dict:
    """Load settings from data/settings.json with fallback to defaults."""
    if os.path.exists(_SETTINGS_FILE):
        try:
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    merged = DEFAULT_ANALYSIS_SETTINGS.copy()
                    merged.update(data)
                    return merged
        except Exception:
            pass
    return DEFAULT_ANALYSIS_SETTINGS.copy()


def save_analysis_settings(settings: dict) -> bool:
    """Save settings dictionary to data/settings.json and sync session state."""
    try:
        os.makedirs(os.path.dirname(_SETTINGS_FILE), exist_ok=True)
        tmp = _SETTINGS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        os.replace(tmp, _SETTINGS_FILE)
        if hasattr(st, "session_state") and "analysis_settings" in st.session_state:
            st.session_state.analysis_settings = settings.copy()
        return True
    except Exception:
        return False


def reset_analysis_settings() -> dict:
    """Reset settings to factory defaults in both file and session state."""
    defaults = DEFAULT_ANALYSIS_SETTINGS.copy()
    save_analysis_settings(defaults)
    return defaults
