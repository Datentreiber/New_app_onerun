from blocks.components.util.scaffold import ee_authenticate
from blocks.components.gee.aoi_from_spec import aoi_from_spec
from blocks.components.gee.ndvi_acquire_process import build_ndvi_doy_composite

ee_authenticate()
aoi = aoi_from_spec({"type":"place","name":"Europe","radius_km":500})  # großzügig
col = build_ndvi_doy_composite(ref_year=2019)
print("OK: NDVI DOY collection size (server-side):", col.size().getInfo())
