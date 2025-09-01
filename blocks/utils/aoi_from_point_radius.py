# AOI Helper (Placeholder)
def aoi_from_point_radius(lat: float, lon: float, km: float = 5.0) -> dict:
    # Rückgabe als GeoJSON-ähnlicher Dict (nur Demo)
    return {
        "type": "Circle",
        "center": [lon, lat],
        "radius_km": km
    }
