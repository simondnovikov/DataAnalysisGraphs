



import geopandas as gpd
from shapely.geometry import Polygon
import pandas as pd
import rasterio
import json
from rasterio.mask import mask


raster_path = "../staticData/ukr_ppp_2010_UN.tif"
def sum_polygon(polygons,UN = False):
    if UN:
        raster_path = "../staticData/ukr_ppp_2010_UNadj.tif"
    else:
        raster_path = "../staticData/ukr_ppp_2010.tif"

    polygons_object_list = {"geometry": [ Polygon(item[1]) for item in polygons ]}
    polygons_fills = [ item[0] for item in polygons ]
    gdf = gpd.GeoDataFrame(polygons_object_list, crs="EPSG:4326")

    gdf["fills"]=polygons_fills

    unique_fills = gdf["fills"].unique()
    totals = {}

    with rasterio.open(raster_path) as src:
        for fill in unique_fills:
            gdf_inner = gdf[gdf["fills"] == fill]
            unified_polygon = gdf_inner.geometry.union_all()

            # Step 4: Mask the raster with the unified polygon
            # The mask function requires a list of geometries
            out_image, out_transform = mask(
                dataset=src,
                shapes=[unified_polygon],
               # crop=True,  # Crop the raster to the extent of the polygon
            )

            nodata_value = src.nodata
            total_pop = out_image[out_image != nodata_value].sum()
            totals[fill]=total_pop

    return totals

if __name__ == "__main__":
    with open("../scripts/data.json") as f:
        polygons = json.load(f)
    totals = sum_polygon(polygons)
    print(totals)
    pd.DataFrame.from_dict(totals,columns=[["pop"]],orient="index").to_csv("../scripts/totals.csv")