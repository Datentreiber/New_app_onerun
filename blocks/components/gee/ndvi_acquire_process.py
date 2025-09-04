# blocks/components/gee/ndvi_acquire_process.py
"""
Purpose
-------
Baue eine ImageCollection, in der jedes Element der Median aller MODIS NDVI
Bilder mit identischem DOY (day-of-year) über das gesamte Archiv ist.

Contracts
---------
def build_ndvi_doy_composite(ref_year: int = 2019) -> ee.ImageCollection

Args
----
ref_year : int
    Referenzjahr zur Enumeration der DOYs.

Returns
-------
ee.ImageCollection
    Kollektion, deren Bilder nach DOY gruppiert und per Median reduziert sind.
    Jedes Bild trägt die Eigenschaft 'doy'.

Side Effects
------------
Keine.

Notes
-----
Logik 1:1 aus der Vorlage übernommen; Visualisierung/Paletten nicht enthalten.
"""

import ee

def build_ndvi_doy_composite(ref_year: int = 2019) -> ee.ImageCollection:
    """Median-per-DOY Composite für MODIS/061/MOD13A2 NDVI."""
    col = ee.ImageCollection("MODIS/061/MOD13A2").select("NDVI")

    def add_doy(img):
        doy = ee.Date(img.get("system:time_start")).getRelative("day", "year")
        return img.set("doy", doy)

    col = col.map(add_doy)
    distinct = col.filterDate(f"{ref_year}-01-01", f"{ref_year+1}-01-01")

    join_filter = ee.Filter.equals(leftField="doy", rightField="doy")
    saved_join = ee.Join.saveAll(matchesKey="doy_matches")
    joined = ee.ImageCollection(saved_join.apply(distinct, col, join_filter))

    def median_by_doy(img):
        doy_col = ee.ImageCollection.fromImages(img.get("doy_matches"))
        return doy_col.reduce(ee.Reducer.median()).copyProperties(img, ["doy"])

    comp = joined.map(median_by_doy)
    return comp
