from blocks.components.util.scaffold import ee_authenticate
from blocks.components.gee.aoi_from_spec import aoi_from_spec
from blocks.components.gee.urban_acquire_process import get_built_surface_image

ee_authenticate()
aoi = aoi_from_spec({"type":"place","name":"Shenzhen, China","radius_km":25})
img = get_built_surface_image(2025).clip(aoi)
print("OK: Urban built surface image prepared.")
