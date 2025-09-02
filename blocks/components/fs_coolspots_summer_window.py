# Cool Spots (LST) — Summer window (UI + start/end dates)
import streamlit as st
import ee
from datetime import date

def ui_pick_summer_window():
    """
    UI to choose a year for the summer (Jun–Aug).
    Returns: (year, start_date, end_date)
    """
    current_year = date.today().year
    year = st.number_input("Year (summer window: Jun–Aug)", min_value=2013, max_value=current_year, value=current_year, step=1)

    start = ee.Date.fromYMD(int(year), 6, 1)   # inclusive
    end   = ee.Date.fromYMD(int(year), 9, 1)   # exclusive
    return int(year), start, end
