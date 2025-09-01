# Zusatz-Komponente: Split-View (Vorher/Nachher)
import streamlit as st

def split_view_left_right(meta_left: dict, meta_right: dict):
    st.markdown("#### Split View (Placeholder)")
    col_l, col_r = st.columns(2)
    with col_l:
        st.write("Left")
        st.json(meta_left)
    with col_r:
        st.write("Right")
        st.json(meta_right)
