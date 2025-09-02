# NO2 Monthly — Acquire & Reduce
def build_no2_monthly_image(start: ee.Date, end: ee.Date) -> ee.Image:
    """
    Acquire S5P NRTI NO2 column and compute monthly mean image for [start, end).
    Exact band: 'NO2_column_number_density'.
    """
    collection = (
        ee.ImageCollection("COPERNICUS/S5P/NRTI/L3_NO2")
        .select("NO2_column_number_density")
        .filterDate(start, end)
    )
    # Mean over the monthly window
    image = collection.mean().rename("NO2_column_number_density")
    return image
