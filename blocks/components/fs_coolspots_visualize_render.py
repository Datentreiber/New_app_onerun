# Cool Spots (LST) — Visualize & Render (Split-map right + Colorbar)
from geemap.foliumap import Map

def render_lst_on_map(m: Map, lst_image, palette_label: str = "Surface temperature (°C)"):
    # Visualization parameters (exact constants from the reference)
    TEMP_OPACITY = 0.6
    temp_vis = {
        "min": 20,
        "max": 45,
        "palette": [
            "#313695", "#4575b4", "#74add1", "#abd9e9", "#e0f3f8", "#ffffbf",
            "#fee090", "#fdae61", "#f46d43", "#d73027", "#a50026"
        ],
        "opacity": TEMP_OPACITY,
    }

    # Right side occupied (split-mode preferred); fallback to add_layer if needed
    try:
        m.split_map(left_layer=None, right_layer=lst_image, right_vis=temp_vis, right_name="LST (°C, summer median)")
    except Exception:
        m.add_layer(lst_image, temp_vis, "LST (°C, summer median)")

    # Colorbar (horizontal at bottom)
    try:
        m.add_colorbar(
            vis_params={"min": temp_vis["min"], "max": temp_vis["max"], "palette": temp_vis["palette"]},
            label=palette_label,
            orientation="horizontal",
            layer_name="LST (°C, summer median)",
        )
    except Exception:
        pass

    # Streamlit render
    m.to_streamlit(height=680)
