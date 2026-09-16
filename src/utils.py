"""
utils.py — دوال مساعدة مشتركة لجميع خطوات خط الأنابيب
=======================================================
"""

import os
import sys
import numpy as np
import pandas as pd

# أضف مجلد المشروع الجذري إلى مسار البحث
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


# ═══════════════════════════ إدارة الملفات ════════════════════════════════

def ensure_dirs():
    """إنشاء جميع المجلدات المطلوبة إذا لم تكن موجودة."""
    for d in [config.SAMPLE_DIR, config.LC_DIR, config.RESULTS_DIR,
              config.PLOTS_DIR, config.CANDIDATES_PLOTS_DIR]:
        os.makedirs(d, exist_ok=True)


def sample_path():
    """مسار ملف عيّنة النجوم."""
    return os.path.join(config.SAMPLE_DIR, "evolved_stars_sample.csv")


def candidates_raw_path():
    """مسار ملف المرشّحين الأوليين."""
    return os.path.join(config.RESULTS_DIR, "candidates_raw.csv")


def candidates_validated_path():
    """مسار ملف المرشّحين بعد التحقق."""
    return os.path.join(config.RESULTS_DIR, "candidates_validated.csv")


def reanalysis_path():
    """مسار ملف نتائج إعادة التحليل."""
    return os.path.join(config.RESULTS_DIR, "reanalysis_results.csv")


def lc_cache_path(tic_id, sector):
    """مسار ملف منحنى الضوء المحفوظ محلياً."""
    return os.path.join(config.LC_DIR, f"TIC{tic_id}_S{sector:04d}.csv")


# ═══════════════════════ حساب معامل اللاتماثل ════════════════════════════

# ═══════════════════════ الإطار متعدد المقاييس لتحليل اللاتماثل ════════════════════════════

def fit_transit_center(time, flux, start_idx, end_idx, min_idx, baseline=1.0):
    """
    تحديد مركز الهبوط t0 باستخدام الانحدار المكافئ (Parabolic Fit) أو المركز الثقلي التدفقي
    بدلاً من الاعتماد الحصري على النقطة الفردية الأدنى تدفقاً.
    """
    dip_t = time[start_idx:end_idx+1]
    dip_f = flux[start_idx:end_idx+1]

    if len(dip_t) < 4:
        return float(time[min_idx])

    depth = baseline - flux[min_idx]
    if depth <= 0:
        return float(time[min_idx])

    # اختيار نقاط القاع (أسفل 60% من عمق الهبوط)
    thresh = baseline - 0.6 * depth
    core_mask = dip_f <= thresh

    if np.sum(core_mask) >= 5:
        t_core = dip_t[core_mask]
        f_core = dip_f[core_mask]
        try:
            p = np.polyfit(t_core, f_core, 2)
            if p[0] > 0:  # قطع مكافئ محدب لأسفل
                t_vertex = -p[1] / (2.0 * p[0])
                if time[start_idx] <= t_vertex <= time[end_idx]:
                    return float(t_vertex)
        except Exception:
            pass

    # بديل آمن: المركز الثقلي للتدفق (Flux-weighted centroid)
    weights = np.maximum(0.0, baseline - dip_f) ** 2
    sum_w = np.sum(weights)
    if sum_w > 0:
        t_centroid = np.sum(weights * dip_t) / sum_w
        if time[start_idx] <= t_centroid <= time[end_idx]:
            return float(t_centroid)

    return float(time[min_idx])



def compute_local_noise_mad(time, flux, start_idx, end_idx, baseline=1.0, return_baseline=False):
    """Robust local noise using MAD and a locally measured baseline.

    The event itself is excluded. When there are too few nearby points the
    function falls back to all out-of-event samples, then to the full curve.
    """
    time = np.asarray(time, dtype=float)
    flux = np.asarray(flux, dtype=float)
    t_start = time[start_idx]
    t_end = time[end_idx]
    dt_dur = max(0.01, t_end - t_start)

    left_mask = (time >= t_start - 2.0 * dt_dur) & (time < t_start)
    right_mask = (time > t_end) & (time <= t_end + 2.0 * dt_dur)
    local_mask = left_mask | right_mask
    if np.sum(local_mask) < 8:
        local_mask = (time < t_start) | (time > t_end)

    local_flux = flux[local_mask] if np.sum(local_mask) >= 5 else flux
    local_flux = local_flux[np.isfinite(local_flux)]
    if len(local_flux) == 0:
        local_baseline = float(baseline)
        sigma_mad = 1e-5
    else:
        local_baseline = float(np.nanmedian(local_flux))
        mad = np.nanmedian(np.abs(local_flux - local_baseline))
        sigma_mad = float(1.4826 * mad)
        if not np.isfinite(sigma_mad) or sigma_mad <= 1e-7:
            sigma_mad = float(np.nanstd(local_flux))
        if not np.isfinite(sigma_mad) or sigma_mad <= 1e-7:
            sigma_mad = 1e-5

    depth = local_baseline - float(np.nanmin(flux[start_idx:end_idx + 1]))
    snr = max(0.0, depth) / sigma_mad if sigma_mad > 0 else 0.0
    result = (round(float(sigma_mad), 6), round(float(snr), 2))
    if return_baseline:
        return result[0], result[1], float(local_baseline)
    return result

