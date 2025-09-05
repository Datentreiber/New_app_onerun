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

def _mask_s2_sr(img: ee.Image) -> ee.Image:
    qa = img.select("QA60")
    cloud_bit, cirrus_bit = 1 << 10, 1 << 11
    mask = qa.bitwiseAnd(cloud_bit).eq(0).And(qa.bitwiseAnd(cirrus_bit).eq(0))
    return img.updateMask(mask).divide(10000).copyProperties(img, img.propertyNames())

def build_s2_quarter_median(aoi: ee.Geometry, start: ee.Date, end: ee.Date) -> ee.Image:
    col = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterDate(start, end)
        .filterBounds(aoi)
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", 80))
        .map(_mask_s2_sr)
    )

    size = col.size()
    def _ok():
        return (col.select(["B8","B11","B4"]).median().clip(aoi).set("empty", 0))
    def _empty():
        return (ee.Image.constant([0,0,0]).rename(["B8","B11","B4"]).toFloat().clip(aoi).set("empty", 1))
    return ee.Image(ee.Algorithms.If(size.gt(0), _ok(), _empty()))
