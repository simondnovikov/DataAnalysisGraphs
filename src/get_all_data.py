import json
import os
from datetime import datetime, timezone

import pandas as pd

import API
from sum_polygons import sum_polygon
import rasterio



def main(UN=True):


    if UN:
        raster_path = "../staticData/ukr_ppp_2010_UNadj.tif"
    else:
        raster_path = "../staticData/ukr_ppp_2010.tif"

    times = API.get_times()

    # Select the first available timestamp for each month (UTC)
    # Keep the original type (likely str) for API calls/filenames
    selected_times = []
    seen_months = set()  # (year, month)
    for t in sorted(times, key=lambda x: int(x)):
        dt = datetime.fromtimestamp(int(t), tz=timezone.utc)
        ym = (dt.year, dt.month)
        if (t >= 1664627935) and (ym not in seen_months):
            seen_months.add(ym)
            selected_times.append(t)

    totals = {}
    with rasterio.open(raster_path) as src:
        for start_time in selected_times:


            file_path = f"../pulled_data/{start_time}.json"
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    polygons = json.load(f)
            else:
                polygons = API.get_polygons(start_time)
                json.dump(polygons, open(file_path, "w"), indent=4)


            totals[start_time]=sum_polygon(polygons,src,[],draw_image=True,title=str(start_time))

    pop_totals = pd.DataFrame.from_dict(totals)


    pop_totals.to_csv("totals_buffers.csv")


if __name__ == "__main__":
    totals = main()