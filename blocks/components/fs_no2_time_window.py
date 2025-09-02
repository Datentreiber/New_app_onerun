# NO2 Monthly — Month Window (UI + start/end)
import calendar

def month2idx(name: str) -> int:
    """Map month name (English) to index (1..12). Supports numeric strings too."""
    table = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
    if name.isdigit():
        v = int(name)
        return v if 1 <= v <= 12 else 1
    return table.get(name.strip().lower(), 1)

def ui_pick_year_month():
    cols = st.columns(2)
    with cols[0]:
        year = st.number_input("Jahr", min_value=2018, max_value=date.today().year, value=date.today().year, step=1)
    with cols[1]:
        month_name = st.selectbox("Monat", options=list(calendar.month_name)[1:], index=date.today().month - 1)
    month = month2idx(month_name)

    # Build [start, end)
    start = ee.Date.fromYMD(int(year), int(month), 1)
    if month == 12:
        end = ee.Date.fromYMD(int(year) + 1, 1, 1)
    else:
        end = ee.Date.fromYMD(int(year), int(month) + 1, 1)
    return int(year), int(month), start, end, month_name
