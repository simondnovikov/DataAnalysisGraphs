import requests
import json

def get_times():
    base_url = "https://deepstatemap.live/api/history/public"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(base_url, headers=headers)
    response_json = response.json()
    times = [item["id"] for item in response_json]
    return times




def get_polygons(time=None):


    base_url = "https://deepstatemap.live/api/history/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }


    if time is None:
        url = base_url+"last"
    else:
        url = base_url+str(time) + "/geojson"
    response = requests.get(url, headers=headers)
    response_json = response.json()
    map = response_json["features"]

    polygons = []
    for row in map:
        try:
            fill = row["properties"]["fill"]
            polygon = row["geometry"]["coordinates"][0]
            no_zero_polygon = [ [item[0],item[1]] for item in polygon ]
            polygons.append([fill,no_zero_polygon])
        except KeyError:
            continue
    return polygons


if __name__ == "__main__":
    polygons = get_polygons()

    with open('../scripts/data.json', 'w') as f:
        json.dump(polygons, f, indent=4)
