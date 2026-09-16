"""
01_build_sample.py — بناء عيّنة النجوم المتطورة
=================================================
يستخدم MAST Observations API لجلب النجوم المرصودة في قطاعات TESS،
ثم يفلتر حسب logg و Tmag لاختيار النجوم المتطورة.
"""
import os
import sys
import argparse
import pandas as pd
import numpy as np
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src import utils

try:
    from astroquery.mast import Observations, Catalogs
except ImportError:
    print("خطأ: astroquery غير مثبتة — pip install astroquery")
    sys.exit(1)


def get_sector_targets(sector):
    """جلب TIC IDs لجميع النجوم المرصودة في قطاع TESS معيّن."""
    try:
        obs = Observations.query_criteria(
            obs_collection="TESS",
            dataproduct_type="timeseries",
            sequence_number=sector,
        )
        if obs is None or len(obs) == 0:
            return set()

        tic_ids = set()
        for name in obs["target_name"]:
            name_str = str(name).strip()
            digits = "".join(c for c in name_str if c.isdigit())
            if digits:
                tic_ids.add(int(digits))
        return tic_ids

    except Exception as e:
        print(f"  خطأ في قطاع {sector}: {e}")
        return set()


def get_tic_bulk(tic_ids_batch):
    """جلب معلومات مجموعة نجوم دفعة واحدة من TIC."""
    results = {}
    try:
        # استعلام بالدفعة
        id_str = ",".join(str(x) for x in tic_ids_batch)
        cat = Catalogs.query_criteria(catalog="Tic", ID=id_str)
        if cat is not None and len(cat) > 0:
            for row in cat:
                try:
                    tic_id = int(row["ID"])
                    logg_val = row["logg"]
                    tmag_val = row["Tmag"]

                    logg = float(logg_val) if logg_val is not None and not np.ma.is_masked(logg_val) else None
                    tmag = float(tmag_val) if tmag_val is not None and not np.ma.is_masked(tmag_val) else None

                    if logg is not None and tmag is not None:
                        results[tic_id] = {
                            "logg": logg,
                            "teff": float(row["Teff"]) if row["Teff"] is not None and not np.ma.is_masked(row["Teff"]) else None,
                            "tmag": tmag,
                            "ra": float(row["ra"]) if row["ra"] is not None and not np.ma.is_masked(row["ra"]) else None,
                            "dec": float(row["dec"]) if row["dec"] is not None and not np.ma.is_masked(row["dec"]) else None,
                            "lumclass": str(row["lumclass"]) if row["lumclass"] is not None and not np.ma.is_masked(row["lumclass"]) else "",
                        }
                except Exception:
                    continue
    except Exception as e:
        # إذا فشلت الدفعة، جرّب واحد-واحد
        for tic_id in tic_ids_batch:
            try:
                cat = Catalogs.query_criteria(catalog="Tic", ID=tic_id)
                if cat and len(cat) > 0:
                    row = cat[0]
                    logg_val = row["logg"]
                    tmag_val = row["Tmag"]
                    logg = float(logg_val) if logg_val is not None and not np.ma.is_masked(logg_val) else None
                    tmag = float(tmag_val) if tmag_val is not None and not np.ma.is_masked(tmag_val) else None
                    if logg is not None and tmag is not None:
                        results[tic_id] = {
                            "logg": logg,
                            "teff": float(row["Teff"]) if row["Teff"] is not None and not np.ma.is_masked(row["Teff"]) else None,
                            "tmag": tmag,
                            "ra": float(row["ra"]) if row["ra"] is not None and not np.ma.is_masked(row["ra"]) else None,
                            "dec": float(row["dec"]) if row["dec"] is not None and not np.ma.is_masked(row["dec"]) else None,
                            "lumclass": str(row["lumclass"]) if row["lumclass"] is not None and not np.ma.is_masked(row["lumclass"]) else "",
                        }
            except Exception:
                continue
    return results


def build_sample(sectors, max_per_sector=None):
    """بناء العيّنة: قطاع-أولاً ثم فلترة بالمعايير النجمية."""
    utils.print_header("بناء عينة النجوم المتطورة")
    utils.ensure_dirs()

    # ─── الخطوة 1: جمع TIC IDs من كل قطاع ───
    all_stars = {}  # tic_id -> set of sectors

    for sector in tqdm(sectors, desc="جلب نجوم القطاعات"):
        tic_ids = get_sector_targets(sector)
        if max_per_sector and len(tic_ids) > max_per_sector:
            tic_ids = set(list(tic_ids)[:max_per_sector])

        print(f"  قطاع {sector}: {len(tic_ids)} نجم")

        for tid in tic_ids:
            if tid in all_stars:
                all_stars[tid].add(sector)
            else:
                all_stars[tid] = {sector}

    total_unique = len(all_stars)
    print(f"\nاجمالي النجوم الفريدة: {total_unique}")

    if total_unique == 0:
        print("لم يتم العثور على نجوم.")
        return

    # ─── الخطوة 2: جلب المعلومات النجمية وفلترة المتطورة ───
    print(f"جاري فلترة النجوم المتطورة (logg <= {config.LOGG_MAX}, Tmag <= {config.TMAG_MAX})...")

    final_rows = []
    tic_list = list(all_stars.keys())
    batch_size = 10

    for i in tqdm(range(0, len(tic_list), batch_size), desc="فلترة النجوم"):
        batch = tic_list[i:i + batch_size]
        info_dict = get_tic_bulk(batch)

        for tic_id, info in info_dict.items():
            if info["logg"] <= config.LOGG_MAX and info["tmag"] <= config.TMAG_MAX:
                final_rows.append({
                    "tic_id": tic_id,
                    "ra": info["ra"],
                    "dec": info["dec"],
                    "logg": info["logg"],
                    "teff": info["teff"],
                    "tmag": info["tmag"],
                    "lumclass": info["lumclass"],
                    "sectors": ",".join(str(s) for s in sorted(all_stars[tic_id])),
                })

    # ─── حفظ ───
    if final_rows:
        df = pd.DataFrame(final_rows)
        save_path = utils.sample_path()
        df.to_csv(save_path, index=False)
        print(f"\n{'='*50}")
        print(f"  ✓ تم حفظ {len(df)} نجم متطور")
        print(f"  المسار: {save_path}")
        print(f"  نطاق logg: {df['logg'].min():.2f} - {df['logg'].max():.2f}")
        print(f"  نطاق Tmag: {df['tmag'].min():.2f} - {df['tmag'].max():.2f}")
        print(f"{'='*50}")
    else:
        print("لم يتم العثور على نجوم متطورة تطابق المعايير.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="بناء عينة النجوم المتطورة")
    parser.add_argument("--sectors", type=str, default=None,
                        help="قطاعات محددة مفصولة بفواصل (مثال: 40,50,60)")
    parser.add_argument("--max-per-sector", type=int, default=None,
                        help="حد اعلى لعدد النجوم لكل قطاع (للتجربة)")
    args = parser.parse_args()

    if args.sectors:
        sectors = [int(s.strip()) for s in args.sectors.split(",")]
    else:
        sectors = list(range(config.SECTOR_MIN, config.SECTOR_MAX + 1))

    build_sample(sectors, max_per_sector=args.max_per_sector)
