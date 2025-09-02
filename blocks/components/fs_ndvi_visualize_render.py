# NDVI Timelapse — Build AOI, render map+GIF with month labels, error handling
import io
import requests
import ee
import streamlit as st
import geemap.foliumap as geemap
from datetime import datetime, timedelta

from fs_ndvi_geo_lists import WORLD_REGIONS, COUNTRIES
from fs_ndvi_doy_composite import build_ndvi_doy_composite
from fs_ndvi_label_overlay import label_gif_with_month

def render_ndvi_timelapse(aoi_type: str = "world_region"):
    """
    Full rendering pipeline:
      - Choose AOI by world region (wld_rgn) or by country (country_na)
      - Build median-per-DOY composite (ref_year=2019)
      - Visualize sequence, get GIF from EE, overlay month labels
      - Left: map with boundary + first-frame preview
      - Right: labeled animation
    """
    st.title("Vegetation Index Timelapse")

    # Fixed params (as reference)
    ref_year = 2019
    fps = 10
    dimensions = 600
    crs = "EPSG:3857"

    # Build composite and vis params
    comp, visParams = build_ndvi_doy_composite(ref_year=ref_year)

    # AOI selection and mask feature collection
    if aoi_type == "world_region":
        aoi_name = st.selectbox("Select a Continent", WORLD_REGIONS)
        mask_fc = (
            ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
            .filter(ee.Filter.eq("wld_rgn", aoi_name))
        )
        zoom_lvl = 3
    elif aoi_type == "country":
        aoi_name = st.selectbox("Select a Country", COUNTRIES)
        mask_fc = (
            ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
            .filter(ee.Filter.eq("country_na", aoi_name))
        )
        zoom_lvl = 6
    else:
        st.error("Unsupported AOI type.")
        st.stop()

    region = mask_fc.geometry().bounds()

    # Prepare sequence: visualize each DOY composite and clip to AOI
    rgbVis = comp.map(lambda img: img.visualize(**visParams).clip(mask_fc))
    gifParams = {
        "region": region,
        "dimensions": dimensions,
        "crs": crs,
        "framesPerSecond": fps,
    }

    # Layout
    left, right = st.columns([1, 1])

    # Build month labels from DOYs in the composited collection
    doys = comp.aggregate_array("doy").getInfo()
    months = []
    for d in doys:
        dt = datetime(ref_year, 1, 1) + timedelta(days=int(d))
        months.append(dt.strftime("%B"))

    # Left: map with boundary and first DOY frame
    with left:
        st.subheader("Map")
        coords = mask_fc.geometry().centroid().getInfo()["coordinates"]
        m = geemap.Map(center=[coords[1], coords[0]], zoom=zoom_lvl)
        boundary_style = mask_fc.style(color="black", fillColor="00000000", width=1)
        m.addLayer(boundary_style, {}, f"{aoi_name} boundary")
        first_frame = ee.Image(comp.first()).visualize(**visParams).clip(mask_fc)
        m.addLayer(first_frame, {}, "NDVI (first DOY frame)")
        m.to_streamlit()

    # Right: animation with month labels
    with right:
        st.subheader("Vegetation Animation")
        try:
            gif_url = rgbVis.getVideoThumbURL(gifParams)
            resp = requests.get(gif_url, timeout=60)
            resp.raise_for_status()
            raw_gif = io.BytesIO(resp.content)
            labeled = label_gif_with_month(raw_gif, months, fps=fps, xy=(10, 10))
            st.image(
                labeled,
                caption=f"NDVI median-per-DOY animation ({aoi_name}, MOD13A2)",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Failed to create animation: {e}")
            st.info("Tip: Make sure your Earth Engine account is enabled and you’re logged in.")

        # Helper expander
        with st.expander("What this app does"):
            st.markdown(
                """
- Loads **MODIS/061/MOD13A2 NDVI** and tags each image with its **day-of-year (DOY)**.
- Uses a **reference year** (default 2019) to get the set of DOYs.
- For each DOY, **collects all matching DOYs across the full collection** and reduces them with the **median**.
- Visualizes the sequence and renders a **GIF animation** (with month labels).
                """
            )
