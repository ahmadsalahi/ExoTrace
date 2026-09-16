"""
config.py — ثوابت وإعدادات مشروع كشف المذنبات الخارجية حول النجوم المتطورة
===========================================================================
"""

import os

# ──────────────────────────────── المسارات ────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SAMPLE_DIR = os.path.join(DATA_DIR, "sample")
LC_DIR = os.path.join(DATA_DIR, "lightcurves")
RESULTS_DIR = os.path.join(DATA_DIR, "results")
PLOTS_DIR = os.path.join(PROJECT_ROOT, "plots")
CANDIDATES_PLOTS_DIR = os.path.join(PLOTS_DIR, "candidates")

# ──────────────────────────── معايير العيّنة ───────────────────────────────
# الجاذبية السطحية — قيمة منخفضة تعني نجماً متطوراً (عملاق / عملاق فرعي)
LOGG_MAX = 3.5          # log g ≤ 3.5 للعمالقة والعمالقة الفرعية

# القدر الضوئي — حد أعلى لضمان جودة بيانات كافية
TMAG_MAX = 12.0         # TESS magnitude ≤ 12

# ────────────────────────── نطاق قطاعات TESS ──────────────────────────────
# الدراسة السابقة (Norazman+ 2025) غطّت القطاعات 1–26
# نبدأ من 27 فصاعداً للبحث الجديد
SECTOR_MIN = 27         # أول قطاع لم تغطّيه الدراسة السابقة
SECTOR_MAX = 99         # حد أعلى مرن — يشمل كل قطاع متاح حالياً

# ─────────────────────── معايير كشف الهبوطات ──────────────────────────────
SIGMA_THRESHOLD = 3.0   # عتبة الكشف: نقاط أقل من −3σ (تُحسب الآن بـ MAD الحقيقي القوي)
DIP_MIN_DURATION_HR = 1.0    # أقل مدة لهبوط مرشّح (ساعة كاملة كما تطلب واجهة الفلاتر)
DIP_MAX_DURATION_HR = 24.0   # أعلى مدة لهبوط مرشّح (ساعة)

# ──────────────────── معايير تنظيف منحنى الضوء ────────────────────────────
DETREND_WINDOW_DAYS = 2.0    # طول نافذة التنعيم (أيام) — قيمة افتراضية
OUTLIER_SIGMA = 5.0          # عتبة إزالة القيم الشاذة قبل التنظيف

# ──────────────────── معايير معامل اللاتماثل ──────────────────────────────
# لا نستبعد أي نطاق — خلافاً للدراسة السابقة التي استبعدت > 1%
ASYMMETRY_MIN = 0.05    # الحد الأدنى: تحت هذا يُعتبر متماثلاً (كوكب/ثنائي)
ASYMMETRY_WARN = 0.30   # فوق هذا: لاتماثل شديد — يُفحص بحذر

# ────────────────── المرشّحان المعروفان لإعادة التحليل ────────────────────
KNOWN_CANDIDATES = [
    {
        "tic_id": 229790952,
        "name": "TIC 229790952",
        "type": "عملاق",
        "notes": "مرشّح من دراسة Norazman+ 2025 — طبيعته غير محسومة",
    },
    {
        "tic_id": 110969638,
        "name": "TIC 110969638",
        "type": "عملاق فائق محتمل",
        "notes": "مرشّح من دراسة Norazman+ 2025 — طبيعته غير محسومة",
    },
]

# ────────────────────────── إعدادات التحميل ───────────────────────────────
PREFERRED_AUTHOR = "SPOC"     # المصدر المفضّل لمنحنيات الضوء
FALLBACK_AUTHORS = ["QLP", "TESS-SPOC"]  # مصادر بديلة
DOWNLOAD_BATCH_SIZE = 50      # عدد النجوم في كل دفعة تحميل


# ───────────────────── إعدادات التشغيل الموحّدة ─────────────────────
ANALYSIS_SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
DEFAULT_ANALYSIS_SETTINGS = {
    "sigma_threshold": SIGMA_THRESHOLD,
    "min_duration": DIP_MIN_DURATION_HR,
    "max_duration": DIP_MAX_DURATION_HR,
    "asymmetry_min": ASYMMETRY_MIN,
    "detrend_window": DETREND_WINDOW_DAYS,
}


def load_runtime_settings():
    """Read persisted analysis settings without importing Streamlit.

    The scientific engine and CLI scripts use this function so the values shown
    in the Settings page are the same values used by the pipeline.
    """
    import json
    settings = DEFAULT_ANALYSIS_SETTINGS.copy()
    try:
        if os.path.exists(ANALYSIS_SETTINGS_FILE):
            with open(ANALYSIS_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for key in settings:
                    if key in data:
                        settings[key] = float(data[key])
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass
    return settings


def get_analysis_setting(name, fallback=None):
    settings = load_runtime_settings()
    if name in settings:
        return settings[name]
    return fallback

# Quality-control constants
MIN_EVENT_POINTS = 3
MIN_WING_POINTS = 2
SNR_REVIEW_THRESHOLD = 5.0
EDGE_MARGIN_DAYS = 0.5
