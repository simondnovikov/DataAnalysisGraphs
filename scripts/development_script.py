import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon
import pandas as pd
import rasterio
import matplotlib.pyplot as plt
from rasterio.plot import show
import matplotlib.colors as mcolors
import json
from rasterio.mask import mask
raster_path = "/home/simon/PycharmProjects/DataAnalysisGraphs/staticData/ukr_ppp_2010.tif"
def main():

    #polygons = get_polygons()

    with open("data.json") as f:
        polygons = json.load(f)
    polygons_object_list = {"geometry": [ Polygon(item[1]) for item in polygons ]}
    polygons_fills = [ item[0] for item in polygons ]
    gdf = gpd.GeoDataFrame(polygons_object_list, crs="EPSG:4326")

    gdf["fills"]=polygons_fills

    unique_fills = gdf["fills"].unique()
    totals = {}
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    totals_2 = {}
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


    # Step 4: Prepare the data for plotting
    # Select the first band
            image_to_plot = out_image

    # Create a masked array to handle nodata values transparently
            masked_image = np.ma.masked_where(image_to_plot == nodata_value, image_to_plot)
            totals_2[fill]={"pop":total_pop,"image":image_to_plot}
    # Step 5: Plot the masked raster
    # We use rasterio.plot.show which understands georeferencing
    # To fill with a single color, we can set a min/max and use a simple colormap



            show(
                masked_image,
                transform=out_transform,
                ax=ax,
                cmap=mcolors.LinearSegmentedColormap.from_list("my_custom_cmap", ['#000000' ,fill], N=256),
                vmin=0,  # Ensures all valid data gets colored
                vmax=1
            )


    # Step 7: Final plot adjustments
    ax.set_title('Masked Population Area')
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    plt.savefig("development_plot.png",dpi=100)
   # plt.show()
    plt.savefig("development_plot.jpg")

    return totals

if __name__ == "__main__":
    totals = main()
    print(totals)
    pd.DataFrame.from_dict(totals,columns=[["pop"]],orient="index").to_csv("totals.csv")