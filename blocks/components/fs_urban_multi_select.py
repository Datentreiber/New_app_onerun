# Urban Change — Multi-Select (Layer-Stack)
import ee
import streamlit as st
import geemap.foliumap as geemap

def render_urban_multi_select():
    """Mehrere Jahre als Layer-Stack, Colorbar horizontal."""
    Map = geemap.Map(center=[22.6, 114], zoom=10, basemap="SATELLITE")
    Map.add_basemap("CartoDB.PositronOnlyLabels")

    row1_col1, row1_col2 = st.columns([3, 1])
    years = [1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2030]

    with row1_col2:
        selected_years = st.multiselect("Select a year", years)

    if selected_years:
        for y in selected_years:
            Map.addLayer(ee.Image(f"{GHSL_PREFIX}/{y}").select("built_surface"), ghsl_vis, f"Built Surface {y}", opacity=0.6)

        Map.add_colorbar(
            vis_params=ghsl_vis,
            label="Built-up area (m² per 100 m grid)",
            orientation="horizontal",
            background_color="white",
            font_size=12,
            position="bottomright",
        )
        with row1_col1:
            Map.to_streamlit()
    else:
        with row1_col1:
            Map.to_streamlit()
