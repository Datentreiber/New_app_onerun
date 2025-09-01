# Streamlit + S5P NO2 Monatsmittel + optionaler Vergleich
import streamlit as st

def app():
    st.title("S5P NO₂ Monatsmittel / Vergleich")
    aoi_text = st.text_input("Ort/Adresse/Polygon (GeoJSON)", "Berlin, Germany")
    month = st.text_input("Monat (YYYY-MM)", "2020-03")
    compare_to = st.text_input("Vergleichsmonat (YYYY-MM, optional)", "")

    st.info("Monatsmittel NO₂; Vergleichsmodus zeigt Differenz.")
    st.subheader("Debug/Preview (Placeholder)")
    st.json({"aoi": aoi_text, "month": month, "compare_to": compare_to})

if __name__ == "__main__":
    app()
