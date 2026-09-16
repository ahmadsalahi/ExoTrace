"""
05_asymmetry.py — حساب معامل اللاتماثل وتصنيف الهبوطات المرشّحة
================================================================
"""
import os
import sys
import argparse
import pandas as pd
import numpy as np
from tqdm import tqdm

# إضافة مسار المشروع الرئيسي
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src import utils



def process_asymmetry(limit=None, asymmetry_min=None):
    """
    قراءة الهبوطات المكتشفة وحساب اللاتماثل لكل واحد منها.
    """
    utils.print_header("حساب معامل اللاتماثل وتصنيف المرشّحين")
    utils.ensure_dirs()

    dips_path = os.path.join(config.RESULTS_DIR, "dips_detected.csv")
    if not os.path.exists(dips_path):
        print(f"خطأ: ملف الهبوطات غير موجود — {dips_path}")
        print("شغّل 04_detect_dips.py أولاً.")
        return

    dips_df = pd.read_csv(dips_path)
    if limit:
        dips_df = dips_df.head(limit)

    results = []

    print(f"جاري حساب اللاتماثل لـ {len(dips_df)} هبوط...")

    for _, row in tqdm(dips_df.iterrows(), total=len(dips_df), desc="حساب اللاتماثل"):
        tic_id = int(row["tic_id"])
        sector = int(row["sector"])

        # مسار الملف المنظّف
        flat_path = os.path.join(
            config.LC_DIR, f"TIC{tic_id}_S{sector:04d}_flat.csv"
        )
        if not os.path.exists(flat_path):
            continue

        try:
            lc_df = pd.read_csv(flat_path)
            time = lc_df["time"].values
            flux = lc_df["flux_flat"].values

            start_idx = int(row["start_idx"])
            end_idx = int(row["end_idx"])
            min_idx = int(row["min_idx"])

            m_res = utils.compute_multimetric_asymmetry(
                time, flux, start_idx, end_idx, min_idx, asymmetry_min=asymmetry_min
            )

            event_id = utils.make_event_id(tic_id, sector, row["start_time"], True)
            results.append({
                "event_id": event_id,
                "tic_id": tic_id,
                "sector": sector,
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "min_time": row["min_time"],
                "t0": m_res["t0"],
                "depth": row["depth"],
                "duration_hr": row["duration_hr"],
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

        except Exception as e:
            print(f"  خطأ — TIC {tic_id} S{sector}: {e}")

    # ─── حفظ النتائج ───
    out_path = utils.candidates_raw_path()
    results_df = pd.DataFrame(results)
    if results_df.empty:
        results_df = pd.DataFrame(columns=[
            "event_id", "tic_id", "sector", "start_time", "end_time", "min_time", "t0",
            "depth", "duration_hr", "A", "A_time", "A_shape", "A_area", "slope_ratio",
            "snr", "morphology_score", "gap_flag", "morphology_valid", "direction_agreement",
            "dominance", "t_ingress", "t_egress", "classification"
        ])
    results_df.to_csv(out_path, index=False)
    if not results_df.empty:
        print(f"\n✓ تم حفظ {len(results_df)} مرشّح في: {out_path}")
        print("\nملخص التصنيفات:")
        for cls, cnt in results_df["classification"].value_counts().items():
            print(f"  {cls}: {cnt}")
    else:
        print(f"لم يتم حساب اللاتماثل لأي هبوط. تم مسح النتائج القديمة: {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="حساب معامل اللاتماثل")
    parser.add_argument("--limit", type=int, default=None, help="عدد الهبوطات (للتجربة)")
    parser.add_argument("--asymmetry-min", type=float, default=None)
    args = parser.parse_args()
    process_asymmetry(limit=args.limit, asymmetry_min=args.asymmetry_min)
