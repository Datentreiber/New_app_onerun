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
    """
    Erzeuge Geometrie aus einem "place"-Namen.
    Reihenfolge:
      1) Versuch: GAUL Admin-Grenze Level 1 (z. B. 'Berlin, Germany').
      2) Fallback: geemap.geocode(name) – verträgt Nominatim-Dicts ODER ArcGIS-Objekte.

    Unterstützte Rückgaben:
      - Nominatim: List[dict] mit keys 'boundingbox' und/oder 'lat'/'lon'
      - ArcGIS (geocoder.arcgis): Objekt mit .bbox (W,S,E,N) und/oder .latlng (lat, lon) oder .json
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError("place.name must be a non-empty string.")
    place = name.strip()

    # 1) Admin-Grenze (GAUL Level 1): '<Region>, <Country>' → exakte Verwaltungseinheit
    try:
        parts = [p.strip() for p in place.split(",")]
        if len(parts) >= 2:
            region = parts[0]
            country = parts[-1]
            gaul = ee.FeatureCollection("FAO/GAUL/2015/level1")
            fc = gaul.filter(ee.Filter.And(
                ee.Filter.eq("ADM1_NAME", region),
                ee.Filter.eq("ADM0_NAME", country)
            ))
            # .first() kann None sein → in try/except abfangen
            candidate = fc.first()
            # Wenn keine Features, wirft geometry() unten
            geom = ee.Feature(candidate).geometry()
            # Sicherstellen, dass die Geometrie sich bilden lässt (bounds abfragen)
            _ = geom.bounds()
            return geom
    except Exception:
        # stiller Fallback auf Geocoding
        pass

    # 2) Geocoding via geemap (Provider-agnostisch)
    try:
        results = geemap.geocode(place)
    except Exception as ge:
        raise ValueError(f"Geocoding failed for '{place}': {ge}") from ge

    if not results:
        raise ValueError(f"No geocoding result for '{place}'.")

    best = results[0]

    # 2a) Nominatim: dict mit 'boundingbox', 'lat', 'lon'
    if isinstance(best, dict):
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
        raise ValueError(f"Geocoding (Nominatim) result for '{place}' lacks usable geometry.")

    # 2b) ArcGIS: Objekt mit häufig .bbox (W,S,E,N) und/oder .latlng (lat, lon) oder .json
    try:
        # bbox: erwartete Reihenfolge (W, S, E, N)
        bbox_attr = getattr(best, "bbox", None)
        if bbox_attr and len(bbox_attr) == 4:
            west, south, east, north = map(float, bbox_attr)
            _validate_lonlat(west, south)
            _validate_lonlat(east, north)
            if west < east and south < north:
                return ee.Geometry.Rectangle([west, south, east, north])

        # latlng: erwartete Reihenfolge (lat, lon)
        latlng_attr = getattr(best, "latlng", None)
        if latlng_attr and len(latlng_attr) == 2:
            lat, lon = float(latlng_attr[0]), float(latlng_attr[1])
            _validate_lonlat(lon, lat)
            return ee.Geometry.Point([lon, lat])

        # json: versuchen, bbox/extent zu lesen
        json_attr = getattr(best, "json", None)
        if isinstance(json_attr, dict):
            # einige Implementierungen haben 'bbox' oder 'bounds'
            jbbox = json_attr.get("bbox") or json_attr.get("bounds")
            if jbbox and len(jbbox) == 4:
                west, south, east, north = map(float, jbbox)
                _validate_lonlat(west, south)
                _validate_lonlat(east, north)
                if west < east and south < north:
                    return ee.Geometry.Rectangle([west, south, east, north])
            # extent-Objekt
            extent = json_attr.get("extent") or json_attr.get("Extents")
            if isinstance(extent, dict):
                xmin = float(extent.get("xmin"))
                ymin = float(extent.get("ymin"))
                xmax = float(extent.get("xmax"))
                ymax = float(extent.get("ymax"))
                _validate_lonlat(xmin, ymin)
                _validate_lonlat(xmax, ymax)
                if xmin < xmax and ymin < ymax:
                    return ee.Geometry.Rectangle([xmin, ymin, xmax, ymax])

        # location: (x,y) / (lon,lat)
        loc = getattr(best, "location", None)
        if isinstance(loc, dict) and "x" in loc and "y" in loc:
            lon, lat = float(loc["x"]), float(loc["y"])
            _validate_lonlat(lon, lat)
            return ee.Geometry.Point([lon, lat])

        # fallback: separate attributes x,y
        if hasattr(best, "x") and hasattr(best, "y"):
            lon, lat = float(getattr(best, "x")), float(getattr(best, "y"))
            _validate_lonlat(lon, lat)
            return ee.Geometry.Point([lon, lat])

    except Exception:
        # falls irgendein Access fehlschlägt, am Ende allgemeine Fehlermeldung
        pass

    raise ValueError(f"Geocoding (ArcGIS) result for '{place}' lacks usable geometry.")


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
