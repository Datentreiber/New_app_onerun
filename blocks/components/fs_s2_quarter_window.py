# S2 Visual — Quarter window & visualization presets
import datetime
import streamlit as st

# Visualization configurations (exactly as in the reference app)
MAP_PARAMS: dict[str, list[str]] = {
    "Natural Color (Red/Green/Blue)": ["B4", "B3", "B2"],
    "Vegetation": ["B12", "B8", "B4"],
    "Land/Water": ["B8", "B11", "B4"],
    "Color Infrared": ["B8", "B4", "B3"],
}
shared_vis = {"min": 0, "max": 0.325, "gamma": 1.0}

def ui_pick_quarter_and_year():
    """
    UI for FCC selection, year and quarter.
    Returns: (viz_type, start_str, end_str, quarter_label, year)
    """
    quarters = {
        "Q1 (Jan–Mar)": 1,
        "Q2 (Apr–Jun)": 4,
        "Q3 (Jul–Sep)": 7,
        "Q4 (Oct–Dec)": 10,
    }
    col1, col2 = st.columns([4, 1])

    with col2:
        options = list(MAP_PARAMS.keys())
        viz_type = st.selectbox("Select a Visualization", options, index=0)

        max_year = datetime.date.today().year
        year = st.selectbox(
            "Select a Year",
            list(range(2016, max_year + 1)),
            index=max_year - 2016
        )

        quarter_label = st.selectbox(
            "Select a Quarter", list(quarters.keys()), index=2
        )  # default Q3

        # Compute [start, end) for the selected quarter
        start_month = quarters[quarter_label]
        start_date = datetime.date(int(year), int(start_month), 1)
        end_month = start_month + 3
        if end_month > 12:
            end_date = datetime.date(int(year) + 1, end_month - 12, 1)
        else:
            end_date = datetime.date(int(year), end_month, 1)

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

    return viz_type, start_str, end_str, quarter_label, int(year), col1, col2
