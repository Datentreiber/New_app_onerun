# NDVI Timelapse — Scaffold (Imports, Page Config, EE Auth)
import io
import ee
import streamlit as st
import geemap.foliumap as geemap
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageSequence
import requests

# Exact page config as reference
st.set_page_config(page_title="Timelapses", layout="wide")

@st.cache_data
def ee_authenticate(token_name: str = "EARTHENGINE_TOKEN"):
    """Initialize Earth Engine via geemap helper; cached to avoid repeated init."""
    geemap.ee_initialize(token_name=token_name)

# Init once
ee_authenticate()
