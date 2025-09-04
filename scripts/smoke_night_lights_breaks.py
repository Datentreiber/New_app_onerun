import ee
from blocks.components.util.scaffold import ee_authenticate
from blocks.components.gee.aoi_from_spec import aoi_from_spec
from blocks.components.gee.night_lights_acquire_process import get_viirs_month

ee_authenticate()
aoi = aoi_from_spec({"type":"point_buffer","point":[32.02,46.95],"radius_km":20})
pre  = ee.Date.fromYMD(2022, 6, 1)
post = ee.Date.fromYMD(2023, 6, 1)
pre_img = get_viirs_month(pre).clip(aoi)
post_img = get_viirs_month(post).clip(aoi)
print("OK: VIIRS pre/post prepared.")