def check_data_coverage(time, start_idx, end_idx, t0):
    """
    فحص التغطية الرصدية وفجوات البيانات لمنع تصنيف انقطاع البيانات أو نهاية القطاع كذيل وهمي.
    """
    dip_t = time[start_idx:end_idx+1]
    if len(dip_t) < 3:
        return True, 0.0, 0.0

    diffs = np.diff(dip_t)
    cadence = np.nanmedian(diffs) if len(diffs) > 0 else 0.00138  # 2 min default
    if cadence <= 0:
        cadence = 0.00138

    # فحص أقصى فجوة زمنية
    left_t = dip_t[dip_t <= t0]
    right_t = dip_t[dip_t >= t0]

    max_gap_left = np.max(np.diff(left_t)) if len(left_t) > 1 else 0.0
    max_gap_right = np.max(np.diff(right_t)) if len(right_t) > 1 else 0.0
    max_gap = max(max_gap_left, max_gap_right)

    total_dur = dip_t[-1] - dip_t[0]
    expected_pts = max(1.0, total_dur / cadence + 1.0)
    duty_cycle = min(1.0, len(dip_t) / expected_pts)

    gap_flag = bool((max_gap > 3.5 * cadence) or (duty_cycle < 0.60))
    return gap_flag, round(float(max_gap), 5), round(float(duty_cycle), 2)



def compute_fit_slopes(time, flux, start_idx, end_idx, t0, baseline=1.0):
    """Fit ingress/egress slopes and return |m_in|/|m_eg|.

    A near-zero egress slope no longer maps to 1 (which falsely implies
    symmetry). The denominator is protected with a small, scale-aware epsilon.
    """
    dip_t = np.asarray(time[start_idx:end_idx + 1], dtype=float)
    dip_f = np.asarray(flux[start_idx:end_idx + 1], dtype=float)
    left_mask = dip_t <= t0
    right_mask = dip_t >= t0

    depth = max(1e-8, float(baseline - np.nanmin(dip_f)))
    total_dur = max(1e-6, float(dip_t[-1] - dip_t[0]))
    eps = max(1e-8, depth / total_dur * 1e-3)

    if np.sum(left_mask) >= 3:
        s_in = abs(float(np.polyfit(dip_t[left_mask], dip_f[left_mask], 1)[0]))
    elif np.sum(left_mask) >= 2:
        s_in = abs(float((dip_f[left_mask][-1] - dip_f[left_mask][0]) /
                         (dip_t[left_mask][-1] - dip_t[left_mask][0] + 1e-12)))
    else:
        s_in = np.nan

    if np.sum(right_mask) >= 3:
        s_eg = abs(float(np.polyfit(dip_t[right_mask], dip_f[right_mask], 1)[0]))
    elif np.sum(right_mask) >= 2:
        s_eg = abs(float((dip_f[right_mask][-1] - dip_f[right_mask][0]) /
                         (dip_t[right_mask][-1] - dip_t[right_mask][0] + 1e-12)))
    else:
        s_eg = np.nan

    if not np.isfinite(s_in) or not np.isfinite(s_eg):
        slope_ratio = np.nan
    else:
        slope_ratio = min(50.0, s_in / max(s_eg, eps))
    return float(s_in) if np.isfinite(s_in) else np.nan, float(s_eg) if np.isfinite(s_eg) else np.nan, float(slope_ratio) if np.isfinite(slope_ratio) else np.nan


