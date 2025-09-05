# blocks/components/gee/aoi_from_spec.py
"""
Purpose
-------
Wandelt eine strukturierte AOI-Spezifikation (dict) deterministisch in ee.Geometry um.
Unterstützte Varianten:
  1) {"type":"bbox","bbox":[minLon,minLat,maxLon,maxLat]}
  2) {"type":"point_buffer","point":[lon,lat],"radius_km":int}
  3) {"type":"place","name":str,"radius_km":int?}
  4) {"type":"region",...} → optional; aktuell nicht unterstützt (ValueError)

Contracts
---------
def aoi_from_spec(spec: dict) -> ee.Geometry

Args
----
spec : dict
    Strukturierte AOI-Spezifikation (siehe Varianten).

Returns
-------
ee.Geometry
    Rechteck, Polygon oder Punkt (bei Buffer → bounds()).

Side Effects
------------
Keine (kein Streamlit, kein globaler State).

Raises
------
ValueError
    Bei nicht interpretierbaren/ungültigen Eingaben oder fehlenden Feldern.

Notes
-----
- Keine UI. Kein Freitext-Parser.
- "place" nutzt geemap.geocode(...) und bevorzugt die Bounding Box des Geocoders.
- Bei vorhandenem radius_km wird auf den Centroid gepuffert und .bounds() genutzt.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import ee
import geemap


def _validate_lonlat(lon: float, lat: float) -> None:
    if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
        raise ValueError(f"Invalid coordinates: lon={lon}, lat={lat}")


def _to_float_pair(value: List[Any]) -> Tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("Expected [lon, lat].")
    lon = float(value[0])
    lat = float(value[1])
    _validate_lonlat(lon, lat)
    return lon, lat


def _bbox_to_geometry(bbox: List[Any]) -> ee.Geometry:
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        raise ValueError("bbox must be [minLon, minLat, maxLon, maxLat].")
    min_lon = float(bbox[0])
    min_lat = float(bbox[1])
    max_lon = float(bbox[2])
    max_lat = float(bbox[3])
    _validate_lonlat(min_lon, min_lat)
    _validate_lonlat(max_lon, max_lat)
    if min_lon >= max_lon or min_lat >= max_lat:
        raise ValueError(f"Invalid bbox bounds: {(min_lon, min_lat, max_lon, max_lat)}")
    return ee.Geometry.Rectangle([min_lon, min_lat, max_lon, max_lat])


def _place_to_geometry(name: str) -> ee.Geometry:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("place.name must be a non-empty string.")
    try:
        results = geemap.geocode(name.strip(), provider="nominatim")
    except Exception as ge:
        raise ValueError(f"Geocoding failed for '{name}': {ge}") from ge
    if not results or not isinstance(results, list):
        raise ValueError(f"No geocoding result for '{name}'.")
    best = results[0]
    bbox = best.get("boundingbox")
    lat = best.get("lat")
    lon = best.get("lon")
    if bbox and len(bbox) == 4:
        # Nominatim: [south, north, west, east]
        south, north, west, east = map(float, bbox)
        _validate_lonlat(west, south)
        _validate_lonlat(east, north)
        if west < east and south < north:
            return ee.Geometry.Rectangle([west, south, east, north])
    if lat is not None and lon is not None:
        lon_f, lat_f = float(lon), float(lat)
        _validate_lonlat(lon_f, lat_f)
        return ee.Geometry.Point([lon_f, lat_f])
    raise ValueError(f"Geocoding result for '{name}' lacks usable geometry.")


def aoi_from_spec(spec: Dict[str, Any]) -> ee.Geometry:
    """
    Spec-Varianten (eine davon):
      {"type":"bbox","bbox":[minLon,minLat,maxLon,maxLat]}
      {"type":"point_buffer","point":[lon,lat],"radius_km":15}
      {"type":"place","name":"Shenzhen, China","radius_km":10}
      {"type":"region",...} → (optional) darf ValueError werfen, wenn nicht unterstützt
    """
    if not isinstance(spec, dict):
        raise ValueError("aoi_spec must be a dict.")
    if "type" not in spec:
        raise ValueError("aoi_spec requires 'type'.")

    t = str(spec["type"]).lower().strip()

    if t == "bbox":
        bbox = spec.get("bbox", None)
        geom = _bbox_to_geometry(bbox)
        return geom

    if t == "point_buffer":
        point = spec.get("point", None)
        radius_km = spec.get("radius_km", None)
        if radius_km is None:
            raise ValueError("point_buffer requires 'radius_km'.")
        lon, lat = _to_float_pair(point)
        radius_m = float(radius_km) * 1000.0
        pt = ee.Geometry.Point([lon, lat])
        return pt.buffer(radius_m).bounds()

    if t == "place":
        name = spec.get("name", None)
        if not name:
            raise ValueError("place requires 'name'.")
        geom = _place_to_geometry(name)
        radius_km = spec.get("radius_km", None)
        if radius_km is not None:
            try:
                radius_m = float(radius_km) * 1000.0
                centroid = geom.centroid()
                return centroid.buffer(radius_m).bounds()
            except Exception:
                return geom.buffer(float(radius_km) * 1000.0).bounds()
        return geom

    if t == "region":
        # Optional: aktuell nicht implementiert — bewusst klarer Fehler
        raise ValueError("aoi_spec type 'region' is not supported yet.")

    raise ValueError(f"Unsupported aoi_spec type '{t}'.")
