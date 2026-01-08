from __future__ import annotations
from pathlib import Path
from datetime import date, timedelta
from termcolor import colored
import zipfile
import cdsapi
import os
os.environ["CDSAPI_RETRY_MAX"] = "20"
os.environ["CDSAPI_RETRY_WAIT"] = "10"

# Extracting from cams EAC4 for Canadian wildfire data
# For a solid smoke metric, extracting total aerosol optical depth 550nm
DATASET = "cams-global-reanalysis-eac4"
VARIABLE = "total_aerosol_optical_depth_550nm"

# NE US + SE Canada (Wildfire regions and not overwhelmingly large geographical area)
# [north, west, south, east] (regional bounding box covering NE US + SE Canada)
AREA = [50.0, -85.0, 37.0, -65.0]

# Manage director creation and paths 
RAW_DIR = Path("data/cams_raw")
OUT_DIR = Path("data/cams_daily")
RAW_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

TIMES = ["00:00", "06:00", "12:00", "18:00"]  # 4 frames per day (allows for some statistical summaries per day later on)


# Establish range of dates for wildfire
def daterange(d0: date, d1: date):
    d = d0
    while d <= d1:
        yield d
        d += timedelta(days=1)


def download_day(d: date) -> Path:
    #Download zip file containing multiple times for one date (refer to TIMES variable)
    out_zip = RAW_DIR / f"cams_aod550_{d.isoformat()}.zip"
    if out_zip.exists() and out_zip.stat().st_size > 0:
        print("Exists, skipping:", out_zip.name)
        return out_zip

# API client for structuring requests
    c = cdsapi.Client()
    request = {
        "variable": [VARIABLE],
        "date": [f"{d.isoformat()}/{d.isoformat()}"],
        "time": TIMES,
        "area": AREA,
        # ADS uses netcdf_zip format for aerosol optical depth variables
        "data_format": "netcdf_zip",
    }

    print("Requesting:", d.isoformat())
    c.retrieve(DATASET, request, str(out_zip))
    print("Saved:", out_zip)
    return out_zip


def extract_zip(zip_path: Path) -> list[Path]:
    # Extract .nc files from the returned zip into data/cams_daily/ directories
    extracted = []
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if name.lower().endswith(".nc"):
                out = OUT_DIR / name.split("/")[-1]
                if out.exists() and out.stat().st_size > 0:
                    extracted.append(out)
                    continue
                zf.extract(name, OUT_DIR)
                # if it extracted into subfolders should be normalized
                extracted_path = OUT_DIR / name
                if extracted_path.exists() and extracted_path != out:
                    extracted_path.rename(out)
                    # try removing empty dirs
                    try:
                        extracted_path.parent.rmdir()
                    except Exception:
                        pass
                extracted.append(out)
    return extracted


def main():
    start = date(2023, 6, 1) # June 1st 2023
    end = date(2023, 6, 11) # June 11 2023

    for d in daterange(start, end):
        z = download_day(d)
        files = extract_zip(z)
        print(colored(f"Extracted {len(files)} netCDF file(s) for {d.isoformat()}", "light_green"))


if __name__ == "__main__":
    main()
