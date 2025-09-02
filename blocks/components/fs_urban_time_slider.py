# Urban Change — Time Slider (single-year view)
import ee
import streamlit as st
import geemap.foliumap as geemap

def render_urban_time_slider():
    """Ein Jahr via select_slider, Einzel-Layer + Colorbar."""
    years = [1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2030]
    year = st.select_slider("Built-up year", options=years, value=1980)

    Map = geemap.Map(center=[22.6, 114], zoom=10, basemap="SATELLITE")
    Map.add_basemap("CartoDB.PositronOnlyLabels")

    img = ee.Image(f"{GHSL_PREFIX}/{year}").select("built_surface")
    Map.addLayer(img, ghsl_vis, f"Built Surface {year}", opacity=0.6)

    Map.add_colorbar(
        vis_params=ghsl_vis,
        label="Built-up area (m² per 100 m grid)",
        orientation="horizontal",
        background_color="white",
        font_size=12,
        position="bottomright",
    )
    Map.to_streamlit()
