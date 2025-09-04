# blocks/components/gee/cool_spots_acquire_process.py
"""
Purpose
-------
GEE-Logik für 'cool_spots' (Sommer-Hitzeinseln):
- Landsat 8/9 Collection 2 Level 2 laden/mergen
- QA-Masken anwenden (QA_PIXEL Bits 1..5 == 0)
- LST in °C aus ST_B10 berechnen (Skalierung + Kelvin→°C)
- Sommer-Median bilden
- AOI-Clip

Contracts
---------
def mask_landsat_l2(img: ee.Image) -> ee.Image
def add_lst_celsius(img: ee.Image) -> ee.Image
def build_lst_image(aoi: ee.Geometry, start: ee.Date, end: ee.Date) -> ee.Image

Args
----
img : ee.Image
aoi : ee.Geometry
start, end : ee.Date

Returns
-------
ee.Image
    Medianbild der LST_C über Sommer, auf AOI geclippt.

Side Effects
------------
Keine.

Notes
-----
- QA-Bits, Formeln und Datasets 1:1 aus der Vorlage übernommen.
"""

import ee

def mask_landsat_l2(img: ee.Image) -> ee.Image:
    """
    Mask Landsat Collection 2 Level 2 image using QA_PIXEL:
    Bits: 1=dilated, 2=cirrus, 3=cloud, 4=cloud shadow, 5=snow → all must be 0.
    """
    qa = img.select("QA_PIXEL")
    cond = (
        qa.bitwiseAnd(1 << 1).eq(0)  # dilated
        .And(qa.bitwiseAnd(1 << 2).eq(0))  # cirrus
        .And(qa.bitwiseAnd(1 << 3).eq(0))  # cloud
        .And(qa.bitwiseAnd(1 << 4).eq(0))  # cloud shadow
        .And(qa.bitwiseAnd(1 << 5).eq(0))  # snow
    )
    return img.updateMask(cond)

def add_lst_celsius(img: ee.Image) -> ee.Image:
    """
    Compute LST in °C from ST_B10 (Kelvin scale factors):
      LST_K = ST_B10 * 0.00341802 + 149.0
      LST_C = LST_K - 273.15
    """
    lst_k = img.select("ST_B10").multiply(0.00341802).add(149.0)
    lst_c = lst_k.subtract(273.15).rename("LST_C")
    return img.addBands(lst_c)

def build_lst_image(aoi: ee.Geometry, start: ee.Date, end: ee.Date) -> ee.Image:
    """
    Merge Landsat 8/9 L2, mask by QA, compute LST_C band, take summer median, clip to AOI.
    """
    l8 = (
        ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        .filterDate(start, end)
        .filterBounds(aoi)
        .map(mask_landsat_l2)
        .map(add_lst_celsius)
    )
    l9 = (
        ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
        .filterDate(start, end)
        .filterBounds(aoi)
        .map(mask_landsat_l2)
        .map(add_lst_celsius)
    )
    merged = l8.merge(l9)
    lst_median = merged.select("LST_C").median().clip(aoi)
    return lst_median
