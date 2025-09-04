# blocks/components/ui/number_input_int.py
"""
Purpose
-------
Generisches Streamlit-Integer-Number-Input (keine GEE-Operationen).

Contracts
---------
def ui_number_input_int(label: str, min: int, max: int, value: int, step: int = 1) -> int

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

def ui_number_input_int(label: str, min: int, max: int, value: int, step: int = 1) -> int:
    """Render int number input and return selection."""
    return int(st.number_input(label, min_value=int(min), max_value=int(max), value=int(value), step=int(step)))
