# Urban Change — Simple (1980 vs 2025) & Split-Select Varianten
import ee
import streamlit as st
import geemap.foliumap as geemap
import folium

def render_urban_simple():
    """Variant: 1980 vs 2025 Split-Map, colorbar horizontal."""
    Map = geemap.Map(center=[22.6, 114], zoom=10, basemap="SATELLITE")
    Map.add_basemap("CartoDB.PositronOnlyLabels")

    built_surface_1980 = ee.Image(f"{GHSL_PREFIX}/1980").select("built_surface")
    built_surface_2025 = ee.Image(f"{GHSL_PREFIX}/2025").select("built_surface")

    left_layer  = geemap.ee_tile_layer(built_surface_1980, ghsl_vis, "Built Surface 1980", opacity=0.6)
    right_layer = geemap.ee_tile_layer(built_surface_2025, ghsl_vis, "Built Surface 2025", opacity=0.6)

    Map.split_map(left_layer, right_layer)
    Map.add_colorbar(
        vis_params=ghsl_vis,
        label="Built-up area (m² per 100 m grid)",
        orientation="horizontal",
        background_color="white",
        font_size=12,
        position="bottomright",
    )
    Map.to_streamlit()

def render_urban_split_select():
    """Variant: frei wählbares linkes & rechtes Jahr in Split-Map, colorbar horizontal."""
    Map = geemap.Map(center=[22.6, 114], zoom=10, basemap="SATELLITE")
    Map.add_basemap("CartoDB.PositronOnlyLabels")

    years = [1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2030]
    layers = {
        f"Built Surface {year}": geemap.ee_tile_layer(
            ee.Image(f"{GHSL_PREFIX}/{year}").select("built_surface"),
            ghsl_vis, f"Built Surface {year}", opacity=0.6
        ) for year in years
    }

    col1, col2 = st.columns([4, 1])
    with col2:
        options = list(layers.keys())
        left  = st.selectbox("Select a left year", options, index=0)
        right = st.selectbox("Select a right year", options, index=9)
        Map.split_map(layers[left], layers[right])

    with col1:
        Map.add_colorbar(
            vis_params=ghsl_vis,
            label="Built-up area (m² per 100 m grid)",
            orientation="horizontal",
            background_color="white",
            font_size=12,
            position="bottomright",
        )
        Map.addLayerControl()
        Map.to_streamlit()
