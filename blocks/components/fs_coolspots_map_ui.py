# Cool Spots (LST) — Map Setup & Geocode UI (+ AOI from point & radius)

import streamlit as st
import ee
import geemap
from geemap.foliumap import Map
import folium

def build_map_and_aoi(default_place: str = "Shenzhen, China", default_zoom: int = 12, radius_km: int = 15):
    """
    Create a folium-based map, geocode a place name, place a marker,
    set map center and create an AOI polygon from point+radius (bounds()).
    """
    # Create base map: SATELLITE with labels overlay, as per reference
    m = Map(plugin_Draw=False, locate_control=False, fullscreen_control=False)
    try:
        m.add_basemap("SATELLITE")  # Esri.WorldImagery
        m.add_basemap("CartoDB.PositronOnlyLabels")  # labels-only overlay
    except Exception:
        pass

    # Text input for geocoding (exact label)
    keyword = st.text_input("Search for a location:", "")

    place_to_geocode = keyword.strip() if keyword.strip() else default_place
    lon, lat = None, None
    try:
        loc = geemap.geocode(place_to_geocode)
        lon, lat = float(loc[0]["lon"]), float(loc[0]["lat"])
        m.set_center(lon, lat, default_zoom)
        folium.Marker(location=[lat, lon], tooltip=place_to_geocode).add_to(m)
        st.session_state["zoom_level"] = default_zoom
    except Exception as ge:
        st.warning(f"Geocoding failed: {ge}. Falling back to default center.")
        # Fallback to a default center if not already set
        if lon is None or lat is None:
            lon, lat = 114.0579, 22.5431  # Shenzhen
            m.set_center(lon, lat, default_zoom)
            st.session_state["zoom_level"] = default_zoom

    # AOI from point + radius
    RADIUS_M = int(radius_km) * 1000
    point = ee.Geometry.Point([lon, lat])
    aoi = point.buffer(RADIUS_M).bounds()

    return m, (lon, lat), aoi
