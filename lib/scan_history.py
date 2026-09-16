"""
lib/scan_history.py — Persistent Scan History & Audit Log for ExoTrace.

Maintains a permanent record of all astronomical scans (TIC ID, Star Name,
Timestamp, Sectors, Dips, Comets, Status, and Scientific Summary) in
data/results/scan_history.json.
"""

import os
import json
import time
import pandas as pd

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RESULTS_DIR = os.path.join(_PROJECT_ROOT, "data", "results")
_HISTORY_FILE = os.path.join(_RESULTS_DIR, "scan_history.json")

# Mapping of known TESS catalog targets to human-readable scientific names
STAR_NAMES_MAP_AR = {
    "110969638": "مرشح مذنّب بارز (Exocomet Candidate)",
    "229790952": "Beta Pictoris (بيتا بيكتوريس)",
    "245792896": "Debris Disk System (قرص حطام نجمي)",
    "264306713": "HD 172555",
    "341705353": "قزم نجمي متطور (DWARF)",
    "353304732": "نظام مسح دوري (DWARF)",
    "51904828": "HD 131488",
    "261136679": "HD 209458 (Osiris)",
    "149603524": "نجم فائق السطوع",
    "25155310": "WASP-121",
}

STAR_NAMES_MAP_EN = {
    "110969638": "Exocomet Benchmark (TIC 110969638)",
    "229790952": "Beta Pictoris (Circumstellar Disk)",
    "245792896": "Debris Disk System",
    "264306713": "HD 172555 (A7V System)",
    "341705353": "Evolved Dwarf Star (DWARF)",
    "353304732": "Periodic Survey System (DWARF)",
    "51904828": "HD 131488 (CO Gas Disk)",
    "261136679": "HD 209458 (Osiris)",
    "149603524": "High-Luminosity Benchmark",
    "25155310": "WASP-121 (Extreme System)",
}

STAR_NAMES_MAP = STAR_NAMES_MAP_AR


def get_star_name(tic_id: str | int, lang: str = None) -> str:
    """Return friendly star name or fallback to formatted TIC label."""
    clean_id = str(tic_id).strip()
    if lang is None:
        try:
            from lib.i18n import get_lang
            lang = get_lang()
        except Exception:
            lang = "ar"
    if lang == "en":
        return STAR_NAMES_MAP_EN.get(clean_id, f"Host Star TIC {clean_id}")
    return STAR_NAMES_MAP_AR.get(clean_id, f"النجم المضيف TIC {clean_id}")


def _load_raw_history() -> list[dict]:
    """Load raw scan history list from JSON file."""
    os.makedirs(_RESULTS_DIR, exist_ok=True)
    if not os.path.exists(_HISTORY_FILE):
        return []
    try:
        with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_raw_history(history: list[dict]):
    """Save raw scan history list to JSON file."""
    os.makedirs(_RESULTS_DIR, exist_ok=True)
    tmp = _HISTORY_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _HISTORY_FILE)


def log_scan(
    tic_id: str | int,
    star_name: str = None,
    sectors_count: int = 1,
    dips_count: int = 0,
    comets_count: int = 0,
    status: str = "مكتمل بنجاح ✓",
    summary: str = "",
) -> dict:
    """
    Log or update a star scan session in the persistent scan history.
    """
    clean_id = str(tic_id).strip()
    name = star_name or get_star_name(clean_id)
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    if not summary:
        if comets_count > 0:
            summary = f"رصد {comets_count} مذنّب محتمل مع انخفاضات غير متماثلة واضحة."
        elif dips_count > 0:
            summary = f"رصد {dips_count} انخفاض سطوع متماثل متوافق مع عبور كوكبي أو ثنائي."
        else:
            summary = "استقرار ضوئي تام — لم تُسجل انخفاضات سطوع تتجاوز العتبة."

    record = {
        "tic_id": clean_id,
        "star_name": name,
        "timestamp": now_str,
        "sectors_count": sectors_count,
        "dips_count": dips_count,
        "comets_count": comets_count,
        "status": status,
        "summary": summary,
    }

    history = _load_raw_history()
    # If the star was already logged, update the latest entry
    existing_idx = next((i for i, item in enumerate(history) if str(item.get("tic_id")) == clean_id), None)
    if existing_idx is not None:
        history[existing_idx] = record
    else:
        history.insert(0, record)

    _save_raw_history(history)
    return record


def get_scan_history() -> list[dict]:
    """Retrieve all scan history records."""
    if not os.path.exists(_HISTORY_FILE):
        init_default_scan_history()
    return _load_raw_history()


def clear_all_scan_data():
    """Completely wipe all scan history, reanalysis results, and reviews."""
    _save_raw_history([])

    reanalysis_file = os.path.join(_RESULTS_DIR, "reanalysis_results.csv")
    with open(reanalysis_file, "w", encoding="utf-8") as f:
        f.write("event_id,tic_id,sector,dip_found,start_time,end_time,t0,depth,duration_hr,A,A_time,A_shape,A_area,slope_ratio,snr,morphology_score,gap_flag,morphology_valid,direction_agreement,dominance,t_ingress,t_egress,classification\n")

    reviews_file = os.path.join(_RESULTS_DIR, "reviews.json")
    with open(reviews_file, "w", encoding="utf-8") as f:
        f.write("{}\n")


