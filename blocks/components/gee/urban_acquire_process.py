# blocks/components/gee/urban_acquire_process.py
"""
Purpose
-------
GHSL Built-up (JRC/GHSL/P2023A/GHS_BUILT_S) je Jahr laden, optional
Low-Value-Threshold-Maske anwenden, auf AOI clippen und (für Stats) Fläche
in km² aggregieren.

Contracts
---------
def ghsl_built_surface(year: int) -> ee.Image
def build_built_surface_layer(aoi: ee.Geometry, year: int, threshold: int | None = None) -> ee.Image
def builtup_km2(image: ee.Image, region: ee.Geometry) -> ee.Number

Args
----
aoi, region : ee.Geometry
year : int
threshold : int | None   (z. B. 1 → keep values > 1, selfMask)

Returns
-------
ee.Image (Layer) bzw. ee.Number (km²)

Side Effects
-----------
Keine.

Notes
-----
- Dataset, Bandname und typische Threshold-Maske (>1, selfMask) 1:1 aus Vorlagen. 
"""

import ee

_GHSL_PREFIX = "JRC/GHSL/P2023A/GHS_BUILT_S"  # :contentReference[oaicite:5]{index=5}

def ghsl_built_surface(year: int) -> ee.Image:
    """Lade GHSL Built Surface für ein Jahr, Band 'built_surface'."""
    return ee.Image(f"{_GHSL_PREFIX}/{int(year)}").select("built_surface")

def build_built_surface_layer(aoi: ee.Geometry, year: int, threshold: int | None = None) -> ee.Image:
    """Optional Threshold (>threshold) + selfMask und Clip auf AOI."""
    img = ghsl_built_surface(year)
    if threshold is not None:
        img = img.updateMask(img.gt(int(threshold))).selfMask()  # :contentReference[oaicite:6]{index=6}
    return img.clip(aoi)

def builtup_km2(image: ee.Image, region: ee.Geometry) -> ee.Number:
    """Summe der 'built_surface' (m²) in km² umrechnen (÷ 1e6)."""
    s = image.select("built_surface").reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=region,
        scale=100,
        maxPixels=1e13,
        tileScale=4,
    ).get("built_surface")  # :contentReference[oaicite:7]{index=7}
    return ee.Number(s).divide(1e6)
