# Urban Change — Scaffold (Imports, Page Config, Constants)
import ee
import streamlit as st
import geemap.foliumap as geemap
import pandas as pd
import folium
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

# GHSL collection and visualization params (exactly as in the reference)
GHSL_PREFIX = "JRC/GHSL/P2023A/GHS_BUILT_S"  # built_surface, built_surface_nres
ghsl_vis = {
    "min": 0,
    "max": 8000,  # 0..8000 m² of built-up per 100 m grid typical for city cores
    "palette": ["000000", "1f78b4", "a6cee3", "b2df8a", "ffff99", "fdbf6f", "e31a1c"],
}

@st.cache_data
def ee_authenticate(token_name: str = "EARTHENGINE_TOKEN"):
    """Initialize Earth Engine via geemap helper."""
    import geemap
    geemap.ee_initialize(token_name=token_name)

# Initialize once
ee_authenticate()
