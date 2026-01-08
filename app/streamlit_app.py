from __future__ import annotations

from pathlib import Path
from datetime import date, timedelta

import numpy as np
import rasterio
import folium
import matplotlib
import matplotlib.cm as mplcm
from folium.raster_layers import ImageOverlay

import streamlit as st
from streamlit_folium import st_folium

# Paths
RASTER_DIR = Path("outputs/rasters")
GIF_PATH = RASTER_DIR / "agniflow_aod_2023-06-01_to_2023-06-11.gif"

START = date(2023, 6, 1)
END = date(2023, 6, 11)


# Date helper
def daterange(d0: date, d1: date) -> list[str]:
    d = d0
    out = []
    while d <= d1:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


# Raster cache
@st.cache_data
def get_raster_bounds(tif_path: str) -> list[list[float]]:
    # Return folium bounds [[south, west], [north, east]] from GeoTIFF bounds
    with rasterio.open(tif_path) as src:
        b = src.bounds
        return [[b.bottom, b.left], [b.top, b.right]]


@st.cache_data
def load_png_as_rgba(png_path: str) -> np.ndarray:
    # Load PNG into (H, W, bands) uint8 array for Folium raster Image Overlay
    with rasterio.open(png_path) as src:
        img = src.read()  # (bands, H, W)
    img = np.moveaxis(img, 0, -1)  # (H, W, bands)
    if img.dtype != np.uint8:
        img = img.astype(np.uint8)
    return img


@st.cache_data
def raster_summary(tif_path: str) -> dict:
    # Compute quick summary stats on the selected rasters
    with rasterio.open(tif_path) as src:
        arr = src.read(1, masked=True).compressed()
    if arr.size == 0:
        return {"min": None, "max": None, "p50": None, "p90": None, "p99": None}
    return {
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "p50": float(np.percentile(arr, 50)),
        "p90": float(np.percentile(arr, 90)),
        "p99": float(np.percentile(arr, 99)),
    }

@st.cache_data
def load_tif_array(tif_path: str) -> np.ndarray:
    #Load single-band GeoTIFF as float32 with NaNs for nodata
    with rasterio.open(tif_path) as src:
        arr = src.read(1).astype("float32")
        nodata = src.nodata
        if nodata is not None:
            arr = np.where(arr == nodata, np.nan, arr)
    return arr


def delta_to_rgba(delta: np.ndarray, vlim: float) -> np.ndarray:
    
    # Convert delta array into RGBA uint8 using a diverging colormap to show differences in aerosol loading between adjacent days
    # negative = blue, positive = red, transparent where little to no change

    # Normalize to 0..1  and  0.5 mean zero change
    norm = (delta / vlim) * 0.5 + 0.5
    norm = np.clip(norm, 0.0, 1.0)

    cmap = mplcm.get_cmap("RdBu_r")
    rgba = cmap(norm)  # RGBA in 0..1

    # Transparency to hide tiny changes + NaNs
    alpha = np.ones(delta.shape, dtype="float32")
    alpha[np.isnan(delta)] = 0.0
    alpha[np.abs(delta) < (0.05 * vlim)] = 0.0  # transparency threshold

    rgba[..., 3] = rgba[..., 3] * alpha

    out = (rgba * 255).astype(np.uint8)
    return out


@st.cache_data
def build_delta_overlay(tif_today: str, tif_prev: str) -> np.ndarray:
    # Compute delta (current day - prev day) and convert to RGBA image
    a = load_tif_array(tif_today)
    b = load_tif_array(tif_prev)
    delta = a - b

    # symmetric limit based on percentiles
    finite = delta[np.isfinite(delta)]
    if finite.size == 0:
        vlim = 0.1
    else:
        vlim = float(np.percentile(np.abs(finite), 99))
        vlim = max(vlim, 0.1)  # to avoid too-small scaling

    return delta_to_rgba(delta, vlim)


