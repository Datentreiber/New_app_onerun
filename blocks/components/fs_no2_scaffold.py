# NO2 Monthly — Scaffold (Imports, Page Config, EE Auth)
import os
import io
import math
from datetime import datetime, date

import ee
import geemap
from geemap.foliumap import Map
import folium

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Air Quality — Monthly NO₂",
    page_icon="🧪",
    layout="wide",
)

# Earth Engine authentication/initialization
def ee_authenticate():
    """
    Initialize Earth Engine using geemap helper.
    Expects that a valid Earth Engine credential is available on the host.
    """
    try:
        geemap.ee_initialize(token_name="EARTHENGINE_TOKEN")
    except Exception as e:
        st.error(
            "Earth Engine konnte nicht initialisiert werden. "
            "Bitte EE-Login/Token prüfen. Details: {}".format(e)
        )
        st.stop()

# Call EE init once at startup of the app
ee_authenticate()