def shape_asymmetry_advanced(time, flux, t0, depth, baseline=1.0, n_points=50, min_wing_points=None):
    """Measure profile-shape and integrated-area asymmetry.

    Returns NaN, NaN when the morphology is not measurable; this is distinct
    from a measured symmetric event (0, 0).
    """
    if min_wing_points is None:
        min_wing_points = getattr(config, "MIN_WING_POINTS", 2)
    time = np.asarray(time, dtype=float)
    flux = np.asarray(flux, dtype=float)
    valid = np.isfinite(time) & np.isfinite(flux)
    time = time[valid]
    flux = flux[valid]
    if len(time) < (2 * min_wing_points + 1) or not np.isfinite(depth) or depth <= 1e-8:
        return np.nan, np.nan

    order = np.argsort(time)
    time, flux = time[order], flux[order]
    left_mask, right_mask = time < t0, time > t0
    if np.sum(left_mask) < min_wing_points or np.sum(right_mask) < min_wing_points:
        return np.nan, np.nan

    left_t, left_f = t0 - time[left_mask], flux[left_mask]
    right_t, right_f = time[right_mask] - t0, flux[right_mask]
    li, ri = np.argsort(left_t), np.argsort(right_t)
    left_t, left_f = left_t[li], left_f[li]
    right_t, right_f = right_t[ri], right_f[ri]
    max_dt = max(float(left_t.max()), float(right_t.max()))
    if max_dt <= 0:
        return np.nan, np.nan

    dt = np.linspace(0.0, max_dt, int(max(10, n_points)))
    left_interp = np.interp(dt, left_t, left_f, right=baseline)
    right_interp = np.interp(dt, right_t, right_f, right=baseline)
    A_shape = float(np.mean(np.abs(left_interp - right_interp)) / depth)

    deficit_left = np.clip(baseline - left_interp, 0.0, None)
    deficit_right = np.clip(baseline - right_interp, 0.0, None)
    trapz_fn = getattr(np, "trapezoid", getattr(np, "trapz", None))
    area_left = float(trapz_fn(deficit_left, dt))
    area_right = float(trapz_fn(deficit_right, dt))
    total_area = area_left + area_right
    A_area = (area_right - area_left) / total_area if total_area > 1e-12 else 0.0
    return round(A_shape, 4), round(float(np.clip(A_area, -1.0, 1.0)), 4)


