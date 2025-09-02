# S2 Visual — Render (Split-map right) using geemap tile layer
import geemap.foliumap as geemap

def render_fcc(Map, image, viz_type, shared_vis, MAP_PARAMS):
    """
    Build a right-side split layer with selected FCC band triplet and shared_vis parameters.
    """
    right_layer = geemap.ee_tile_layer(
        image,
        {**shared_vis, "bands": MAP_PARAMS[viz_type]},
        viz_type,
        opacity=1.0,
    )
    # Split map with empty left side
    Map.split_map("", right_layer)
    Map.to_streamlit()
