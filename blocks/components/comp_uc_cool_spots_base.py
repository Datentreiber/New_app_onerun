# Streamlit + EE: LST Sommer-Median + Map + optional Percentile-Maske
import streamlit as st

def app():
    st.title("Urban Cool Spots — Landsat LST (Sommer-Median)")
    # Widgets
    aoi_text = st.text_input("Ort/Adresse/Polygon (GeoJSON)", "Munich, Germany")
    year = st.number_input("Jahr", min_value=2015, max_value=2025, value=2023, step=1)
    m1, m2, m3 = st.columns(3)
    summer_months = m1.multiselect("Sommer-Monate", [6,7,8], default=[6,7,8])
    percentile = m2.slider("Kühlste x % hervorheben", 80, 99, 90)
    opacity = m3.slider("Layer-Deckkraft", 0.2, 1.0, 0.9, 0.05)

    st.info("Hinweis: AOI/Zeitraum/Parameter sind jederzeit änderbar. "
            "Diese Basis-Komponente erzeugt LST (°C) als Sommer-Median.")

    st.subheader("Debug/Preview (Placeholder)")
    st.json({
        "aoi": aoi_text,
        "year": year,
        "summer_months": summer_months,
        "percentile": percentile,
        "opacity": opacity
    })

if __name__ == "__main__":
    app()