def compute_multimetric_asymmetry(time, flux, start_idx, end_idx, min_idx,
                                  baseline=1.0, n_points=50, asymmetry_min=None):
    """Multi-metric event morphology engine.

    A_time, A_shape, and A_area are kept as separate measurements.  The legacy
    field ``A`` elsewhere remains A_time only for backward compatibility.
    Classification direction is based on A_area, with explicit quality states
    for gaps, unmeasurable morphology, low SNR, or direction disagreement.
    """
    time = np.asarray(time, dtype=float)
    flux = np.asarray(flux, dtype=float)
    if asymmetry_min is None:
        asymmetry_min = float(config.get_analysis_setting("asymmetry_min", config.ASYMMETRY_MIN))

    t0 = fit_transit_center(time, flux, start_idx, end_idx, min_idx, baseline=baseline)
    t_start, t_end = float(time[start_idx]), float(time[end_idx])
    t_ingress = max(0.0, t0 - t_start)
    t_egress = max(0.0, t_end - t0)
    total_dur = t_ingress + t_egress
    A_time = (t_egress - t_ingress) / total_dur if total_dur > 1e-10 else np.nan

    gap_flag, max_gap, duty_cycle = check_data_coverage(time, start_idx, end_idx, t0)
    sigma_mad, snr, local_baseline = compute_local_noise_mad(
        time, flux, start_idx, end_idx, baseline=baseline, return_baseline=True
    )
    depth = float(local_baseline - np.nanmin(flux[start_idx:end_idx + 1]))
    if depth <= 0:
        depth = 1e-8

    s_in, s_eg, slope_ratio = compute_fit_slopes(
        time, flux, start_idx, end_idx, t0, baseline=local_baseline
    )

    n_pts = end_idx - start_idx + 1
    pad = max(3, int(n_pts * 0.3))
    w_start = max(0, start_idx - pad)
    w_end = min(len(time) - 1, end_idx + pad)
    win_t = time[w_start:w_end + 1]
    win_f = flux[w_start:w_end + 1]
    win_diffs = np.diff(win_t)
    win_good_diffs = win_diffs[np.isfinite(win_diffs) & (win_diffs > 0)]
    profile_gap_flag = False
    if len(win_good_diffs) > 1:
        profile_cadence = float(np.nanmedian(win_good_diffs))
        profile_gap_flag = bool(np.nanmax(win_good_diffs) > 3.5 * profile_cadence)
    gap_flag = bool(gap_flag or profile_gap_flag)

    A_shape, A_area = shape_asymmetry_advanced(
        win_t, win_f, t0, depth, baseline=local_baseline, n_points=n_points
    )

    morphology_valid = bool(np.isfinite(A_shape) and np.isfinite(A_area) and not gap_flag)
    if not np.isfinite(A_area) or abs(A_area) < asymmetry_min:
        dominance = "symmetric"
    elif A_area > 0:
        dominance = "post_center"
    else:
        dominance = "pre_center"

    # Direction agreement is informative only when both metrics are significant.
    direction_agreement = True
    if np.isfinite(A_time) and np.isfinite(A_area) and abs(A_time) >= asymmetry_min and abs(A_area) >= asymmetry_min:
        direction_agreement = bool(np.sign(A_time) == np.sign(A_area))

    if not morphology_valid:
        classification = "needs_review"
        morph_score = 0.0
    else:
        sign = 1.0 if A_area > 0 else -1.0
        time_score = min(1.0, max(0.0, sign * A_time)) if np.isfinite(A_time) else 0.0
        area_score = min(1.0, max(0.0, sign * A_area)) if np.isfinite(A_area) else 0.0
        shape_score = min(1.0, max(0.0, A_shape)) if np.isfinite(A_shape) else 0.0
        
        exocomet_score = 0.5 * time_score + 0.3 * area_score + 0.2 * shape_score
        
        if snr < 5.0:
            exocomet_score *= 0.7
            
        if not direction_agreement:
            exocomet_score *= 0.8
            
        if gap_flag:
            exocomet_score *= 0.7
            
        morph_score = float(exocomet_score)
        
        extreme = abs(A_area) > getattr(config, "ASYMMETRY_WARN", 0.30) or (np.isfinite(A_time) and abs(A_time) > getattr(config, "ASYMMETRY_WARN", 0.30))
        
        if dominance == "symmetric":
            classification = "symmetric"
        else:
            if dominance == "post_center":
                classification = "positive_extreme" if extreme else "positive_moderate"
            else:
                classification = "reverse_extreme" if extreme else "reverse_moderate"

    return {
        "A_time": round(float(A_time), 4) if np.isfinite(A_time) else np.nan,
        "A_shape": round(float(A_shape), 4) if np.isfinite(A_shape) else np.nan,
        "A_area": round(float(A_area), 4) if np.isfinite(A_area) else np.nan,
        "slope_ratio": round(float(slope_ratio), 2) if np.isfinite(slope_ratio) else np.nan,
        "snr": round(float(snr), 1),
        "morphology_score": round(float(morph_score), 3),
        "gap_flag": bool(gap_flag),
        "max_gap": max_gap,
        "duty_cycle": duty_cycle,
        "morphology_valid": morphology_valid,
        "direction_agreement": bool(direction_agreement),
        "dominance": dominance,
        "t0": round(float(t0), 5),
        "t_ingress": round(float(t_ingress), 5),
        "t_egress": round(float(t_egress), 5),
        "depth": round(float(depth), 6),
        "local_baseline": round(float(local_baseline), 6),
        "classification": classification,
    }

def compute_asymmetry(time, flux, dip_start_idx, dip_end_idx, dip_min_idx):
    """
    حساب معامل اللاتماثل لهبوط معيّن (مع الحفاظ على التوافق التراجعي الكامل).
    """
    res = compute_multimetric_asymmetry(time, flux, dip_start_idx, dip_end_idx, dip_min_idx)
    return res["A_time"], res["t_ingress"], res["t_egress"]


# ═══════════════════════ كشف الهبوطات في المنحنى ═════════════════════════


