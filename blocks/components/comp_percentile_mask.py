# Zusatz-Komponente: Percentile-Maske (UI + einfache Logik-Hooks)
import streamlit as st

def ui_percentile(default: int = 90) -> int:
    return st.slider("Percentile (kühlste x %)", 80, 99, int(default))

def apply_percentile_mask(info: dict, percentile: int) -> dict:
    # Placeholder: hier würde auf ein LST-Image eine Maskierung angewendet.
    info = dict(info)
    info["percentile_applied"] = percentile
    return info
