# Streamlit + MODIS NDVI Timelapse
import streamlit as st

def app():
    st.title("MODIS NDVI Timelapse")
    aoi_text = st.text_input("Ort/Adresse/Polygon (GeoJSON)", "Amazonas")
    start_year = st.number_input("Startjahr", min_value=2001, max_value=2024, value=2019, step=1)
    end_year = st.number_input("Endjahr", min_value=2001, max_value=2025, value=2024, step=1)

    st.info("Erzeugt animierte NDVI-Ansicht (Placeholder).")

    st.subheader("Debug/Preview (Placeholder)")
    st.json({"aoi": aoi_text, "start_year": start_year, "end_year": end_year})

if __name__ == "__main__":
    app()
