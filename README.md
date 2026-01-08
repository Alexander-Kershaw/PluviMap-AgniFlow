
***
# PluviMap-AgniFlow 
***
**Wildfire Smoke Dispersion Explorer — 2023 Canadian Wildfires**

PluviMap-AgniFlow is an interactive geospatial dashboard for exploring the spatial and temporal evolution of wildfire smoke during the June 2023 Canadian wildfires.

The project uses CAMS Global Reanalysis aerosol data to visualise daily smoke dispersion, identify regions of increasing or decreasing aerosol loading, and animate plume evolution across North America during the key wildfire dates.

---

## What AgniFlow Dashboard Shows

- Daily wildfire smoke dispersion using Aerosol Optical Depth (AOD 550nm)
- Temporal evolution of smoke plumes
- Delta view highlighting where smoke increased or decreased versus the previous day
- Interactive Streamlit dashboard
- Raster overlays on web maps
- Animated GIF overview of the full event

This project is part of my **PluviMap** series, which applies a reusable and extendible geospatial analytics framework to extreme environmental events which I will continue to work on, extending to a variety of notable meteorological and atmopsheric events that have sufficient data.

---

## Data Sources

- **CAMS Global Reanalysis (EAC4)**  
  Copernicus Atmosphere Monitoring Service  
  Variable: Total aerosol optical depth at 550 nm

- Spatial reference system: **WGS84 (EPSG:4326)**

---

## Methods Overview

1. Download sub-daily CAMS AOD fields for June 1–11, 2023  
2. Aggregate sub-daily fields into daily mean AOD
3. Export daily rasters to GeoTIFF
4. Generate transparent PNG overlays for web mapping
5. Build animated GIF showing smoke plume evolution
6. Develop an interactive Streamlit dashboard with:
   - Day selector
   - Play mode animation
   - Absolute and delta AOD views

---

## Dashboard Features

- **Absolute AOD view**  
  Shows overall smoke/aerosol loading

- **AOD view (Delta Mode)**  
  Highlights daily changes:
  - Increase in aerosol loading
  - Decrease in aerosol loading

- **Overview GIF**  
  Quick visual summary of the entire event showing evolution of the smoke plume with the PNG raster image overlays

---

## Running Locally

```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```
***
