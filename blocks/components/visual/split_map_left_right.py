# blocks/components/visual/split_map_left_right.py
"""
Purpose
-------
Generisches Split-Map-Pattern: linker und rechter Layer, optional Farbleiste.

Contract
--------
def render_split_map_left_right(
    m, left_layer, right_layer,
    left_vis: dict | None, right_vis: dict,
    left_title: str, right_title: str,
    height: int = 680,
    colorbar_label: str | None = None
) -> None

Args
----
m : geemap.foliumap.Map
left_layer, right_layer : beliebige Layer-Objekte (z. B. geemap.ee_tile_layer(...))
left_vis, right_vis : Visualisierungs-Parameter (min/max/palette/opacity/bands)
left_title, right_title : Legenden-/Layernamen
height : Kartenhöhe
colorbar_label : Label für automatisch erzeugte Farbleiste (wenn right_vis min/max/palette enthält)

Returns
-------
None

Side-effects
------------
Schreibt in Streamlit (m.to_streamlit).
"""
from typing import Any, Dict, Optional
from geemap.foliumap import Map

def render_split_map_left_right(
    m: Map,
    left_layer: Any,
    right_layer: Any,
    left_vis: Optional[Dict] = None,
    right_vis: Optional[Dict] = None,
    left_title: str = "Left",
    right_title: str = "Right",
    height: int = 680,
    colorbar_label: Optional[str] = None,
) -> None:
    # Split-Ansicht
    m.split_map(left_layer=left_layer, right_layer=right_layer,
                left_vis=(left_vis or {}), right_vis=(right_vis or {}),
                left_name=left_title, right_name=right_title)
    # Farbleiste (für rechten Layer)
    try:
        if right_vis and all(k in right_vis for k in ("min", "max", "palette")):
            m.add_colorbar(
                vis_params={"min": right_vis["min"], "max": right_vis["max"], "palette": right_vis["palette"]},
                label=(colorbar_label or right_title),
                orientation="horizontal",
                layer_name=right_title,
            )
    except Exception:
        pass
    m.to_streamlit(height=int(height))
