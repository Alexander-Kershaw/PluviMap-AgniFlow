from pathlib import Path
import zipfile

RAW_DIR = Path("data/cams_raw")
OUT_DIR = Path("data/cams_extracted")

OUT_DIR.mkdir(parents=True, exist_ok=True)

zips = sorted(RAW_DIR.glob("*.zip"))
print("Found zips:", len(zips))

for z in zips:
    day = z.stem.split("_")[-1]  # cams_aod550_YYYY-MM-DD
    day_dir = OUT_DIR / day
    day_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(z) as zf:
        zf.extractall(day_dir)

    print("Extracted:", z.name, "->", day_dir)
