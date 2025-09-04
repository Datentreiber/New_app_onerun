# blocks/components/visual/ndvi_timelapse_panel.py
"""
Purpose
-------
Rendert ein NDVI-Timelapse-Panel mit (links) Karten-Vorschau und (rechts)
animiertem GIF. Keine fest verdrahteten Paletten/Min/Max: alles über vis_params.

Contracts
---------
def render_ndvi_timelapse_panel(
    m,
    comp,                 # ee.ImageCollection (median-per-DOY)
    aoi,                  # ee.Geometry
    vis_params: dict,
    ref_year: int,
    fps: int = 10,
    dimensions: int = 600,
    crs: str = "EPSG:3857",
    left_title: str = "Map",
    right_title: str = "Vegetation Animation",
    label_xy: tuple[int,int] = (10, 10),
    caption: str | None = None,
) -> None

Args
----
m : geemap.foliumap.Map
comp : ee.ImageCollection
aoi : ee.Geometry
vis_params : Dict[str, Any]
ref_year : int
fps, dimensions, crs : Visual/GIF-Parameter

Returns
-------
None

Side Effects
------------
Streamlit-Rendering; lädt GIF via HTTP von Earth Engine.
"""

from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional
import io
import requests
import streamlit as st
import ee
from geemap.foliumap import Map
from .gif_label_overlay import label_gif

def _month_labels_from_ic(comp: ee.ImageCollection, ref_year: int) -> List[str]:
    # DOYs von der Kollektion ins Client holen und in Monatsnamen wandeln
    doys = comp.aggregate_array("doy").getInfo()
    from datetime import datetime, timedelta
    months = []
    for d in doys:
        dt = datetime(ref_year, 1, 1) + timedelta(days=int(d))
        months.append(dt.strftime("%B"))
    return months

def render_ndvi_timelapse_panel(
    m: Map,
    comp: ee.ImageCollection,
    aoi: ee.Geometry,
    vis_params: Dict[str, Any],
    ref_year: int,
    fps: int = 10,
    dimensions: int = 600,
    crs: str = "EPSG:3857",
    left_title: str = "Map",
    right_title: str = "Vegetation Animation",
    label_xy: Tuple[int, int] = (10, 10),
    caption: Optional[str] = None,
) -> None:
    """Render NDVI timelapse panel with map preview and labeled GIF."""
    region = aoi.bounds()
    # Visualisierte & geclippte Frames
    rgbVis = comp.map(lambda img: img.visualize(**vis_params).clip(aoi))
    gifParams = {"region": region, "dimensions": int(dimensions), "crs": crs, "framesPerSecond": int(fps)}

    left, right = st.columns([1, 1])

    with left:
        st.subheader(left_title)
        try:
            coords = aoi.centroid().getInfo()["coordinates"]
            m.set_center(coords[0], coords[1], 4)
        except Exception:
            pass
        # Grenze (einfach: AOI-Umriss)
        try:
            boundary = ee.FeatureCollection([ee.Feature(aoi)]).style(color="black", fillColor="00000000", width=1)
            m.addLayer(boundary, {}, "AOI boundary")
        except Exception:
            pass
        try:
            first_frame = ee.Image(comp.first()).visualize(**vis_params).clip(aoi)
            m.addLayer(first_frame, {}, "NDVI (first DOY frame)")
        except Exception:
            pass
        m.to_streamlit()

    with right:
        st.subheader(right_title)
        try:
            gif_url = rgbVis.getVideoThumbURL(gifParams)
            resp = requests.get(gif_url, timeout=60)
            resp.raise_for_status()
            raw_gif = io.BytesIO(resp.content)
            months = _month_labels_from_ic(comp, ref_year)
            labeled = label_gif(raw_gif, months, fps=fps, xy=label_xy)
            st.image(labeled, caption=caption, use_container_width=True)
        except Exception as e:
            st.error(f"Failed to create animation: {e}")
            st.info("Tip: Check Earth Engine auth and that the AOI is valid.")
