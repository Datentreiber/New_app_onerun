# Cool Spots (LST) — Scaffold (Imports, Page Config, EE Auth)
import os
from datetime import date

import ee
import geemap
import geemap.foliumap as geemap_folium
from geemap.foliumap import Map
import folium

import streamlit as st

# Page configuration (wide to give room for the map)
st.set_page_config(
    page_title="Cool Spots — Summer LST (Landsat 8/9 L2)",
    page_icon="🌡️",
    layout="wide",
)

@st.cache_data
def ee_authenticate(token_name: str = "EARTHENGINE_TOKEN"):
    """
    Initialize Earth Engine using geemap helper.
    Expects that a valid Earth Engine credential is available on the host.
    Cached to avoid repeated init.
    """
    geemap.ee_initialize(token_name=token_name)

# Initialize EE once
ee_authenticate()