# Map build
def make_map_for_day(day: str, show_raster: bool, opacity: float, view_mode: str, days: list[str]):
    tif_today = RASTER_DIR / f"agniflow_aod_{day}.tif"
    png_today = RASTER_DIR / f"agniflow_aod_{day}.png"

    if not tif_today.exists():
        st.error(f"Missing: {tif_today}")
        st.stop()

    m = folium.Map(location=[44.5, -75.5], zoom_start=5, tiles="OpenStreetMap")

    if show_raster:
        bounds = get_raster_bounds(str(tif_today))

        if view_mode == "Absolute AOD":
            if not png_today.exists():
                st.error(f"Missing: {png_today}")
                st.stop()
            img = load_png_as_rgba(str(png_today))
            name = f"AOD 550nm (daily mean) — {day}"

        else:
            # Delta mode: need previous day
            i = days.index(day)
            if i == 0:
                st.info("Delta AOD needs a previous day. Select a later date.")
                return m, str(tif_today)

            prev_day = days[i - 1]
            tif_prev = RASTER_DIR / f"agniflow_aod_{prev_day}.tif"
            if not tif_prev.exists():
                st.error(f"Missing previous day TIFF: {tif_prev}")
                st.stop()

            img = build_delta_overlay(str(tif_today), str(tif_prev))
            name = f"Delta AOD (today - yesterday) — {prev_day} → {day}"

        ImageOverlay(
            name=name,
            image=img,
            bounds=bounds,
            opacity=float(opacity),
            zindex=1,
            interactive=False,
            cross_origin=False,
        ).add_to(m)

    folium.LayerControl(collapsed=True).add_to(m)
    return m, str(tif_today)


# Dashboard
def main():
    st.set_page_config(page_title="PluviMap-AgniFlow — 2023 Wildfire Smoke", layout="wide")

    st.title("PluviMap-AgniFlow — 2023 Canadian Wildfire Smoke")
    st.write(
        "Daily mean Aerosol Optical Depth (AOD) at 550nm from CAMS reanalysis.\n\n"
        "Use the selector section to explore how the smoke plume evolves over time."
    )

    days = daterange(START, END)

    with st.sidebar:
        st.header("Controls")

        day = st.selectbox("Day", days, index=5)  # default ~June 6
        show_raster = st.checkbox("Show AOD raster overlay", value=True)
        opacity = st.slider("Overlay opacity", 0.1, 1.0, 0.65, 0.05)
        view_mode = st.selectbox("View", ["Absolute AOD", "Delta AOD vs previous day"], index=0) # delta AOP selector 

        st.markdown("---")
        st.subheader("Overview animation")
        if GIF_PATH.exists():
            st.caption("Daily mean AOD (June 1 -> 11, 2023)")
        else:
            st.caption("GIF not found")

    left, right = st.columns([2, 1])

    with left:
        st.subheader(f"Map — {day}")
        m, tif_path = make_map_for_day(day, show_raster, opacity, view_mode, days)
        st_folium(m, width=950, height=650)

    with right:
        st.subheader("AOD summary (selected day)")
        stats = raster_summary(tif_path)
        if stats["max"] is None:
            st.write("No valid pixels found.")
        else:
            st.write(
                f"- Min: **{stats['min']:.3f}**\n"
                f"- Median (p50): **{stats['p50']:.3f}**\n"
                f"- p90: **{stats['p90']:.3f}**\n"
                f"- p99: **{stats['p99']:.3f}**\n"
                f"- Max: **{stats['max']:.3f}**"
            )
            st.caption("AOD is unitless; higher values indicate more denseaerosol loading (hazier/smokier air).")

        st.markdown("---")
        st.subheader("Animation")
        if GIF_PATH.exists():
            st.image(str(GIF_PATH), caption="Daily mean AOD — June 1 to June 11, 2023")
        else:
            st.info("GIF not found. Expected at: outputs/rasters/agniflow_aod_2023-06-01_to_2023-06-11.gif")

        st.markdown("---")
        st.subheader("Summary")

        if view_mode == "Delta AOD vs previous day":
            st.caption("Delta view: positive = increase in aerosol loading; negative = decrease.")
        else:
            st.caption("Absolute view: higher AOD generally indicates hazier/smokier air.")


    st.markdown("---")
    with st.expander("How to read this"):
        st.write(
            "- **AOD 550nm** is a satellite-/model-derived measure of how much aerosols (like smoke) block/scatter light.\n"
            "- Higher AOD generally means **more smoke/aerosols** in the atmospheric column.\n"
            "- The overlay is a **daily mean** computed from sub-daily CAMS time steps.\n"
            "- The animation provides a quick view of plume evolution across the date range."
        )


if __name__ == "__main__":
    main()
