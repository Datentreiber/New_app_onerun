from datetime import date
from blocks.components.util.scaffold import ee_authenticate
from blocks.components.gee.aoi_from_spec import aoi_from_spec
from blocks.components.gee.s2_acquire_process import quarter_window, fetch_quarter_mosaic

ee_authenticate()
aoi = aoi_from_spec({"type":"place","name":"Rome, Italy","radius_km":20})
start, end = quarter_window(year=date.today().year, quarter=3)
img = fetch_quarter_mosaic(start, end).clip(aoi)
print("OK: S2 mosaic prepared.")
