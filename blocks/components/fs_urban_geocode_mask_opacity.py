# Urban Change — Geocode + Low-Value Mask + Opacity (Split 1980/2025)
import ee
import streamlit as st
import geemap.foliumap as geemap
import folium

def render_urban_geocode_mask_opacity():
    """Geocode→set_center(12); Maskenschwelle 1; selfMask; Opazitäts-Slider; Split 1980/2025; Colorbar."""
    Map = geemap.Map(center=[22.6, 114], zoom=10, basemap="SATELLITE")
    Map.add_basemap("CartoDB.PositronOnlyLabels")

    keyword = st.text_input("Search for a location:", "")
    if keyword:
        locations = geemap.geocode(keyword)
        if locations is not None and len(locations) > 0:
            str_locations = [str(g)[1:-1] for g in locations]
            location = st.selectbox("Select a location:", str_locations)
            loc_index = str_locations.index(location)
            selected_loc = locations[loc_index]
            lat, lng = selected_loc.lat, selected_loc.lng
            folium.Marker(location=[lat, lng], popup=location).add_to(Map)
            Map.set_center(lng, lat, 12)
            st.session_state["zoom_level"] = 12

    built_surface_1980 = ee.Image(f"{GHSL_PREFIX}/1980").select("built_surface")
    built_surface_2025 = ee.Image(f"{GHSL_PREFIX}/2025").select("built_surface")

    # Threshold mask (keep > 1) + selfMask as in the reference
    mask_threshold = 1
    bs1980_masked = built_surface_1980.updateMask(built_surface_1980.gt(mask_threshold)).selfMask()
    bs2025_masked = built_surface_2025.updateMask(built_surface_2025.gt(mask_threshold)).selfMask()

    opacity = st.slider("Layer opacity", 0.0, 1.0, 0.7, 0.05)
    left_layer  = geemap.ee_tile_layer(bs1980_masked, ghsl_vis, "Built Surface 1980", opacity=opacity)
    right_layer = geemap.ee_tile_layer(bs2025_masked, ghsl_vis, "Built Surface 2025", opacity=opacity)

    Map.split_map(left_layer, right_layer)
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
