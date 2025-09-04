# blocks/components/ui/slider_int.py
"""
Purpose
-------
Generischer Streamlit-Integer-Slider (keine GEE-Operationen).

Contracts
---------
def ui_slider_int(label: str, min: int, max: int, value: int, step: int = 1) -> int

Args
----
label : str
min, max, value : int
step : int

Returns
-------
int : aktuelle Auswahl

Side Effects
------------
Streamlit-Rendering.
"""

import streamlit as st

def ui_slider_int(label: str, min: int, max: int, value: int, step: int = 1) -> int:
    """Render int slider and return selection."""
    return int(st.slider(label, min_value=int(min), max_value=int(max), value=int(value), step=int(step)))
