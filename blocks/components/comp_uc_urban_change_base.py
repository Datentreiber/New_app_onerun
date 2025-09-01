# Streamlit + GHSL Urban Change
import streamlit as st

def app():
    st.title("GHSL Urban Change")
    aoi_text = st.text_input("Ort/Adresse/Polygon (GeoJSON)", "Nairobi, Kenya")
    y1, y2 = st.columns(2)
    year1 = y1.number_input("Jahr 1", min_value=1975, max_value=2025, value=1990, step=5)
    year2 = y2.number_input("Jahr 2", min_value=1975, max_value=2025, value=2015, step=5)

    st.info("Zeigt Änderung zwischen zwei Zeitpunkten (Placeholder).")

    st.subheader("Debug/Preview (Placeholder)")
    st.json({"aoi": aoi_text, "years": [int(year1), int(year2)]})

if __name__ == "__main__":
    app()
