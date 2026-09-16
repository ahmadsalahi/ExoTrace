"""
03_detrend.py — تنظيف منحنيات الضوء وإزالة التذبذب النجمي
==========================================================
"""
import os
import sys
import argparse
import pandas as pd
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from tqdm import tqdm

# إضافة مسار المشروع الرئيسي
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src import utils

# مجلد رسوم التنظيف
DETREND_PLOTS = os.path.join(config.PLOTS_DIR, "detrend")


def main():
    """تنظيف منحنيات الضوء المحمّلة وحفظ النسخ المسطّحة."""
    parser = argparse.ArgumentParser(description="تنظيف منحنيات الضوء")
    parser.add_argument("--limit", type=int, default=None, help="عدد النجوم (للتجربة)")
    parser.add_argument("--window-days", type=float, default=None, help="طول نافذة التنعيم بالأيام (افتراضي من settings.json)")
    parser.add_argument("--force", action="store_true", help="إعادة حساب الملفات حتى لو كانت موجودة")
    args = parser.parse_args()
    runtime_settings = config.load_runtime_settings()
    window_days = float(args.window_days if args.window_days is not None else runtime_settings["detrend_window"])

    utils.print_header("تنظيف منحنيات الضوء وإزالة التذبذب النجمي")
    utils.ensure_dirs()
    os.makedirs(DETREND_PLOTS, exist_ok=True)

    # قراءة العيّنة
    sample_file = utils.sample_path()
    if not os.path.exists(sample_file):
        print(f"خطأ: ملف العيّنة غير موجود — {sample_file}")
        return

    df_sample = pd.read_csv(sample_file)
    if args.limit:
        df_sample = df_sample.head(args.limit)

    processed = 0
    skipped = 0
    failed = 0

    for _, row in tqdm(df_sample.iterrows(), total=len(df_sample), desc="تنظيف المنحنيات"):
        tic_id = int(row["tic_id"])

        # تحليل القطاعات
        sectors_str = str(row.get("sectors", ""))
        if not sectors_str or sectors_str == "nan":
            continue
        sectors = [int(s.strip()) for s in sectors_str.split(",") if s.strip().isdigit()]

        for sector in sectors:
            lc_path = utils.lc_cache_path(tic_id, sector)
            flat_path = os.path.join(config.LC_DIR, f"TIC{tic_id}_S{sector:04d}_flat.csv")
            plot_path = os.path.join(DETREND_PLOTS, f"TIC{tic_id}_S{sector:04d}_detrend.png")

            meta_path = flat_path + ".meta.json"
            cache_ok = False
            if os.path.exists(flat_path) and os.path.exists(meta_path) and not args.force:
                try:
                    with open(meta_path, "r", encoding="utf-8") as mf:
                        meta = json.load(mf)
                    cache_ok = abs(float(meta.get("detrend_window", -1)) - window_days) < 1e-9
                except Exception:
                    cache_ok = False
            if cache_ok:
                skipped += 1
                continue

            # تحقق من وجود الملف الخام
            if not os.path.exists(lc_path):
                failed += 1
                continue

            try:
                df_lc = pd.read_csv(lc_path)
                if "time" not in df_lc.columns or "flux" not in df_lc.columns:
                    failed += 1
                    continue

                time = df_lc["time"].values
                flux = df_lc["flux"].values

                # تنظيف
                time_clean, flux_flat, trend, flux_clean = utils.flatten_lightcurve(
                    time, flux, window_days=window_days, return_clean_flux=True
                )

                if len(time_clean) < 10:
                    failed += 1
                    continue

                # حفظ البيانات المنظّفة
                df_flat = pd.DataFrame({
                    "time": time_clean,
                    "flux_flat": flux_flat,
                    "trend": trend,
                })
                df_flat.to_csv(flat_path, index=False)
                with open(meta_path, "w", encoding="utf-8") as mf:
                    json.dump({"detrend_window": window_days, "outlier_sigma": config.OUTLIER_SIGMA}, mf, indent=2)

                # No static diagnostic plots generated here anymore to save space.
                # Interactive Plotly charts are generated dynamically in the UI instead.

                processed += 1

            except Exception as e:
                print(f"\n  خطأ — TIC {tic_id} S{sector}: {e}")
                failed += 1

    print("\nنتائج التنظيف:")
    print(f"  ✓ تمت المعالجة: {processed}")
    print(f"  ⊘ مُتخطّى (موجود): {skipped}")
    print(f"  ✗ فشل: {failed}")


if __name__ == "__main__":
    main()
