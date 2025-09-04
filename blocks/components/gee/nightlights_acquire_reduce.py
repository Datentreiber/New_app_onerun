# blocks/components/gee/nightlights_acquire_reduce.py
"""
Purpose
-------
Reine GEE-/Datenlogik für VIIRS Nighttime Lights:
- Laden der VIIRS monthly Kollektion (Band 'avg_rad')
- Monatsbild aus Jahr+Monat ableiten
- JRC-Gewässermaske (occurrence>threshold) → Landmaske
- Zeitreihe (Mean über AOI) als Pandas DataFrame
- Pre/Post Bilddifferenz (absolut, prozentual)
- Blackout-Maske (großer %-Rückgang + niedrige absolute Radiance)

Contracts
---------
get_viirs_collection() -> ee.ImageCollection
month_image(col: ee.ImageCollection, year: int, month: int) -> ee.Image
jrc_non_water_mask(threshold: int = 30, dataset_id: str = 'JRC/GSW1_4/GlobalSurfaceWater') -> ee.Image
region_timeseries(col: ee.ImageCollection, aoi: ee.Geometry,
                  start_year:int, start_month:int, end_year:int, end_month:int,
                  scale:int=500) -> pandas.DataFrame
compute_change(pre_img: ee.Image, post_img: ee.Image) -> tuple[ee.Image, ee.Image]
blackout_mask(post_img: ee.Image, pct_img: ee.Image,
              pct_thresh: float=-70, abs_thresh: float=0.5) -> ee.Image

Side-effects
------------
Keine Streamlit-Abhängigkeiten, keine UI.
"""
from __future__ import annotations
from typing import Tuple
import datetime as dt
import ee
import pandas as pd

# 1:1 aus der Vorlage: bevorzugter Datensatz + Fallback. :contentReference[oaicite:1]{index=1}
VIIRS_IDS = [
    "NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG",  # stray-light corrected, gap-filled
    "NOAA/VIIRS/DNB/MONTHLY_V1/VCMCFG",
]

def get_viirs_collection() -> ee.ImageCollection:
    """Erstes verfügbares VIIRS-Monatsprodukt (Band 'avg_rad') zurückgeben."""
    last_err = None
    for ds in VIIRS_IDS:
        try:
            return ee.ImageCollection(ds).select("avg_rad")
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"Could not load VIIRS collection. Last error: {last_err}")

def month_image(col: ee.ImageCollection, year: int, month: int) -> ee.Image:
    """Monats-Mosaik (1. bis Folgemonat), 'system:time_start' auf Monatsstart."""
    start = ee.Date.fromYMD(int(year), int(month), 1)
    end = start.advance(1, "month")
    img = col.filterDate(start, end).mosaic().set("system:time_start", start)
    return ee.Image(img)

def jrc_non_water_mask(threshold: int = 30,
                       dataset_id: str = "JRC/GSW1_4/GlobalSurfaceWater") -> ee.Image:
    """Land=1, Wasser (occurrence>threshold) maskiert (0)."""
    gsw = ee.Image(dataset_id).select("occurrence")  # 0..100
    water = gsw.gt(int(threshold))
    nonwater = water.Not()
    return nonwater

def region_timeseries(col: ee.ImageCollection,
                      aoi: ee.Geometry,
                      start_year: int,
                      start_month: int,
                      end_year: int,
                      end_month: int,
                      scale: int = 500) -> pd.DataFrame:
    """
    Zeitreihe (Mean 'avg_rad') über AOI von [startY,startM]..[endY,endM] (inkl.).
    """
    start = ee.Date.fromYMD(int(start_year), int(start_month), 1)
    end = ee.Date.fromYMD(int(end_year), int(end_month), 1).advance(1, "month")
    ts_col = col.filterBounds(aoi).filterDate(start, end)

    def to_feature(img):
        mean = img.reduceRegion(ee.Reducer.mean(), aoi, scale=scale, maxPixels=1e13).get("avg_rad")
        return ee.Feature(None, {
            "date": ee.Date(img.get("system:time_start")).format("YYYY-MM"),
            "mean_rad": mean,
        })

    fc = ts_col.map(to_feature).filter(ee.Filter.notNull(["mean_rad"]))
    dates = fc.aggregate_array("date").getInfo()
    vals = fc.aggregate_array("mean_rad").getInfo()
    df = pd.DataFrame({"date": pd.to_datetime(dates), "mean_rad": vals})
    df = df.sort_values("date").reset_index(drop=True)
    return df

def compute_change(pre_img: ee.Image, post_img: ee.Image) -> Tuple[ee.Image, ee.Image]:
    """(absolute Δ, prozentuale Δ) zwischen 'avg_rad' der Bilder."""
    pre = pre_img.select("avg_rad")
    post = post_img.select("avg_rad")
    d = post.subtract(pre).rename("d_rad")
    eps = ee.Image.constant(1.0)
    pct = d.divide(pre.max(eps)).multiply(100).rename("pct_change")
    return d, pct

def blackout_mask(post_img: ee.Image, pct_img: ee.Image,
                  pct_thresh: float = -70, abs_thresh: float = 0.5) -> ee.Image:
    """Maske möglicher Blackouts: starker negativer %-Change + niedrige absolute Radiance."""
    cond = pct_img.lte(float(pct_thresh)).And(post_img.select("avg_rad").lte(float(abs_thresh)))
    return cond.selfMask().rename("blackout")
