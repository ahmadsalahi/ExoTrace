"""
07_reanalyze.py — إعادة تحليل المرشّحين المعروفين (TIC 229790952 و TIC 110969638)
=================================================================================
عبر جميع قطاعات TESS المتاحة بما فيها ما بعد القطاع 26.
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import lightkurve as lk
from tqdm import tqdm

# إضافة مسار المشروع الرئيسي
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src import utils

# مجلد رسوم إعادة التحليل
REANALYSIS_PLOTS = os.path.join(config.PLOTS_DIR, "reanalysis")


def _search_indices_by_priority(search):
    """Prefer deterministic TESS products (SPOC, then TESS-SPOC, then QLP) and shorter cadence."""
    author_rank = {"SPOC": 0, "TESS-SPOC": 1, "QLP": 2}
    rows = []
    table = getattr(search, "table", None)
    for i in range(len(search)):
        author = ""
        exptime = 1e12
        mission = ""
        try:
            if table is not None:
                if "author" in table.colnames:
                    author = str(table["author"][i])
                if "exptime" in table.colnames:
                    exptime = float(table["exptime"][i])
                if "mission" in table.colnames:
                    mission = str(table["mission"][i])
        except Exception:
            pass
        rows.append((author_rank.get(author.upper(), 9), exptime, mission, i))
    return [r[-1] for r in sorted(rows)]


def _sector_from_search_row(search, i):
    table = getattr(search, "table", None)
    try:
        if table is not None and "mission" in table.colnames:
            mission_str = str(table["mission"][i])
            return int(mission_str.split("Sector")[-1].strip())
    except Exception:
        pass
    return None


def analyze_candidate(candidate, sigma_thresh=None, min_duration=None, max_duration=None, asymmetry_min=None, detrend_window=None):
    """
    تحليل مرشّح واحد عبر جميع القطاعات المتاحة له في TESS.
    """
    tic_id = candidate["tic_id"]
    name = candidate["name"]
    utils.print_header(f"إعادة تحليل: {name}")

    # ─── البحث عن جميع القطاعات المتاحة ───
    try:
        search = lk.search_lightcurve(f"TIC {tic_id}", mission="TESS")
        _secs = {_sector_from_search_row(search, j) for j in range(len(search))}
        _secs.discard(None)
        print(f"منتجات متاحة: {len(search)} | قطاعات فريدة: {len(_secs) if _secs else 'غير محدد'}")
    except Exception as e:
        print(f"خطأ أثناء البحث: {e}")
        return []

    if len(search) == 0:
        print("لا توجد قطاعات.")
        return []

    results = []
    sector_data = {}  # لتخزين البيانات للرسم المقارن
    seen_sectors = set()

    for i in tqdm(_search_indices_by_priority(search), total=len(search), desc=f"قطاعات {name}"):
        try:
            # استخراج رقم القطاع أولاً قبل التنزيل لتجنب تكرار المعالجة
            sector = _sector_from_search_row(search, i)
            if sector is None and hasattr(search[i], "mission") and search[i].mission is not None:
                mission_str = str(search[i].mission[0]) if len(search[i].mission) > 0 else ""
                try:
                    sector = int(mission_str.split("Sector")[-1].strip())
                except (ValueError, IndexError):
                    pass

            # تحميل المنحنى
            lc = search[i].download()
            if lc is None:
                continue

            if sector is None:
                sector = getattr(lc, "sector", None)
            if sector is None:
                sector = i + 1

            # منع تكرار تحليل نفس القطاع أكثر من مرة
            if sector in seen_sectors:
                continue
            seen_sectors.add(sector)

            # استخراج المصفوفات
            time_raw = lc.time.value
            if hasattr(lc, "pdcsap_flux") and lc.pdcsap_flux is not None:
                flux_raw = lc.pdcsap_flux.value
            else:
                flux_raw = lc.flux.value

            # إزالة NaN
            mask = np.isfinite(time_raw) & np.isfinite(flux_raw)
            time_raw = time_raw[mask]
            flux_raw = flux_raw[mask]

            if len(time_raw) < 50:
                continue

            # ─── تنظيف ───
            time_clean, flux_flat, trend = utils.flatten_lightcurve(
                time_raw, flux_raw, window_days=detrend_window
            )

            if len(time_clean) < 50:
                continue

            # ─── حفظ المنحنيات للواجهة الأمامية ───
            try:
                import pandas as pd
                _p_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                lc_dir = os.path.join(_p_root, "data", "lightcurves")
                os.makedirs(lc_dir, exist_ok=True)
                
                # Raw
                pd.DataFrame({"time": time_raw, "flux": flux_raw}).to_csv(
                    os.path.join(lc_dir, f"TIC{tic_id}_S{sector:04d}.csv"), index=False
                )
                
                # Flat
                pd.DataFrame({"time": time_clean, "flux_flat": flux_flat, "trend": trend}).to_csv(
                    os.path.join(lc_dir, f"TIC{tic_id}_S{sector:04d}_flat.csv"), index=False
                )
            except Exception as e:
                print(f"Failed to save LC CSVs for UI: {e}")

            # ─── كشف الهبوطات ───
            dips = utils.detect_dips(time_clean, flux_flat, sigma_thresh=sigma_thresh, min_dur_hr=min_duration, max_dur_hr=max_duration)

            # حفظ للرسم المقارن
            sector_data[sector] = {
                "time": time_clean,
                "flux": flux_flat,
                "dips": dips,
            }

            if not dips:
                results.append({
                    "event_id": utils.make_event_id(tic_id, sector, None, False),
                    "tic_id": tic_id,
                    "sector": sector,
                    "dip_found": False,
                    "start_time": np.nan,
                    "end_time": np.nan,
                    "t0": np.nan,
                    "depth": np.nan,
                    "duration_hr": np.nan,
                    "A": np.nan,
                    "A_time": np.nan,
                    "A_shape": np.nan,
                    "A_area": np.nan,
                    "slope_ratio": np.nan,
                    "snr": 0.0,
                    "morphology_score": 0.0,
                    "gap_flag": False,
                    "morphology_valid": False,
                    "direction_agreement": True,
                    "dominance": "none",
                    "t_ingress": np.nan,
                    "t_egress": np.nan,
                    "classification": "No dip",
                })
            else:
                for dip in dips:
                    m_res = utils.compute_multimetric_asymmetry(
                        time_clean, flux_flat,
                        dip["start_idx"], dip["end_idx"], dip["min_idx"], asymmetry_min=asymmetry_min
                    )

                    results.append({
                        "event_id": utils.make_event_id(tic_id, sector, dip["start_time"], True),
                        "tic_id": tic_id,
                        "sector": sector,
                        "dip_found": True,
                        "start_time": dip["start_time"],
                        "end_time": dip["end_time"],
                        "t0": m_res["t0"],
                        "depth": m_res["depth"],
                        "duration_hr": dip["duration_hr"],
                        "A": m_res["A_time"],
                        "A_time": m_res["A_time"],
                        "A_shape": m_res["A_shape"],
                        "A_area": m_res["A_area"],
                        "slope_ratio": m_res["slope_ratio"],
                        "snr": m_res["snr"],
                        "morphology_score": m_res["morphology_score"],
                        "gap_flag": m_res["gap_flag"],
                        "morphology_valid": m_res["morphology_valid"],
                        "direction_agreement": m_res["direction_agreement"],
                        "dominance": m_res["dominance"],
                        "t_ingress": m_res["t_ingress"],
                        "t_egress": m_res["t_egress"],
                        "classification": m_res["classification"],
                    })

                    # رسم فردي
                    try:
                        dip_info = {k: dip[k] for k in dip}
                        asym_info = {
                            "A": m_res["A_time"],
                            "A_time": m_res["A_time"],
                            "t_ingress": m_res["t_ingress"],
                            "t_egress": m_res["t_egress"],
                        }
                        # Interactive charts are now used. No static plots generated.
                    except Exception:
                        pass

        except Exception as e:
            print(f"  خطأ — قطاع {i}: {e}")

    # ─── الحكم النهائي ───
    dips_found = [r for r in results if r["dip_found"]]
    sectors_with_dips = set(r["sector"] for r in dips_found)
    asym_dips = [r for r in dips_found if r["classification"] in ("positive_moderate", "positive_extreme", "moderate", "extreme")]

    print("\n" + "─" * 50)
    print(f"  الحكم النهائي لـ {name}")
    print("─" * 50)
    if len(sectors_with_dips) > 1 and len(asym_dips) > 1:
        print(f"  ✓ الإشارة اللامتماثلة تتكرر في {len(sectors_with_dips)} قطاعات")
        print(f"    → يتوافق مع تفسير المذنّب الخارجي")
    elif len(sectors_with_dips) == 1:
        print(f"  ⚠ الإشارة وُجدت في قطاع واحد فقط")
        print(f"    → لا توجد أدلة تكرار كافية؛ يلزم فحص المرشح دون ترجيح تفسير فيزيائي بعينه")
    else:
        print(f"  ✗ لم تُعثر على هبوطات لامتماثلة كافية")
        print(f"    → أدلة غير كافية")
    print("─" * 50)

    return results


def _comparison_plot(tic_id, sector_data):
    """
    رسم مقارن يعرض جميع القطاعات جنباً إلى جنب.
    """
    if not sector_data:
        return

    sectors = sorted(sector_data.keys())
    n = len(sectors)
    n_cols = min(3, n)
    n_rows = int(np.ceil(n / n_cols))

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 3.5 * n_rows))
    if n == 1:
        axes = np.array([axes])
    axes = np.atleast_1d(axes).flatten()

    for i, sector in enumerate(sectors):
        ax = axes[i]
        d = sector_data[sector]
        ax.plot(d["time"], d["flux"], "k.", ms=1, alpha=0.4)

        for dip in d["dips"]:
            ax.axvspan(dip["start_time"], dip["end_time"],
                       alpha=0.3, color="red")

        ax.set_title(f"Sector {sector}", fontsize=10)
        ax.set_xlabel("Time (BTJD)", fontsize=8)
        ax.set_ylabel("Rel. flux", fontsize=8)

    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])

    fig.suptitle(f"TIC {tic_id} — Multi-sector comparison", fontsize=13, y=1.02)
    plt.tight_layout()

    os.makedirs(REANALYSIS_PLOTS, exist_ok=True)
    out = os.path.join(REANALYSIS_PLOTS, f"TIC{tic_id}_comparison.png")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ رسم المقارنة: {out}")


def main():
    parser = argparse.ArgumentParser(description="إعادة تحليل المرشّحين المعروفين")
    parser.add_argument("--tic-id", type=int, default=None,
                        help="تحليل مرشّح واحد فقط بمعرّف TIC")
    parser.add_argument("--sigma", type=float, default=None, help="عتبة سيجما")
    parser.add_argument("--min-duration", type=float, default=None)
    parser.add_argument("--max-duration", type=float, default=None)
    parser.add_argument("--asymmetry-min", type=float, default=None)
    parser.add_argument("--detrend-window", type=float, default=None)
    args = parser.parse_args()

    utils.ensure_dirs()

    candidates = config.KNOWN_CANDIDATES
    if args.tic_id:
        cands = [c for c in candidates if c["tic_id"] == args.tic_id]
        if not cands:
            cands = [{"tic_id": args.tic_id, "name": f"TIC {args.tic_id}"}]
        candidates = cands

    all_results = []
    for cand in candidates:
        results = analyze_candidate(cand, sigma_thresh=args.sigma, min_duration=args.min_duration, max_duration=args.max_duration, asymmetry_min=args.asymmetry_min, detrend_window=args.detrend_window)
        all_results.extend(results)

    out_csv = utils.reanalysis_path()
    analyzed_tics = [c["tic_id"] for c in candidates]
    if os.path.exists(out_csv):
        try:
            old_df = pd.read_csv(out_csv)
            if "tic_id" in old_df.columns:
                old_df = old_df[~pd.to_numeric(old_df["tic_id"], errors="coerce").isin(analyzed_tics)]
        except Exception:
            old_df = pd.DataFrame()
    else:
        old_df = pd.DataFrame()

    new_df = pd.DataFrame(all_results)
    merged_df = pd.concat([old_df, new_df], ignore_index=True, sort=False) if not old_df.empty or not new_df.empty else pd.DataFrame()
    if not merged_df.empty:
        if "event_id" not in merged_df.columns:
            merged_df["event_id"] = merged_df.apply(
                lambda r: utils.make_event_id(r.get("tic_id", 0), r.get("sector", 0), r.get("start_time"), bool(r.get("dip_found", False))), axis=1
            )
        merged_df = merged_df.drop_duplicates(subset=["event_id"], keep="last")
    merged_df.to_csv(out_csv, index=False)
    print(f"\n✓ تم تحديث نتائج إعادة التحليل في: {out_csv} ({len(new_df)} سجل جديد)")


if __name__ == "__main__":
    main()
