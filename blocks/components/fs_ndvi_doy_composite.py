# NDVI Timelapse — DOY-tagging, Join & median-per-DOY composite
import ee
import streamlit as st

def build_ndvi_doy_composite(ref_year: int = 2019):
    """
    Build an ImageCollection where each element is the median of all MODIS NDVI
    images sharing the same day-of-year (DOY) across the full archive.
    """
    col = ee.ImageCollection("MODIS/061/MOD13A2").select("NDVI")

    # Tag each image with its 'doy' (0-based day from year's start)
    def add_doy(img):
        doy = ee.Date(img.get("system:time_start")).getRelative("day", "year")
        return img.set("doy", doy)

    col = col.map(add_doy)

    # Use a single reference year to enumerate distinct DOYs
    distinct = col.filterDate(f"{ref_year}-01-01", f"{ref_year+1}-01-01")

    # Join by equal 'doy' between the distinct and the full collection
    join_filter = ee.Filter.equals(leftField="doy", rightField="doy")
    saved_join = ee.Join.saveAll(matchesKey="doy_matches")
    joined = ee.ImageCollection(saved_join.apply(distinct, col, join_filter))

    # Reduce all matches per DOY to a single median image
    def median_by_doy(img):
        doy_col = ee.ImageCollection.fromImages(img.get("doy_matches"))
        return doy_col.reduce(ee.Reducer.median()).copyProperties(img, ["doy"])

    comp = joined.map(median_by_doy)

    # Visualization parameters exactly like the reference
    visParams = {
        "min": 0.0,
        "max": 9000.0,
        "palette": [
            "FFFFFF","CE7E45","DF923D","F1B555","FCD163","99B718","74A901",
            "66A000","529400","3E8601","207401","056201","004C00","023B01",
            "012E01","011D01","011301"
        ],
    }
    return comp, visParams
