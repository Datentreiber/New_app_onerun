# NO2 Monthly — Map Setup & Geocode UI
def build_map_and_geocode(default_place: str = "Berlin, Germany", default_zoom: int = 8):
    # Create map
    m = Map(plugin_Draw=False, locate_control=False, fullscreen_control=False)
    try:
        m.add_basemap("CartoDB.Positron")
    except Exception:
        pass

    # Geocode text input
    place = st.text_input("Ort / Geocode (z. B. 'Berlin, Germany')", value=default_place)
    if place.strip():
        try:
            loc = geemap.geocode(place)
            lon, lat = loc[0]["lon"], loc[0]["lat"]
            m.set_center(lon, lat, default_zoom)
            folium.Marker(location=[lat, lon], tooltip=place).add_to(m)
            st.session_state["zoom_level"] = default_zoom
        except Exception as ge:
            st.warning(f"Geocoding fehlgeschlagen: {ge}")

    return m
