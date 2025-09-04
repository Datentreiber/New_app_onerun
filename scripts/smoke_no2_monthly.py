import ee
from blocks.components.util.scaffold import ee_authenticate
from blocks.components.gee.aoi_from_spec import aoi_from_spec
from blocks.components.gee.no2_acquire_process import build_no2_monthly_image

ee_authenticate()
aoi = aoi_from_spec({"type":"bbox","bbox":[13.0,52.3,13.9,52.7]})
start = ee.Date.fromYMD(2023,7,1); end = ee.Date.fromYMD(2023,8,1)
img = build_no2_monthly_image(start, end).clip(aoi)
print("OK: NO2 image prepared.")