def restore_baseline_data():
    """Restore pre-configured sample stars and survey results."""
    import shutil
    baseline_json = os.path.join(_RESULTS_DIR, "scan_history_baseline.json")
    if os.path.exists(baseline_json):
        shutil.copyfile(baseline_json, _HISTORY_FILE)
    else:
        init_default_scan_history()

    baseline_csv = os.path.join(_RESULTS_DIR, "reanalysis_results_baseline.csv")
    reanalysis_file = os.path.join(_RESULTS_DIR, "reanalysis_results.csv")
    if os.path.exists(baseline_csv):
        shutil.copyfile(baseline_csv, reanalysis_file)


def get_scanned_stars_table(lang: str = None) -> pd.DataFrame:
    """
    Build clean, localized DataFrame for the scanned stars modal table.
    Supports English and Arabic dynamically based on lang parameter or get_lang().
    """
    if lang is None:
        try:
            from lib.i18n import get_lang
            lang = get_lang()
        except Exception:
            lang = "ar"

    is_en = (lang == "en")
    records = get_scan_history()
    
    ar_cols = [
        "رقم النجم (TIC)", "اسم النجم", "تاريخ الفحص",
        "القطاعات المفحوصة", "إشارات السطوع", "المذنبات المرشحة", "حالة الفحص", "أهم معلومات الفحص"
    ]
    en_cols = [
        "Star (TIC)", "Star Name", "Survey Date",
        "Surveyed Sectors", "Flux Dips", "Comet Candidates", "Pipeline Status", "Observation Summary"
    ]
    
    if not records:
        return pd.DataFrame(columns=en_cols if is_en else ar_cols)

    rows = []
    for r in records:
        ts = str(r.get("timestamp", "—"))
        if len(ts) == 19 and ts[16] == ":":
            ts = ts[:16]

        tic = str(r.get("tic_id", "")).strip()
        star_name_val = get_star_name(tic, lang="en" if is_en else "ar")
        sec_cnt = r.get("sectors_count", 1)
        dips_cnt = r.get("dips_count", 0)
        comets_cnt = r.get("comets_count", 0)
        
        if is_en:
            comets_str = f"☄️ {comets_cnt} Comet{'s' if comets_cnt != 1 else ''}" if comets_cnt > 0 else "0 Comets"
            summary_en = r.get("summary_en")
            if not summary_en:
                if comets_cnt > 0:
                    summary_en = f"Detected {comets_cnt} comet candidate(s) with prominent asymmetric tail profiles."
                elif dips_cnt > 0:
                    summary_en = f"Detected {dips_cnt} symmetric dip(s) consistent with planetary transit or binary."
                else:
                    summary_en = "Photometric stability confirmed — no dips detected above threshold."

            rows.append({
                "Star (TIC)": f"⭐ TIC {tic}",
                "Star Name": star_name_val,
                "Survey Date": ts,
                "Surveyed Sectors": f"🔭 {sec_cnt} Sector{'s' if sec_cnt > 1 else ''}",
                "Flux Dips": f"📉 {dips_cnt} Dip{'s' if dips_cnt != 1 else ''}",
                "Comet Candidates": comets_str,
                "Pipeline Status": "✅ Completed ✓",
                "Observation Summary": summary_en,
            })
        else:
            comets_str = f"☄️ {comets_cnt} مذنب" if comets_cnt > 0 else "0 مذنب"
            rows.append({
                "رقم النجم (TIC)": f"⭐ TIC {tic}",
                "اسم النجم": star_name_val,
                "تاريخ الفحص": ts,
                "القطاعات المفحوصة": f"🔭 {sec_cnt} قطاع",
                "إشارات السطوع": f"📉 {dips_cnt} إشارة",
                "المذنبات المرشحة": comets_str,
                "حالة الفحص": "✅ مكتمل بنجاح",
                "أهم معلومات الفحص": r.get("summary", "—"),
            })

    return pd.DataFrame(rows)


def init_default_scan_history():
    """Seed baseline history records if none exist yet."""
    baseline = [
        {
            "tic_id": "110969638",
            "star_name": "مرشح مذنّب بارز (Exocomet Candidate)",
            "timestamp": "2026-09-14 11:20:00",
            "sectors_count": 2,
            "dips_count": 2,
            "comets_count": 2,
            "status": "مكتمل بنجاح ✓",
            "summary": "تم تأكيد رصد هبوطين ضوئيين بذيول غبارية حادة (لاتماثل عالي A=0.34).",
        },
        {
            "tic_id": "229790952",
            "star_name": "Beta Pictoris (بيتا بيكتوريس)",
            "timestamp": "2026-09-14 11:35:10",
            "sectors_count": 66,
            "dips_count": 7,
            "comets_count": 0,
            "status": "مكتمل بنجاح ✓",
            "summary": "مسح شامل لـ 66 قطاعاً، رُصد 7 انخفاضات سطوع متماثلة ونشاط حطامي كثيف.",
        },
    ]
    _save_raw_history(baseline)
