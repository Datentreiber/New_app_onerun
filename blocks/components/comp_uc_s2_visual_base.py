# Streamlit + Sentinel-2 Quartals-FCC
import streamlit as st

def app():
    st.title("Sentinel-2 FCC (Quartal)")
    aoi_text = st.text_input("Ort/Adresse/Polygon (GeoJSON)", "Barcelona, Spain")
    year = st.number_input("Jahr", min_value=2016, max_value=2025, value=2024, step=1)
    quarter = st.selectbox("Quartal", ["Q1","Q2","Q3","Q4"], index=2)
    opacity = st.slider("Layer-Deckkraft", 0.2, 1.0, 0.95, 0.05)

    st.info("FCC: B8 (NIR), B4 (R), B3 (G). Wolkenmaskierung per QA60/s2cloudless (implizit).")

    st.subheader("Debug/Preview (Placeholder)")
    st.json({"aoi": aoi_text, "year": year, "quarter": quarter, "opacity": opacity})

if __name__ == "__main__":
    app()
