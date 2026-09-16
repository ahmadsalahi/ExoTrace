"""
lib/data_loader.py — Cached data loading and localization for ExoTrace.

Wraps all CSV reads in @st.cache_data with appropriate TTL.
Provides 100% sanitized, localized, and formatted candidate records
with zero 'None' leaks, Arabic classifications, and computed metrics.
"""

import os
import json
import glob
import numpy as np
import pandas as pd
import streamlit as st

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_PROJECT_ROOT, "data")
_RESULTS_DIR = os.path.join(_DATA_DIR, "results")
_SAMPLE_DIR = os.path.join(_DATA_DIR, "sample")
_LC_DIR = os.path.join(_DATA_DIR, "lightcurves")
_PLOTS_DIR = os.path.join(_PROJECT_ROOT, "plots")
_REVIEWS_FILE = os.path.join(_RESULTS_DIR, "reviews.json")


def _sanitize_and_translate_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sanitize DataFrame to guarantee zero English leaks, zero raw 'None' or NaN,
    and add beautiful formatted columns for display.
    """
    if df.empty:
        return df

    df = df.copy()

    # Classification translation mapping
    class_map_ar = {
        "positive_extreme": "مرشح مذنّب بارز (لاتماثل إيجابي شديد)",
        "positive_moderate": "مرشح مذنّب محتمل (لاتماثل إيجابي معتدل)",
        "reverse_moderate": "لاتماثل معكوس معتدل (سحابة متقدمة / بقع)",
        "reverse_extreme": "لاتماثل معكوس شديد (حطام كوكبي / شذوذ رصدي)",
        "symmetric": "عبور متماثل (كوكب / ثنائي كسوفي)",
        "No dip": "لا يوجد انخفاض سطوع",
        "noise": "إشارة ضجيج أو خلل رصدي",
        "rejected": "مستبعد علمياً",
        "extreme": "مرشح مذنّب بارز (لاتماثل إيجابي شديد)",
        "moderate": "مرشح مذنّب محتمل (لاتماثل إيجابي معتدل)",
        "needs_review": "قياس مورفولوجي غير مكتمل — يحتاج مراجعة",
        "low_snr": "إشارة منخفضة نسبة الإشارة إلى الضجيج — تحتاج مراجعة",
        "discordant_asymmetry": "مقاييس اللاتماثل غير متوافقة — تحتاج مراجعة",
    }
    class_map_en = {
        "positive_extreme": "Strong comet candidate (Positive Extreme)",
        "positive_moderate": "Possible comet candidate (Positive Moderate)",
        "reverse_moderate": "Reverse Moderate (Leading dust / Starspots)",
        "reverse_extreme": "Reverse Extreme (Disintegrating / Anomaly)",
        "symmetric": "Symmetric transit (Exoplanet / Binary)",
        "No dip": "No brightness dip detected",
        "noise": "Noise / instrumental artifact",
        "rejected": "Scientifically rejected",
        "extreme": "Strong comet candidate (Positive Extreme)",
        "moderate": "Possible comet candidate (Positive Moderate)",
        "needs_review": "Morphology not reliably measurable — review required",
        "low_snr": "Low-SNR signal — review required",
        "discordant_asymmetry": "Asymmetry metrics disagree — review required",
    }

    # Clean numeric columns
    numeric_cols = [
        "depth", "duration_hr", "A", "A_time", "A_shape", "A_area",
        "slope_ratio", "snr", "morphology_score", "t_ingress", "t_egress",
        "start_time", "end_time", "t0"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Stable event identity: multiple events in one sector remain distinct.
    if "event_id" not in df.columns:
        def _event_id_row(r):
            try:
                tic = int(float(r.get("tic_id")))
                sec = int(float(r.get("sector")))
                stime = r.get("start_time")
                if pd.isna(stime):
                    return f"TIC{tic}_S{sec:04d}_NODIP"
                return f"TIC{tic}_S{sec:04d}_T{float(stime):.5f}"
            except Exception:
                return "unknown_event"
        df["event_id"] = df.apply(_event_id_row, axis=1)

    # Arabic classification column
    if "classification" in df.columns:
        df["classification_raw"] = df["classification"].fillna("No dip").astype(str)
        df["classification_ar"] = df["classification_raw"].map(lambda x: class_map_ar.get(x, "قيد المراجعة والتدقيق"))
        df["classification_en"] = df["classification_raw"].map(lambda x: class_map_en.get(x, "Under review"))
    else:
        df["classification_raw"] = "No dip"
        df["classification_ar"] = "لا يوجد انخفاض سطوع"
        df["classification_en"] = "No dip detected"

    # Category code for filtering: 'strong', 'reverse', 'symmetric', 'no_dip', 'other'
    def get_category_code(raw):
        if raw in ["positive_extreme", "positive_moderate", "extreme", "moderate"]:
            return "strong"
        elif raw in ["reverse_extreme", "reverse_moderate"]:
            return "reverse"
        elif raw == "symmetric":
            return "symmetric"
        elif raw in ["No dip", "nodip"]:
            return "no_dip"
        return "other"

    df["category_code"] = df["classification_raw"].apply(get_category_code)

    # Formatted display columns
    def fmt_depth(val):
        if pd.isna(val) or val == 0:
            return "—"
        return f"{abs(float(val)) * 100:.2f}%"

    def fmt_hours_ar(val):
        if pd.isna(val) or val is None:
            return "—"
        h = float(val) * 24.0
        return f"{h:.2f} ساعة" if h > 0 else "—"

    def fmt_hours_en(val):
        if pd.isna(val) or val is None:
            return "—"
        h = float(val) * 24.0
        return f"{h:.2f} hr" if h > 0 else "—"

    def fmt_asym(val):
        if pd.isna(val):
            return "—"
        return f"{val * 100:+.1f}%" if abs(val) <= 1.0 else f"{val:.2f}"

    def fmt_shape(val):
        if pd.isna(val):
            return "—"
        return f"{val * 100:.1f}%"

    def fmt_area(val):
        if pd.isna(val):
            return "—"
        return f"{val * 100:+.1f}%"

    def fmt_slope(val):
        if pd.isna(val) or val == 0:
            return "—"
        return f"{val:.2f}x"

    def fmt_snr(val):
        if pd.isna(val) or val <= 0:
            return "—"
        return f"{val:.1f}σ"

    def fmt_morph_score(val):
        if pd.isna(val) or val <= 0:
            return "—"
        return f"{val * 100:.0f}%"

    def fmt_duration_ar(val):
        if pd.isna(val) or val == 0:
            return "—"
        return f"{val:.1f} ساعة"

    def fmt_duration_en(val):
        if pd.isna(val) or val == 0:
            return "—"
        return f"{val:.1f} hr"

    df["depth_display"] = df["depth"].apply(fmt_depth) if "depth" in df.columns else "—"
    df["ingress_display_ar"] = df["t_ingress"].apply(fmt_hours_ar) if "t_ingress" in df.columns else "—"
    df["ingress_display_en"] = df["t_ingress"].apply(fmt_hours_en) if "t_ingress" in df.columns else "—"
    df["egress_display_ar"] = df["t_egress"].apply(fmt_hours_ar) if "t_egress" in df.columns else "—"
    df["egress_display_en"] = df["t_egress"].apply(fmt_hours_en) if "t_egress" in df.columns else "—"
    df["asym_display"] = df["A_time"].apply(fmt_asym) if "A_time" in df.columns else (df["A"].apply(fmt_asym) if "A" in df.columns else "—")
    df["duration_display_ar"] = df["duration_hr"].apply(fmt_duration_ar) if "duration_hr" in df.columns else "—"
    df["duration_display_en"] = df["duration_hr"].apply(fmt_duration_en) if "duration_hr" in df.columns else "—"

    # Multi-metric display columns
    df["asym_shape_display"] = df["A_shape"].apply(fmt_shape) if "A_shape" in df.columns else "—"
    df["asym_area_display"] = df["A_area"].apply(fmt_area) if "A_area" in df.columns else "—"
    df["slope_ratio_display"] = df["slope_ratio"].apply(fmt_slope) if "slope_ratio" in df.columns else "—"
    df["snr_display"] = df["snr"].apply(fmt_snr) if "snr" in df.columns else "—"
    df["morphology_score_display"] = df["morphology_score"].apply(fmt_morph_score) if "morphology_score" in df.columns else "—"

    # Data gap flag display
    if "gap_flag" in df.columns:
        df["gap_flag_bool"] = df["gap_flag"].fillna(False).astype(bool)
        df["gap_flag_display_ar"] = df["gap_flag_bool"].map({True: "⚠️ فجوة رصدية", False: "تغطية متصلة ✓"})
        df["gap_flag_display_en"] = df["gap_flag_bool"].map({True: "⚠️ Data Gap", False: "Continuous ✓"})
    else:
        df["gap_flag_bool"] = False
        df["gap_flag_display_ar"] = "تغطية متصلة ✓"
        df["gap_flag_display_en"] = "Continuous ✓"

    # Dominance display
    dom_map_ar = {
        "post_center": "هيمنة ما بعد المركز (رجحان الخروج)",
        "pre_center": "هيمنة ما قبل المركز (رجحان الدخول)",
        "symmetric": "بروفايل متماثل",
        "none": "—",
    }
    dom_map_en = {
        "post_center": "Post-center dominance (Egress)",
        "pre_center": "Pre-center dominance (Ingress)",
        "symmetric": "Symmetric transit",
        "none": "—",
    }
    if "dominance" in df.columns:
        df["dominance_display_ar"] = df["dominance"].map(lambda x: dom_map_ar.get(str(x), "—"))
        df["dominance_display_en"] = df["dominance"].map(lambda x: dom_map_en.get(str(x), "—"))
    else:
        df["dominance_display_ar"] = "—"
        df["dominance_display_en"] = "—"

    # Default display aliases
    df["ingress_display"] = df["ingress_display_ar"]
    df["egress_display"] = df["egress_display_ar"]
    df["duration_display"] = df["duration_display_ar"]

    # Badge colors for UI styling
    def get_badge_color(raw):
        if raw in ["positive_extreme", "extreme"]:
            return "#ef4444"  # Red/Crimson
        elif raw in ["positive_moderate", "moderate"]:
            return "#f59e0b"  # Amber/Gold
        elif raw in ["reverse_extreme", "reverse_moderate"]:
            return "#8b5cf6"  # Purple/Violet
        elif raw == "symmetric":
            return "#3b82f6"  # Blue
        return "#64748b"      # Muted Gray

    df["badge_color"] = df["classification_raw"].apply(get_badge_color)

    # Boolean dip found
    if "dip_found" in df.columns:
        df["dip_found_bool"] = df["dip_found"].astype(bool)
        df["dip_found_ar"] = df["dip_found_bool"].map({True: "نعم ✓", False: "لا —"})
        df["dip_found_en"] = df["dip_found_bool"].map({True: "Yes ✓", False: "No —"})
    else:
        df["dip_found_bool"] = df["depth"].notna() & (df["depth"] > 0)
        df["dip_found_ar"] = df["dip_found_bool"].map({True: "نعم ✓", False: "لا —"})
        df["dip_found_en"] = df["dip_found_bool"].map({True: "Yes ✓", False: "No —"})

    return df


@st.cache_data(ttl=30)
def load_reanalysis_results() -> pd.DataFrame:
    """Load reanalysis_results.csv — the primary results file, sanitized and localized."""
    path = os.path.join(_RESULTS_DIR, "reanalysis_results.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    raw = pd.read_csv(path)
    return _sanitize_and_translate_df(raw)


@st.cache_data(ttl=30)
def load_candidates_validated() -> pd.DataFrame:
    """Load candidates_validated.csv from the survey pipeline."""
    path = os.path.join(_RESULTS_DIR, "candidates_validated.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    raw = pd.read_csv(path)
    return _sanitize_and_translate_df(raw)


@st.cache_data(ttl=30)
def load_candidates_raw() -> pd.DataFrame:
    """Load candidates_raw.csv."""
    path = os.path.join(_RESULTS_DIR, "candidates_raw.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    raw = pd.read_csv(path)
    return _sanitize_and_translate_df(raw)


@st.cache_data(ttl=60)
def load_sample() -> pd.DataFrame:
    """Load evolved_stars_sample.csv."""
    path = os.path.join(_SAMPLE_DIR, "evolved_stars_sample.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data(ttl=30)
def load_lightcurve(tic_id: int, sector: int, flat: bool = False) -> pd.DataFrame:
    """Load a specific light curve CSV file."""
    suffix = "_flat" if flat else ""
    filename = f"TIC{tic_id}_S{sector:04d}{suffix}.csv"
    path = os.path.join(_LC_DIR, filename)
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path)
    return df


def get_candidate_plots(tic_id: int, sector: int = None, start_time: float = None) -> list[str]:
    """Return candidate plots, optionally narrowed to one sector/event."""
    plots = []
    pattern_reanalysis = os.path.join(_PLOTS_DIR, "reanalysis", f"TIC{tic_id}_*.png")
    plots.extend(glob.glob(pattern_reanalysis))
    pattern_candidates = os.path.join(_PLOTS_DIR, "candidates", f"TIC{tic_id}_*.png")
    plots.extend(glob.glob(pattern_candidates))
    if sector is not None:
        sector_str = f"S{sector:04d}"
        sector_plots = [p for p in plots if sector_str in os.path.basename(p)]
        if sector_plots:
            plots = sector_plots
    if start_time is not None:
        try:
            token = f"T{float(start_time):.2f}"
            event_plots = [p for p in plots if token in os.path.basename(p)]
            if event_plots:
                plots = event_plots
        except (TypeError, ValueError):
            pass
    return sorted(set(plots))


def get_all_results() -> pd.DataFrame:
    """Merge result sources by event_id, not merely by TIC+sector."""
    frames = []
    validated = load_candidates_validated()
    if not validated.empty:
        validated = validated.copy()
        validated["source_priority"] = 2
        frames.append(validated)
    reanalysis = load_reanalysis_results()
    if not reanalysis.empty:
        reanalysis = reanalysis.copy()
        reanalysis["source_priority"] = 1
        frames.append(reanalysis)
    if not frames:
        return pd.DataFrame()
    merged = pd.concat(frames, ignore_index=True, sort=False)
    if "event_id" not in merged.columns:
        merged = _sanitize_and_translate_df(merged)
    merged = merged.sort_values("source_priority", ascending=False).drop_duplicates(subset=["event_id"], keep="first")
    return merged.drop(columns=["source_priority"], errors="ignore").reset_index(drop=True)

def compute_dashboard_stats() -> dict:
    """Compute aggregated statistics for the dashboard KPIs."""
    df = get_all_results()
    if df.empty:
        return {
            "stars_analyzed": 0,
            "dips_detected": 0,
            "strong_candidates": 0,
            "needs_review": 0,
            "running_analyses": 0,
        }

    stars = int(df["tic_id"].nunique()) if "tic_id" in df.columns else 0
    dips = int((df["dip_found_bool"] == True).sum()) if "dip_found_bool" in df.columns else 0
    strong = int((df["category_code"] == "strong").sum()) if "category_code" in df.columns else 0
    needs_rev = int((df["category_code"].isin(["strong", "reverse", "other"])).sum()) if "category_code" in df.columns else 0
    running = st.session_state.get("running_analyses", 0)

    return {
        "stars_analyzed": stars,
        "dips_detected": dips,
        "strong_candidates": strong,
        "needs_review": needs_rev,
        "running_analyses": running,
    }


def get_comets_table(lang: str = None) -> pd.DataFrame:
    """Build clean DataFrame of all detected comets across all stars."""
    from lib.scan_history import get_star_name
    if lang is None:
        try:
            from lib.i18n import get_lang
            lang = get_lang()
        except Exception:
            lang = "ar"

    is_en = (lang == "en")
    df = get_all_results()
    ar_cols = ["رقم النجم (TIC)", "اسم النجم", "القطاع", "عمق الانخفاض %", "نسبة اللاتماثل %", "مدة العبور", "التصنيف العلمي"]
    en_cols = ["Star (TIC)", "Star Name", "Sector", "Dip Depth %", "Asymmetry %", "Transit Duration", "Classification"]
    cols = en_cols if is_en else ar_cols

    if df.empty:
        return pd.DataFrame(columns=cols)
    comets = df[df["category_code"] == "strong"].copy()
    if comets.empty:
        return pd.DataFrame(columns=cols)
    rows = []
    for _, r in comets.iterrows():
        tic = str(int(r.get("tic_id", 0)))
        sec = int(r.get("sector", 0))
        star_n = get_star_name(tic, lang="en" if is_en else "ar")
        if is_en:
            rows.append({
                "Star (TIC)": f"TIC {tic}",
                "Star Name": star_n,
                "Sector": f"Sector {sec}",
                "Dip Depth %": r.get("depth_display", "—"),
                "Asymmetry %": r.get("asym_display", "—"),
                "Transit Duration": r.get("duration_display_en", "—"),
                "Classification": r.get("classification_en", "Comet Candidate"),
            })
        else:
            rows.append({
                "رقم النجم (TIC)": f"TIC {tic}",
                "اسم النجم": star_n,
                "القطاع": f"قطاع {sec}",
                "عمق الانخفاض %": r.get("depth_display", "—"),
                "نسبة اللاتماثل %": r.get("asym_display", "—"),
                "مدة العبور": r.get("duration_display_ar", "—"),
                "التصنيف العلمي": r.get("classification_ar", "مرشح مذنّب"),
            })
    return pd.DataFrame(rows)


def get_dips_table(lang: str = None) -> pd.DataFrame:
    """Build clean DataFrame of all brightness dips detected across all stars."""
    from lib.scan_history import get_star_name
    if lang is None:
        try:
            from lib.i18n import get_lang
            lang = get_lang()
        except Exception:
            lang = "ar"

    is_en = (lang == "en")
    df = get_all_results()
    ar_cols = ["رقم النجم (TIC)", "اسم النجم", "القطاع", "نوع الإشارة", "عمق الانخفاض %", "A_time", "A_shape", "A_area", "مدة العبور"]
    en_cols = ["Star (TIC)", "Star Name", "Sector", "Signal Type", "Dip Depth %", "A_time", "A_shape", "A_area", "Transit Duration"]
    cols = en_cols if is_en else ar_cols

    if df.empty:
        return pd.DataFrame(columns=cols)
    dips = df[df["dip_found_bool"] == True].copy()
    if dips.empty:
        return pd.DataFrame(columns=cols)
    rows = []
    for _, r in dips.iterrows():
        tic = str(int(r.get("tic_id", 0)))
        sec = int(r.get("sector", 0))
        star_n = get_star_name(tic, lang="en" if is_en else "ar")
        if is_en:
            rows.append({
                "Star (TIC)": f"TIC {tic}",
                "Star Name": star_n,
                "Sector": f"Sector {sec}",
                "Signal Type": r.get("classification_en", "Flux Dip"),
                "Dip Depth %": r.get("depth_display", "—"),
                "A_time": r.get("asym_display", "—"),
                "A_shape": r.get("asym_shape_display", "—"),
                "A_area": r.get("asym_area_display", "—"),
                "Transit Duration": r.get("duration_display_en", "—"),
            })
        else:
            rows.append({
                "رقم النجم (TIC)": f"TIC {tic}",
                "اسم النجم": star_n,
                "القطاع": f"قطاع {sec}",
                "نوع الإشارة": r.get("classification_ar", "انخفاض سطوع"),
                "عمق الانخفاض %": r.get("depth_display", "—"),
                "A_time": r.get("asym_display", "—"),
                "A_shape": r.get("asym_shape_display", "—"),
                "A_area": r.get("asym_area_display", "—"),
                "مدة العبور": r.get("duration_display_ar", "—"),
            })
    return pd.DataFrame(rows)


def get_review_table(lang: str = None) -> pd.DataFrame:
    """Build clean DataFrame of all cases pending review/audit."""
    from lib.scan_history import get_star_name
    if lang is None:
        try:
            from lib.i18n import get_lang
            lang = get_lang()
        except Exception:
            lang = "ar"

    is_en = (lang == "en")
    df = get_all_results()
    ar_cols = ["رقم النجم (TIC)", "اسم النجم", "القطاع", "التصنيف الرصدي", "عمق الانخفاض %", "حالة التدقيق", "الإجراء المطلوب"]
    en_cols = ["Star (TIC)", "Star Name", "Sector", "Pipeline Classification", "Dip Depth %", "Audit Status", "Required Action"]
    cols = en_cols if is_en else ar_cols

    if df.empty:
        return pd.DataFrame(columns=cols)
    review_items = df[df["category_code"].isin(["strong", "reverse", "other"])].copy()
    if review_items.empty:
        return pd.DataFrame(columns=cols)
    reviews = get_reviews()
    rows = []
    for _, r in review_items.iterrows():
        tic = str(int(r.get("tic_id", 0)))
        sector = int(r.get("sector", 0))
        rev_key = str(r.get("event_id", f"{tic}_{sector}"))
        rev_data = reviews.get(rev_key, reviews.get(f"{tic}_{sector}", {}))
        star_n = get_star_name(tic, lang="en" if is_en else "ar")
        if is_en:
            status = rev_data.get("status_en") or ("Approved ✓" if rev_data.get("status") == "معتمد وموثق ✓" else ("Rejected" if rev_data.get("status") == "مستبعد علمياً ✕" else "Pending Review ⏳"))
            rows.append({
                "Star (TIC)": f"TIC {tic}",
                "Star Name": star_n,
                "Sector": f"Sector {sector}",
                "Pipeline Classification": r.get("classification_en", "Candidate"),
                "Dip Depth %": r.get("depth_display", "—"),
                "Audit Status": status,
                "Required Action": "Verify Transit Profile & Asymmetry",
            })
        else:
            status = rev_data.get("status", "بانتظار تدقيق الباحث ⏳")
            rows.append({
                "رقم النجم (TIC)": f"TIC {tic}",
                "اسم النجم": star_n,
                "القطاع": f"قطاع {sector}",
                "التصنيف الرصدي": r.get("classification_ar", "مرشح مذنّب"),
                "عمق الانخفاض %": r.get("depth_display", "—"),
                "حالة التدقيق": status,
                "الإجراء المطلوب": "مراجعة نموذج المنحنى والمصادقة",
            })
    return pd.DataFrame(rows)


def classify_display(classification: str, lang: str = "ar") -> str:
    """Map current/legacy internal classifications to a concise display label."""
    c = str(classification or "").strip().lower()
    if c in {"", "no dip", "nodip", "none"}:
        return "⚫ لا يوجد انخفاض سطوع" if lang == "ar" else "⚫ No dip detected"

    labels_ar = {
        "positive_extreme": "🔴 مرشح قوي — هيمنة ما بعد المركز",
        "positive_moderate": "🟡 مرشح محتمل — هيمنة ما بعد المركز",
        "reverse_extreme": "🟣 لاتماثل معكوس شديد — هيمنة ما قبل المركز",
        "reverse_moderate": "🟣 لاتماثل معكوس معتدل — هيمنة ما قبل المركز",
        "symmetric": "🔵 عبور متماثل (كوكب أو ثنائي)",
        "low_snr": "⚪ إشارة منخفضة الدلالة — تحتاج مراجعة",
        "needs_review": "⚪ بيانات/تغطية غير كافية — تحتاج مراجعة",
        "discordant_asymmetry": "🟠 مؤشرات لاتماثل متعارضة — تحتاج مراجعة",
        # Legacy values
        "extreme": "🔴 مرشح مذنّب قوي (لاتماثل حاد)",
        "moderate": "🟡 مرشح مذنّب محتمل (لاتماثل معتدل)",
    }
    labels_en = {
        "positive_extreme": "🔴 Strong candidate — post-center dominance",
        "positive_moderate": "🟡 Possible candidate — post-center dominance",
        "reverse_extreme": "🟣 Strong reverse asymmetry — pre-center dominance",
        "reverse_moderate": "🟣 Moderate reverse asymmetry — pre-center dominance",
        "symmetric": "🔵 Symmetric planet/binary transit",
        "low_snr": "⚪ Low-significance signal — review required",
        "needs_review": "⚪ Insufficient coverage/data — review required",
        "discordant_asymmetry": "🟠 Discordant asymmetry metrics — review required",
        # Legacy values
        "extreme": "🔴 Strong comet candidate",
        "moderate": "🟡 Possible comet candidate",
    }
    return (labels_en if lang == "en" else labels_ar).get(
        c,
        "⚪ Under review" if lang == "en" else "⚪ قيد المراجعة والتدقيق",
    )


def get_reviews() -> dict:
    """Load researcher reviews safely; malformed files do not crash the UI."""
    if not os.path.exists(_REVIEWS_FILE):
        return {}
    try:
        with open(_REVIEWS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, TypeError):
        return {}



def save_review(tic_id: int, sector: int, classification: str, status: str, notes: str,
                event_id: str = None, start_time: float = None):
    """Save review per event, with backward-compatible TIC+sector fallback."""
    import time
    reviews = get_reviews()
    if not event_id:
        if start_time is not None and np.isfinite(float(start_time)):
            event_id = f"TIC{int(tic_id)}_S{int(sector):04d}_T{float(start_time):.5f}"
        else:
            event_id = f"TIC{int(tic_id)}_S{int(sector):04d}"
    reviews[event_id] = {
        "event_id": event_id, "tic_id": tic_id, "sector": sector,
        "start_time": start_time, "classification": classification,
        "status": status, "notes": notes,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    os.makedirs(os.path.dirname(_REVIEWS_FILE), exist_ok=True)
    tmp = _REVIEWS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _REVIEWS_FILE)


def get_review(tic_id: int, sector: int, event_id: str = None, start_time: float = None) -> dict | None:
    reviews = get_reviews()
    if event_id and event_id in reviews:
        return reviews[event_id]
    if start_time is not None:
        key = f"TIC{int(tic_id)}_S{int(sector):04d}_T{float(start_time):.5f}"
        if key in reviews:
            return reviews[key]
    # legacy keys
    return reviews.get(f"{tic_id}_{sector}") or reviews.get(f"TIC{int(tic_id)}_S{int(sector):04d}")

