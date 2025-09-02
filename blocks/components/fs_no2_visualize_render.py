# NO2 Monthly — Visualize & Render (Split-map right + Colorbar)
def render_no2_on_map(m: Map, image: ee.Image, palette_label: str = "NO₂ column (mol/m²)"):
    # Visualization parameters (exact constants from the template)
    no2_vis = {
        "min": 0.0,
        "max": 0.0002,
        "palette": [
            "#000000",
            "#120E3B",
            "#3E1E60",
            "#7C1D6F",
            "#B01764",
            "#D13A4E",
            "#E66D3C",
        ],
        "opacity": 1.0,
    }

    # Right side occupied (split-mode default in examples)
    try:
        m.split_map(left_layer=None, right_layer=image, right_vis=no2_vis, right_name="NO₂ (monthly mean)")
    except Exception:
        # Fallback: normal add_layer if split is not available
        m.add_layer(image, no2_vis, "NO₂ (monthly mean)")

    # Colorbar (horizontal at bottom)
    try:
        m.add_colorbar(
            vis_params={"min": no2_vis["min"], "max": no2_vis["max"], "palette": no2_vis["palette"]},
            label=palette_label,
            orientation="horizontal",
            layer_name="NO₂ (monthly mean)",
        )
    except Exception:
        pass

    # Streamlit render
    m.to_streamlit(height=680)
