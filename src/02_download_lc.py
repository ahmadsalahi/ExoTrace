"""
02_download_lc.py — تحميل منحنيات الضوء من أرشيف MAST
======================================================
"""
import os
import sys
import argparse
import ast
import pandas as pd
import numpy as np
import lightkurve as lk
from tqdm import tqdm

# إضافة مسار المشروع الجذري
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src import utils


def parse_sectors(sectors_str):
    """تحليل سلسلة القطاعات واستخراج قائمة بأرقامها."""
    if pd.isna(sectors_str):
        return []
    if isinstance(sectors_str, str):
        try:
            parsed = ast.literal_eval(sectors_str)
            if isinstance(parsed, list):
                return [int(x) for x in parsed]
            elif isinstance(parsed, (int, float)):
                return [int(parsed)]
        except (ValueError, SyntaxError):
            return [int(x.strip()) for x in sectors_str.split(",") if x.strip().isdigit()]
    elif isinstance(sectors_str, (int, float)):
        return [int(sectors_str)]
    elif isinstance(sectors_str, list):
        return [int(x) for x in sectors_str]
    return []


def download_lightcurves(limit=None, retry_failed=False):
    """تنزيل منحنيات الضوء لجميع النجوم في العيّنة."""
    utils.print_header("تحميل منحنيات الضوء من MAST")
    utils.ensure_dirs()

    sample_file = utils.sample_path()
    if not os.path.exists(sample_file):
        print(f"خطأ: ملف العيّنة غير موجود — {sample_file}")
        return

    df = pd.read_csv(sample_file)
    if limit:
        df = df.head(limit)

    failures_file = os.path.join(config.LC_DIR, "download_failures.csv")
    failed_records = []

    stats = {"successful": 0, "failed": 0, "skipped": 0}

    for _, row in tqdm(df.iterrows(), total=len(df), desc="تحميل منحنيات الضوء"):
        tic_id = row.get("tic_id")
        if pd.isna(tic_id):
            continue
        tic_id = int(tic_id)

        sectors = parse_sectors(row.get("sectors"))

        for sector in sectors:
            if sector < config.SECTOR_MIN:
                continue

            cache_path = utils.lc_cache_path(tic_id, sector)
            if os.path.exists(cache_path):
                stats["skipped"] += 1
                continue

            try:
                # البحث بالمصدر المفضّل
                search = lk.search_lightcurve(
                    f"TIC {tic_id}", sector=sector,
                    mission="TESS", author=config.PREFERRED_AUTHOR,
                )

                # مصادر بديلة
                if not search or len(search) == 0:
                    for author in config.FALLBACK_AUTHORS:
                        search = lk.search_lightcurve(
                            f"TIC {tic_id}", sector=sector,
                            mission="TESS", author=author,
                        )
                        if search and len(search) > 0:
                            break

                if not search or len(search) == 0:
                    raise ValueError("No data found for any author")

                # تحميل
                lc = search.download()
                if lc is None:
                    raise ValueError("Download returned None")

                if isinstance(lc, lk.LightCurveCollection):
                    lc = lc[0]

                time = lc.time.value
                if hasattr(lc, "pdcsap_flux") and lc.pdcsap_flux is not None:
                    flux = lc.pdcsap_flux.value
                    flux_err = lc.pdcsap_flux_err.value
                else:
                    flux = lc.flux.value
                    flux_err = lc.flux_err.value

                # حفظ CSV
                lc_df = pd.DataFrame({"time": time, "flux": flux, "flux_err": flux_err})
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                lc_df.to_csv(cache_path, index=False)
                stats["successful"] += 1

            except Exception as e:
                stats["failed"] += 1
                failed_records.append({"tic_id": tic_id, "sector": sector, "error": str(e)})

    # حفظ تقرير الفشل
    if failed_records:
        fail_df = pd.DataFrame(failed_records)
        header = not os.path.exists(failures_file)
        fail_df.to_csv(failures_file, mode="a", header=header, index=False)

    print("\nإحصائيات التحميل:")
    print(f"  ✓ نجح: {stats['successful']}")
    print(f"  ✗ فشل: {stats['failed']}")
    print(f"  ⊘ مُتخطّى (محفوظ مسبقاً): {stats['skipped']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="تحميل منحنيات الضوء")
    parser.add_argument("--limit", type=int, help="الحد الأقصى لعدد النجوم")
    parser.add_argument("--retry-failed", action="store_true", help="إعادة المحاولة للفاشلة")
    args = parser.parse_args()
    download_lightcurves(limit=args.limit, retry_failed=args.retry_failed)
