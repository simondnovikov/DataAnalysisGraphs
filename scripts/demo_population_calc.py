import os
import requests
import geopandas as gpd
from rasterstats import zonal_stats
from shapely.geometry import Polygon

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'staticData')
ISO_CODE = 'LUX'
YEAR = 2010
# Using 1km resolution for smaller file size in this demo
RASTER_FILENAME = f'{ISO_CODE.lower()}_ppp_{YEAR}_1km_Aggregated.tif'
RASTER_PATH = os.path.join(DATA_DIR, RASTER_FILENAME)
# WorldPop URL structure
DOWNLOAD_URL = f"https://data.worldpop.org/GIS/Population/Global_2000_2020/{YEAR}/{ISO_CODE}/{RASTER_FILENAME}"

def ensure_data_exists():
    """Checks if the raster file exists, otherwise downloads it."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    if not os.path.exists(RASTER_PATH):
        print(f"Dataset not found. Downloading {RASTER_FILENAME} from WorldPop...")
        print(f"URL: {DOWNLOAD_URL}")
        try:
            response = requests.get(DOWNLOAD_URL, stream=True)
            response.raise_for_status()
            with open(RASTER_PATH, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("Download complete.")
        except Exception as e:
            print(f"Error downloading file: {e}")
            return False
    else:
        print(f"Using existing dataset: {RASTER_PATH}")
    return True

def create_sample_polygon():
    """Creates a sample polygon (a box in Luxembourg) for demonstration."""
    # Coordinates roughly in the center of Luxembourg
    # Longitude, Latitude
    lat_point_list = [49.6, 49.8, 49.8, 49.6, 49.6]
    lon_point_list = [6.0, 6.0, 6.2, 6.2, 6.0]
    
    polygon_geom = Polygon(zip(lon_point_list, lat_point_list))
    crs = 'EPSG:4326' # WGS84
    polygon = gpd.GeoDataFrame(index=[0], crs=crs, geometry=[polygon_geom])
    return polygon

def calculate_population(polygon_gdf, raster_path):
    """Calculates the sum of population within the given polygons."""
    print("Calculating zonal statistics...")
    
    # zonal_stats expects the geometry and the path to the raster
    # stats="sum" calculates the total population count
    stats = zonal_stats(polygon_gdf, raster_path, stats="sum")
    
    return stats[0]['sum']

def main():
    if not ensure_data_exists():
        print("Aborting: Could not obtain data.")
        return

    print("Creating sample polygon...")
    sample_poly = create_sample_polygon()
    
    # Optional: Save polygon to file to inspect it later
    poly_path = os.path.join(DATA_DIR, "sample_polygon.geojson")
    sample_poly.to_file(poly_path, driver='GeoJSON')
    print(f"Sample polygon saved to {poly_path}")

    try:
        population = calculate_population(sample_poly, RASTER_PATH)
        print("\n--- Results ---")
        print(f"Estimated Population in the sample polygon (Luxembourg area) for year {YEAR}:")
        print(f"{population:, .2f} people")
    except Exception as e:
        print(f"An error occurred during calculation: {e}")

if __name__ == "__main__":
    main()
