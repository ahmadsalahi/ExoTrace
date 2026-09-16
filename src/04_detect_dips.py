"""
04_detect_dips.py — كشف الهبوطات المرشّحة في منحنيات الضوء المنظّفة
====================================================================
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


def process_dips(limit=None, sigma=None, min_duration=None, max_duration=None):
    """
    قراءة منحنيات الضوء المسطّحة واكتشاف الهبوطات المرشّحة.
    """
    utils.print_header("كشف الهبوطات المرشّحة في المنحنيات المنظّفة")
    utils.ensure_dirs()

    # قراءة عيّنة النجوم
    sample_file = utils.sample_path()
    if not os.path.exists(sample_file):
        print(f"خطأ: ملف العيّنة غير موجود — {sample_file}")
        return

    df_sample = pd.read_csv(sample_file)
    if limit:
        df_sample = df_sample.head(limit)

    all_dips = []
    processed = 0
    skipped = 0

    print(f"جاري فحص {len(df_sample)} نجم...")

    for _, row in tqdm(df_sample.iterrows(), total=len(df_sample), desc="كشف الهبوطات"):
        tic_id = int(row["tic_id"])

        # تحليل قائمة القطاعات
        sectors_str = str(row.get("sectors", ""))
        if not sectors_str or sectors_str == "nan":
            continue
        sectors = [int(s.strip()) for s in sectors_str.split(",") if s.strip().isdigit()]

        for sector in sectors:
            # مسار الملف المنظّف
            flat_path = os.path.join(
                config.LC_DIR, f"TIC{tic_id}_S{sector:04d}_flat.csv"
            )
            if not os.path.exists(flat_path):
                skipped += 1
                continue

            try:
                lc_df = pd.read_csv(flat_path)
                time = lc_df["time"].values
                flux_flat = lc_df["flux_flat"].values

                dips = utils.detect_dips(time, flux_flat, sigma_thresh=sigma, min_dur_hr=min_duration, max_dur_hr=max_duration)

                for dip in dips:
                    all_dips.append({
                        "tic_id": tic_id,
                        "sector": sector,
                        "start_time": dip["start_time"],
                        "end_time": dip["end_time"],
                        "min_time": dip["min_time"],
                        "depth": dip["depth"],
                        "duration_hr": dip["duration_hr"],
                        "start_idx": dip["start_idx"],
                        "end_idx": dip["end_idx"],
                        "min_idx": dip["min_idx"],
                        "n_points": dip.get("n_points"),
                    })
                processed += 1

            except Exception as e:
                print(f"  خطأ — TIC {tic_id} S{sector}: {e}")

    # ─── حفظ النتائج ───
    out_path = os.path.join(config.RESULTS_DIR, "dips_detected.csv")
    columns = ["tic_id", "sector", "start_time", "end_time", "min_time", "depth", "duration_hr", "start_idx", "end_idx", "min_idx", "n_points"]
    dips_df = pd.DataFrame(all_dips, columns=columns)
    dips_df.to_csv(out_path, index=False)
    if all_dips:
        print(f"\n✓ تم حفظ {len(dips_df)} هبوط مرشّح في: {out_path}")
        print(f"  منحنيات مُعالَجة: {processed} | مُتخطّاة: {skipped}")
        print("\nتوزيع الهبوطات حسب النجم:")
        print(dips_df["tic_id"].value_counts().to_string())
    else:
        print(f"لم يتم العثور على أي هبوطات مرشّحة. تم مسح النتائج القديمة: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="كشف الهبوطات المرشّحة")
    parser.add_argument("--limit", type=int, default=None, help="عدد النجوم (للتجربة)")
    parser.add_argument("--sigma", type=float, default=None)
    parser.add_argument("--min-duration", type=float, default=None)
    parser.add_argument("--max-duration", type=float, default=None)
    args = parser.parse_args()
    process_dips(limit=args.limit, sigma=args.sigma, min_duration=args.min_duration, max_duration=args.max_duration)
