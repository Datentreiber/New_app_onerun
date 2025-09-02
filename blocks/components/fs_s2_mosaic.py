# S2 Visual — Build quarterly median mosaic (cloud filter + reflectance scaling)
import ee
import streamlit as st

@st.cache_data(show_spinner=False)
def fetch_mosaic(start_iso: str, end_iso: str):
    """
    Returns a quarterly median Sentinel-2 image for [start_iso, end_iso).
    Processing:
      - Filter by date
      - CLOUDY_PIXEL_PERCENTAGE ≤ 10
      - Scale reflectance to 0..1 via divide(10000)
      - Median composite
    """
    col = (
        ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
        .filterDate(start_iso, end_iso)
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", 10))
        .map(lambda img: img.divide(10000))
    )
    img = col.median()
    return img
