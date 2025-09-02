# S2 Visual — Scaffold (Imports, Page Config, EE Auth)
import datetime
import ee
import streamlit as st
import geemap.foliumap as geemap
import folium

# Page configuration
st.set_page_config(page_title="Sentinel-2 Visualizations", layout="wide")

@st.cache_data
def ee_authenticate(token_name: str = "EARTHENGINE_TOKEN"):
    """
    Initialize Earth Engine via geemap helper and cache the result to avoid repeated init.
    """
    geemap.ee_initialize(token_name=token_name)

# Initialize EE once for the app lifecycle
ee_authenticate()