def detect_dips(time, flux, sigma_thresh=None, min_dur_hr=None, max_dur_hr=None, min_points=None):
    """Detect contiguous statistically significant flux dips.

    Runtime settings are used when arguments are omitted.  Events must contain
    at least ``MIN_EVENT_POINTS`` samples, and the terminal-event duration is
    computed consistently with all other events.
    """
    settings = config.load_runtime_settings()
    sigma_thresh = float(settings["sigma_threshold"] if sigma_thresh is None else sigma_thresh)
    min_dur_hr = float(settings["min_duration"] if min_dur_hr is None else min_dur_hr)
    max_dur_hr = float(settings["max_duration"] if max_dur_hr is None else max_dur_hr)
    min_points = int(getattr(config, "MIN_EVENT_POINTS", 3) if min_points is None else min_points)

    time = np.asarray(time, dtype=float)
    flux = np.asarray(flux, dtype=float)
    valid = np.isfinite(time) & np.isfinite(flux)
    time, flux = time[valid], flux[valid]
    if len(time) < min_points:
        return []

    median_flux = float(np.nanmedian(flux))
    mad = float(np.nanmedian(np.abs(flux - median_flux)))
    std_flux = 1.4826 * mad
    if not np.isfinite(std_flux) or std_flux <= 1e-6:
        # First-difference MAD is less sensitive to a small number of deep dips.
        dflux = np.diff(flux)
        dflux = dflux[np.isfinite(dflux)]
        if len(dflux) >= 3:
            dmed = float(np.nanmedian(dflux))
            dmad = float(np.nanmedian(np.abs(dflux - dmed)))
            std_flux = 1.4826 * dmad / np.sqrt(2.0)
    if not np.isfinite(std_flux) or std_flux <= 1e-6:
        # Quantized/nearly noiseless test data: use a conservative normalized-flux floor.
        std_flux = 0.001
    threshold = median_flux - sigma_thresh * std_flux

    diffs = np.diff(time)
    good_diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
    cadence_days = float(np.nanmedian(good_diffs)) if len(good_diffs) else 0.00138
    below = flux < threshold
    dips, in_dip, start_idx = [], False, 0

    def maybe_add(start_idx, end_idx):
        n_event = end_idx - start_idx + 1
        if n_event < min_points:
            return
        duration_days = (time[end_idx] - time[start_idx]) + cadence_days
        duration_hr = float(duration_days * 24.0)
        if not (min_dur_hr <= duration_hr <= max_dur_hr):
            return
        segment = flux[start_idx:end_idx + 1]
        min_idx = start_idx + int(np.argmin(segment))
        dips.append({
            "start_idx": start_idx, "end_idx": end_idx, "min_idx": min_idx,
            "start_time": float(time[start_idx]), "end_time": float(time[end_idx]),
            "min_time": float(time[min_idx]), "depth": float(median_flux - flux[min_idx]),
            "duration_hr": duration_hr, "n_points": n_event,
        })

    for i, is_below in enumerate(below):
        if is_below and not in_dip:
            in_dip, start_idx = True, i
        elif not is_below and in_dip:
            in_dip = False
            maybe_add(start_idx, i - 1)
    if in_dip:
        maybe_add(start_idx, len(flux) - 1)
    return dips

# ═══════════════════════════ تنظيف المنحنى ════════════════════════════════


def flatten_lightcurve(time, flux, window_days=None, outlier_sigma=None, return_clean_flux=False):
    """Robustly detrend a light curve while preserving negative transit dips."""
    from scipy.ndimage import median_filter
    settings = config.load_runtime_settings()
    if window_days is None:
        window_days = float(settings["detrend_window"])
    if outlier_sigma is None:
        outlier_sigma = config.OUTLIER_SIGMA

    time = np.asarray(time, dtype=float)
    flux = np.asarray(flux, dtype=float)
    mask = np.isfinite(time) & np.isfinite(flux)
    time_clean, flux_clean = time[mask], flux[mask]
    if len(flux_clean) == 0:
        empty = np.array([])
        return (empty, empty, empty, empty) if return_clean_flux else (empty, empty, empty)

    med = float(np.nanmedian(flux_clean))
    mad = float(np.nanmedian(np.abs(flux_clean - med)))
    robust_sigma = 1.4826 * mad
    if not np.isfinite(robust_sigma) or robust_sigma <= 1e-8:
        robust_sigma = float(np.nanstd(flux_clean))
    if not np.isfinite(robust_sigma) or robust_sigma <= 1e-8:
        robust_sigma = 1e-5

    # Remove positive flares/outliers, retain plausible negative dips.
    good = (flux_clean - med) < float(outlier_sigma) * robust_sigma
    good &= (flux_clean > med - 50.0 * robust_sigma) & (flux_clean > 0.0)
    time_clean, flux_clean = time_clean[good], flux_clean[good]
    if len(flux_clean) < 10:
        trend = np.ones_like(flux_clean) * med
        return (time_clean, flux_clean, trend, flux_clean.copy()) if return_clean_flux else (time_clean, flux_clean, trend)

    diffs = np.diff(time_clean)
    good_diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
    cadence_days = float(np.nanmedian(good_diffs)) if len(good_diffs) else 2.0 / (60 * 24)
    window_pts = max(3, int(float(window_days) / cadence_days))
    if window_pts % 2 == 0:
        window_pts += 1
    # Avoid a filter window larger than a practical odd size for this segment.
    if window_pts >= len(flux_clean):
        window_pts = len(flux_clean) if len(flux_clean) % 2 == 1 else len(flux_clean) - 1
        window_pts = max(3, window_pts)

    trend = median_filter(flux_clean, size=window_pts, mode="nearest")
    trend = np.asarray(trend, dtype=float)
    trend[~np.isfinite(trend) | (np.abs(trend) < 1e-10)] = med if abs(med) > 1e-10 else 1.0
    flux_flat = flux_clean / trend
    return (time_clean, flux_flat, trend, flux_clean) if return_clean_flux else (time_clean, flux_flat, trend)



