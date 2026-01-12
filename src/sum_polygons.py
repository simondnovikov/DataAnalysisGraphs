


import matplotlib.pyplot as plt

from rasterio.plot import show
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon
import rasterio
import json
from rasterio.mask import mask


from matplotlib import cm
from matplotlib.colors import ListedColormap
import matplotlib.colors as colors
our_cmap = cm.get_cmap('hot_r', 10)
newcolors = our_cmap(np.linspace(0, 1, 10))
background_colour = np.array([0.9882352941176471, 0.9647058823529412, 0.9607843137254902, 1.0])
newcolors = np.vstack((background_colour, newcolors))
our_cmap = ListedColormap(newcolors)
bounds = [0.0, 0.25, 0.5, 1, 2, 4, 8, 16, 32, 64, 128]
norm = colors.BoundaryNorm(bounds, our_cmap.N)


russian_fills = ['#a52714','#000000','#880e4f','#bcaaa4','#bdbdbd']

file_path = "../pulled_data/1664627935.json"
with open(file_path, "r") as f:
    original_polygons = json.load(f)
polygons_object_list = {"geometry": [ Polygon(item[1]) for item in original_polygons ]}
polygons_fills = [ item[0] for item in original_polygons ]
gdf = gpd.GeoDataFrame(polygons_object_list, crs="EPSG:4326")

gdf["fills"]=polygons_fills


gdf_inner = gdf[gdf["fills"].isin(russian_fills) ]
unified_original_polygon = gdf_inner.geometry.union_all()

def sum_polygon(polygons, src, buffer_meters = [5,50,500,5000],draw_image=False,title="example"):


    polygons_object_list = {"geometry": [ Polygon(item[1]) for item in polygons ]}
    polygons_fills = [ item[0] for item in polygons ]
    gdf = gpd.GeoDataFrame(polygons_object_list, crs="EPSG:4326")

    gdf["fills"]=polygons_fills


    gdf_inner = gdf[gdf["fills"].isin(russian_fills) ]
    unified_polygon = gdf_inner.geometry.union_all()

    # Step 4: Mask the raster with the unified polygon
    out_image, out_transform = mask(
        dataset=src,
        shapes=[unified_polygon]
    )
    nodata_value = src.nodata
    total_pop = out_image[out_image != nodata_value].sum()
    print(out_image.max())
    results = {"pop": total_pop}


    diff_poligon = unified_polygon.difference(unified_original_polygon)
    if diff_poligon.area > 0:
        results["area"] = diff_poligon.area
        out_image_diff, out_transform_diff = mask(
            dataset=src,
            shapes=[diff_poligon],
            crop=True
        )
    if draw_image:
        fig, ax = plt.subplots(1, 1, figsize=(100, 50))
        masked_image = np.ma.masked_where(out_image == nodata_value, out_image)

        show(
            masked_image,
            transform=out_transform,
            ax=ax,
            cmap=our_cmap,
            norm=norm
        )

        # Step 7: Final plot adjustments
        ax.set_title('Masked Population Area')
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        plt.savefig(f"../plots/population/development_plot_{title}.png", dpi=100)
        plt.close()
        if draw_image and diff_poligon.area > 0:
            fig, ax = plt.subplots(1, 1, figsize=(100, 50))
            masked_image_diff = np.ma.masked_where(out_image_diff == nodata_value, out_image_diff)

            show(
                masked_image_diff,
                transform=out_transform,
                ax=ax,
                cmap=our_cmap,
                norm=norm
            )

            # Step 7: Final plot adjustments
            ax.set_title('Masked Population Area')
            ax.set_xlabel('Longitude')
            ax.set_ylabel('Latitude')
            plt.savefig(f"../plots/diff/development_plot_{title}_diff.png", dpi=100)
            plt.close()



    for meters in buffer_meters:
        # Create a GeoSeries to handle projection
        gs = gpd.GeoSeries([unified_polygon], crs="EPSG:4326")
        # Estimate UTM CRS for metric buffering
        utm_crs = gdf_inner.estimate_utm_crs()
        # Reproject, buffer, and reproject back
        buffered_shape = gs.to_crs(utm_crs).buffer(meters).to_crs("EPSG:4326").iloc[0]

        out_image_buf, _ = mask(
            dataset=src,
            shapes=[buffered_shape],
            crop=True
        )
        total_pop_buf = out_image_buf[out_image_buf != nodata_value].sum()
        results[f"pop_{ str(meters)}"] = total_pop_buf

        if draw_image and meters == max(buffer_meters):
            fig, ax = plt.subplots(1, 1, figsize=(20, 20))
            masked_image = np.ma.masked_where(out_image_buf == nodata_value, out_image_buf)

            show(
                masked_image,
                transform=out_transform,
                ax=ax,
                cmap=our_cmap,
                norm=norm
            )

            # Step 7: Final plot adjustments
            ax.set_title('Masked Population Area')
            ax.set_xlabel('Longitude')
            ax.set_ylabel('Latitude')
            plt.savefig(f"../plots/development_plot_{title}_{str(meters)}.png", dpi=100)
            plt.close()


    return results

if __name__ == "__main__":
    with open("../pulled_data/1764624693.json") as f:
        polygons = json.load(f)
    raster_path = "../staticData/ukr_ppp_2010_UNadj.tif"
    with rasterio.open(raster_path) as src:
        totals = sum_polygon(polygons,src, [],True,"try7")
