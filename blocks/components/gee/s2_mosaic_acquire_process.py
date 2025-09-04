# blocks/components/gee/s2_mosaic_acquire_process.py
"""
Purpose
-------
Sentinel-2 Quartalsmosaik erstellen:
- Quelle: COPERNICUS/S2_HARMONIZED
- Filter: Datum [start, end), CLOUDY_PIXEL_PERCENTAGE ≤ 10
- Transform: Reflexion auf 0..1 skalieren (divide(10000))
- Reduce: Median
- Optional: AOI-Clip (hier: clip(aoi))

Contracts
---------
def build_s2_quarter_median(aoi: ee.Geometry, start: ee.Date, end: ee.Date) -> ee.Image

Args
----
aoi : ee.Geometry
start, end : ee.Date

Returns
-------
ee.Image
  Quartals-Medianbild, geclippt auf AOI.

Side Effects
-----------
Keine.

Notes
-----
- CLOUDY_PIXEL_PERCENTAGE ≤ 10 und divide(10000) 1:1 aus der Vorlage. :contentReference[oaicite:2]{index=2}
"""

import ee

def build_s2_quarter_median(aoi: ee.Geometry, start: ee.Date, end: ee.Date) -> ee.Image:
    col = (
        ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
        .filterDate(start, end)
        .filterBounds(aoi)
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", 10))
        .map(lambda img: img.divide(10000))
    )
    img = col.median().clip(aoi)
    return img
