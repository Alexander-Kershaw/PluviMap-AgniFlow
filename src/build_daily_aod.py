from __future__ import annotations 

from pathlib import Path
from datetime import date, timedelta
from termcolor import colored

import numpy as np
import pandas as pd
import xarray as xr
import rioxarray 
import rasterio
import matplotlib.pyplot as plt
from PIL import Image


NC_DIR = Path("data/cams_extracted") # Path to daily atmospheric data (for wildfire Canadian region)
OUT_RASTERS = Path("outputs/rasters") 
OUT_RASTERS.mkdir(parents=True, exist_ok=True)

START = date(2023, 6, 1)
END = date(2023, 6, 11)

# AOD (aerosol optical depth) is unitless
# Specifing bounds for AOD display as PNG
PNG_VMIN = 0.0
PNG_VMAX = 1.5 

def daterange(d0: date, d1: date):
    d = d0
    while d <= d1:
        yield d
        d += timedelta(days=1)


def find_var_name(ds: xr.Dataset) -> str:
    # Find the AOD variable inside a CAMS EAC4 file

    for cand in ["total_aerosol_optical_depth_550nm", "aod550", "aod", "AOD550"]:
        if cand in ds.data_vars:
            return cand

    # pick the first data_var
    if len(ds.data_vars) == 1:
        return list(ds.data_vars)[0]

    raise ValueError(f"Could not determine AOD variable. data_vars={list(ds.data_vars)}")

# Load each daily .nc file
def load_day_file(d: date) -> Path:
    p = NC_DIR / d.isoformat() / "data_sfc.nc"
    if not p.exists():
        raise FileNotFoundError(f"Missing: {p}")
    return p


def to_daily_mean_aod(nc_path: Path) -> xr.DataArray:
    ds = xr.open_dataset(nc_path)

    var = find_var_name(ds)
    da = ds[var]

    # Average over time steps (4 per day)
    if "time" in da.dims:
        da = da.mean("time")

    # Normalize coordinate names for rioxarray
    rename = {}
    if "longitude" in da.coords: rename["longitude"] = "x"
    if "latitude" in da.coords:  rename["latitude"] = "y"
    if "lon" in da.coords:       rename["lon"] = "x"
    if "lat" in da.coords:       rename["lat"] = "y"
    da = da.rename(rename)

    if da.y[0] < da.y[-1]:
        da = da.sortby("y", ascending=False)

    da = da.rio.set_spatial_dims(x_dim="x", y_dim="y").rio.write_crs("EPSG:4326")
    da = da.rename("aod_550_daily_mean")
    da.attrs["units"] = "1"
    return da


# Export geotiff 
def export_geotiff(da: xr.DataArray, out_tif: Path):
    da.rio.to_raster(out_tif)

# PNG from geotiff
def export_png_from_tif(tif_path: Path, png_path: Path, vmin: float, vmax: float):
    with rasterio.open(tif_path) as src:
        arr = src.read(1).astype("float32")
        nodata = src.nodata
        if nodata is not None:
            arr = np.where(arr == nodata, np.nan, arr)

    # Transparent where very low AOD (clear air with little to no smoke)
    alpha = np.where(np.isfinite(arr) & (arr > 0.05), 1.0, 0.0)

    scaled = (arr - vmin) / (vmax - vmin)
    scaled = np.clip(scaled, 0, 1)

    fig = plt.figure(figsize=(6, 6), dpi=200)
    ax = plt.axes([0, 0, 1, 1])
    ax.set_axis_off()

    im = ax.imshow(scaled, interpolation="nearest", vmin=0, vmax=1, alpha=alpha)
    im.set_cmap("magma")  # good for aerosols/smoke

    plt.savefig(png_path, transparent=True, bbox_inches="tight", pad_inches=0)
    plt.close(fig)

# Animate evolution of AOD rasters showing wildfire smoke movement
def build_gif(png_paths: list[Path], out_gif: Path, duration_ms: int = 600):
    frames = [Image.open(p).convert("RGBA") for p in png_paths]
    frames[0].save(
        out_gif,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        disposal=2,
    )


def main():
    out_pngs = []


    for d in daterange(START, END):
        nc = load_day_file(d)
        print(d.isoformat(), "->", nc)

        da = to_daily_mean_aod(nc)

        out_tif = OUT_RASTERS / f"agniflow_aod_{d.isoformat()}.tif"
        out_png = OUT_RASTERS / f"agniflow_aod_{d.isoformat()}.png"

        export_geotiff(da, out_tif)
        export_png_from_tif(out_tif, out_png, PNG_VMIN, PNG_VMAX)

        out_pngs.append(out_png)
        print("Wrote:", out_tif.name, "and", out_png.name)


    out_gif = OUT_RASTERS / f"agniflow_aod_{START.isoformat()}_to_{END.isoformat()}.gif"
    build_gif(out_pngs, out_gif, duration_ms=600)
    print("Wrote GIF:", out_gif.resolve())


if __name__ == "__main__":
    main()
