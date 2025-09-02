# Urban Change — With-Stats (km²-Zeitreihe + Karte)
import ee
import streamlit as st
import geemap.foliumap as geemap
import pandas as pd
import matplotlib.pyplot as plt

def render_urban_with_stats():
    """Zeitreihe der bebauten Fläche (km²) 1975..2030/5 in definierter Region; Map + Chart + DF."""
    # Shenzhen rectangle (exactly as reference)
    region = ee.Geometry.Rectangle([113.75, 22.36, 114.63, 22.89])

    Map = geemap.Map(center=[22.6, 114], zoom=10, basemap="SATELLITE")
    Map.add_basemap("CartoDB.PositronOnlyLabels")

    built_surface_1980 = ee.Image(f"{GHSL_PREFIX}/1980").select("built_surface")
    built_surface_2025 = ee.Image(f"{GHSL_PREFIX}/2025").select("built_surface")

    left_layer  = geemap.ee_tile_layer(built_surface_1980, ghsl_vis, "Built Surface 1980", opacity=0.6)
    right_layer = geemap.ee_tile_layer(built_surface_2025, ghsl_vis, "Built Surface 2025", opacity=0.6)

    Map.split_map(left_layer, right_layer)
    Map.add_colorbar(
        vis_params=ghsl_vis,
        label="Built-up area (m² per 100 m grid)",
        orientation="horizontal",
        background_color="white",
        font_size=12,
        position="bottomright",
    )
    Map.addLayerControl()

    all_years = list(range(1975, 2035, 5))  # 1975..2030 inclusive

    def ghsl_image(year: int):
        return ee.Image(f"{GHSL_PREFIX}/{int(year)}").select("built_surface")

    def builtup_km2(year: int) -> float:
        img = ghsl_image(year)
        stat = img.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=region,
            scale=100,
            maxPixels=1e13,
            tileScale=4,
        ).get("built_surface")
        val = stat.getInfo()
        if val is None:
            return 0.0
        return float(val) / 1e6  # m² → km²

    series = []
    for y in all_years:
        try:
            area_km2 = builtup_km2(y)
        except Exception:
            # retry once on transient API issues
            area_km2 = builtup_km2(y)
        series.append({"year": y, "built_up_km2": area_km2})

    df = pd.DataFrame(series).sort_values("year").reset_index(drop=True)

    # Chart (Streamlit-friendly; don't call plt.show())
    fig, ax = plt.subplots(figsize=(8.5, 5.0))
    ax.plot(df["year"], df["built_up_km2"], marker="o")
    ax.set_title("Shenzhen Built-up Surface Area (GHSL, 1975–2025)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Built-up area (km²)")
    ax.grid(True, alpha=0.3)

    left, right = st.columns([3, 2], gap="large")
    with left:
        Map.to_streamlit(height=650)
    with right:
        st.pyplot(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)
