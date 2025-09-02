# S2 Visual — Map Setup & Geocode UI
import streamlit as st
import geemap.foliumap as geemap
import folium

def build_map_with_geocode(default_center=(52.517057, 3.400917), default_zoom=10):
    """
    Create a map with SATELLITE basemap and labels overlay.
    Provide a text box for geocoding; on selection, add a marker and re-center at zoom 12.
    """
    lat0, lon0 = default_center
    Map = geemap.Map(center=[lat0, lon0], zoom=default_zoom, basemap="SATELLITE")
    try:
        Map.add_basemap("CartoDB.PositronOnlyLabels")
    except Exception:
        pass

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

    return Map
