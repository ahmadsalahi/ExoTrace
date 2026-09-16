"""
06_validate.py — التحقق من المرشّحين عبر SIMBAD والفحص البصري
==============================================================
"""
import os
import sys
import argparse
import warnings
import pandas as pd
import numpy as np
from tqdm import tqdm

warnings.filterwarnings("ignore", module="astroquery")

# إضافة مسار المشروع الرئيسي
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src import utils

# محاولة استيراد astroquery
try:
    from astroquery.simbad import Simbad
    custom_simbad = Simbad()
    custom_simbad.add_votable_fields("otype")
    SIMBAD_AVAILABLE = True
except ImportError:
    SIMBAD_AVAILABLE = False
    print("تحذير: astroquery غير مثبتة — سيتم تخطي فحص SIMBAD.")


def check_simbad(tic_id):
    """
    الاستعلام من SIMBAD عن نوع النجم والتحقق من كونه ثنائياً أو متغيراً.

    Returns: (otype, name, status)
    """
    if not SIMBAD_AVAILABLE:
        return "simbad_unavailable", "N/A", "simbad_unavailable"

    try:
        result = custom_simbad.query_object(f"TIC {tic_id}")
        if result is None:
            return "unknown", "unknown", "passed"

        otype_raw = result["OTYPE"][0]
        name_raw = result["MAIN_ID"][0]
        otype = otype_raw.decode("utf-8") if isinstance(otype_raw, bytes) else str(otype_raw)
        name = name_raw.decode("utf-8") if isinstance(name_raw, bytes) else str(name_raw)

        otype_up = otype.upper()
        if "EB" in otype_up or "ALGOL" in otype_up or "ECL" in otype_up:
            return otype, name, "known_binary"
        elif "V*" in otype_up or "VAR" in otype_up or "PULS" in otype_up:
            return otype, name, "known_variable"
        else:
            return otype, name, "passed"

    except Exception:
        return "error", "error", "simbad_unavailable"


def validate_candidates(no_plots=False):
    """
    التحقق من المرشّحين الأوليين وتصنيف حالتهم.
    """
    utils.print_header("التحقق من صحة المرشّحين")
    utils.ensure_dirs()

    raw_path = utils.candidates_raw_path()
    if not os.path.exists(raw_path):
        print(f"خطأ: ملف المرشّحين غير موجود — {raw_path}")
        print("شغّل 05_asymmetry.py أولاً.")
        return

    df = pd.read_csv(raw_path)

    # تصفية: فقط المرشّحين بلاتماثل (إيجابي أو معكوس) مع استبعاد غير المؤكدين
    if "classification" in df.columns:
        valid_classes = [
            "positive_extreme", "positive_moderate",
            "reverse_moderate", "reverse_extreme",
            "moderate", "extreme"
        ]
        df_filtered = df[df["classification"].isin(valid_classes)].copy()
    else:
        df_filtered = df.copy()

    total = len(df_filtered)
    print(f"مرشّحون للتحقق: {total}")

    if total == 0:
        out_path = utils.candidates_validated_path()
        df_filtered.to_csv(out_path, index=False)
        print(f"لا يوجد مرشّحون — تم مسح النتائج القديمة: {out_path}")
        return

    # أعمدة جديدة
    df_filtered["simbad_otype"] = ""
    df_filtered["simbad_name"] = ""
    df_filtered["edge_flag"] = False
    df_filtered["validation_status"] = ""

    stats = {"passed": 0, "known_binary": 0, "known_variable": 0,
             "edge_effect": 0, "check_manually": 0, "simbad_unavailable": 0}

    for idx, row in tqdm(df_filtered.iterrows(), total=total, desc="التحقق"):
        try:
            tic_id = int(row["tic_id"])
            sector = int(row["sector"])

            # ─── 1. استعلام SIMBAD ───
            otype, name, simbad_status = check_simbad(tic_id)
            df_filtered.at[idx, "simbad_otype"] = otype
            df_filtered.at[idx, "simbad_name"] = name

            # ─── 2. فحص حافة القطاع ───
            raw_lc_path = utils.lc_cache_path(tic_id, sector)
            edge_flag = False
            status = simbad_status

            if os.path.exists(raw_lc_path):
                lc_raw = pd.read_csv(raw_lc_path)
                t = lc_raw["time"].values
                t_start = np.nanmin(t)
                t_end = np.nanmax(t)
                dip_center = row.get("t0", (row["start_time"] + row["end_time"]) / 2.0)

                if (dip_center - t_start < config.EDGE_MARGIN_DAYS) or (t_end - dip_center < config.EDGE_MARGIN_DAYS):
                    edge_flag = True
                    status = "edge_effect"
            else:
                status = "check_manually"

            df_filtered.at[idx, "edge_flag"] = edge_flag
            df_filtered.at[idx, "validation_status"] = status
            stats[status] = stats.get(status, 0) + 1

            # ─── 3. رسم بياني ───
            if not no_plots and os.path.exists(raw_lc_path):
                flat_path = os.path.join(
                    config.LC_DIR, f"TIC{tic_id}_S{sector:04d}_flat.csv"
                )
                if os.path.exists(flat_path):
                    try:
                        lc_raw = pd.read_csv(raw_lc_path)
                        lc_flat = pd.read_csv(flat_path)

                        dip_info = {
                            "start_time": row["start_time"],
                            "end_time": row["end_time"],
                            "min_time": row["min_time"],
                            "start_idx": int(row.get("start_idx", 0)),
                            "end_idx": int(row.get("end_idx", 0)),
                            "min_idx": int(row.get("min_idx", 0)),
                            "depth": row["depth"],
                            "duration_hr": row["duration_hr"],
                        }
                        asym_info = {
                            "A": row.get("A_time", row.get("A", 0)),
                            "A_time": row.get("A_time", row.get("A", 0)),
                            "t_ingress": row.get("t_ingress", 0),
                            "t_egress": row.get("t_egress", 0),
                        }

                        utils.plot_candidate(
                            lc_raw["time"].values, lc_raw["flux"].values,
                            lc_flat["time"].values, lc_flat["flux_flat"].values,
                            dip_info, asym_info, tic_id, sector,
                        )
                    except Exception:
                        pass  # تجاهل أخطاء الرسم

        except Exception:
            df_filtered.at[idx, "validation_status"] = "check_manually"
            stats["check_manually"] = stats.get("check_manually", 0) + 1

    # ─── حفظ النتائج ───
    out_path = utils.candidates_validated_path()
    df_filtered.to_csv(out_path, index=False)

    print(f"\n✓ تم الحفظ في: {out_path}")
    print("\n" + "=" * 45)
    print("  ملخص التحقق")
    print("=" * 45)
    for label, key in [
        ("اجتاز التحقق (Passed)", "passed"),
        ("ثنائي معروف (Known Binary)", "known_binary"),
        ("متغيّر معروف (Known Variable)", "known_variable"),
        ("تأثير حافة (Edge Effect)", "edge_effect"),
        ("SIMBAD غير متاح", "simbad_unavailable"),
        ("يحتاج فحص يدوي", "check_manually"),
    ]:
        print(f"  {label}: {stats.get(key, 0)}")
    print("=" * 45)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="التحقق من المرشّحين")
    parser.add_argument("--no-plots", action="store_true", help="تخطي الرسوم البيانية")
    args = parser.parse_args()
    validate_candidates(no_plots=args.no_plots)