def make_event_id(tic_id, sector, start_time=None, dip_found=True):
    """Stable event identity; multiple dips in one sector stay distinct."""
    if not dip_found or start_time is None or not np.isfinite(float(start_time)):
        return f"TIC{int(tic_id)}_S{int(sector):04d}_NODIP"
    return f"TIC{int(tic_id)}_S{int(sector):04d}_T{float(start_time):.5f}"


# ═══════════════════════════ رسوم بيانية ══════════════════════════════════

def plot_candidate(time_raw, flux_raw, time_clean, flux_flat,
                   dip_info, asym_info, tic_id, sector, save_dir=None):
    """
    رسم بياني لمرشّح يعرض المنحنى قبل وبعد التنظيف مع تظليل الهبوط.

    Parameters
    ----------
    time_raw, flux_raw : arrays
        المنحنى الأصلي.
    time_clean, flux_flat : arrays
        المنحنى المنظّف.
    dip_info : dict
        معلومات الهبوط (من detect_dips).
    asym_info : dict
        معلومات اللاتماثل (A, t_ingress, t_egress).
    tic_id : int
        معرّف النجم.
    sector : int
        رقم القطاع.
    save_dir : str, optional
        مجلد الحفظ. الافتراضي: config.CANDIDATES_PLOTS_DIR.
    """
    import matplotlib.pyplot as plt

    if save_dir is None:
        save_dir = config.CANDIDATES_PLOTS_DIR
    os.makedirs(save_dir, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    fig.suptitle(
        f"TIC {tic_id} — Sector {sector} — A_time = {asym_info.get('A_time', asym_info.get('A', np.nan)):.4f}",
        fontsize=14, fontweight="bold"
    )

    # ─── المنحنى الأصلي ───
    ax1.plot(time_raw, flux_raw, "k.", ms=1, alpha=0.4, label="Raw flux")
    ax1.set_ylabel("Flux (raw)")
    ax1.set_title("Before detrending")
    ax1.legend(loc="upper right")

    # ─── المنحنى المنظّف ───
    ax2.plot(time_clean, flux_flat, "k.", ms=1, alpha=0.4, label="Flat flux")

    # تظليل منطقة الهبوط
    ax2.axvspan(
        dip_info["start_time"], dip_info["end_time"],
        alpha=0.25, color="red", label="Dip region"
    )
    # خطوط Ingress / Egress
    ax2.axvline(dip_info["start_time"], color="blue", ls="--", lw=1, label="Ingress start")
    ax2.axvline(dip_info["min_time"], color="green", ls="-", lw=1.5, label="Deepest point")
    ax2.axvline(dip_info["end_time"], color="orange", ls="--", lw=1, label="Egress end")

    ax2.set_xlabel("Time (BTJD)")
    ax2.set_ylabel("Relative flux")
    ax2.set_title("After detrending")
    ax2.legend(loc="upper right", fontsize=8)

    plt.tight_layout()

    st = dip_info.get("start_time", 0)
    fname = os.path.join(save_dir, f"TIC{tic_id}_S{sector:04d}_T{st:.2f}.png")
    plt.savefig(fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ Plot saved: {fname}")
    return fname


# ═══════════════════════════════ طباعة ════════════════════════════════════

def safe_print(text):
    """طباعة آمنة تتعامل مع مشاكل الترميز على Windows."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


def print_header(title):
    """طباعة عنوان مرحلة بتنسيق واضح."""
    line = "=" * 60
    safe_print(f"\n{line}")
    safe_print(f"  {title}")
    safe_print(f"{line}\n")
