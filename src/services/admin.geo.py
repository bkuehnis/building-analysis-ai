import math
import requests
import os

###############################################
# 1. CONFIGURATION
###############################################
LAYER = "ch.swisstopo.pixelkarte-farbe"
LAYER = "ch.swisstopo.pixelkarte-grau"
WMTS_URL = (
    "https://wmts.geo.admin.ch/1.0.0/"
    + LAYER
    + "/default/current/3857/{z}/{x}/{y}.jpeg"
)

SEARCH_URL = "https://api3.geo.admin.ch/rest/services/api/SearchServer"


###############################################
# 2. Convert address → lon/lat via SwissTopo API
###############################################
def geocode_address(address):
    params = {
        "searchText": address,
        "type": "locations",
    }

    r = requests.get(SEARCH_URL, params=params)
    r.raise_for_status()
    data = r.json()

    if not data["results"]:
        raise ValueError(f"No geocoding result for: {address}")

    attrs = data["results"][0]["attrs"]
    return attrs["lon"], attrs["lat"]


###############################################
# 3. Convert lon/lat → XYZ tile (EPSG:3857)
###############################################
def lonlat_to_xyz(lon, lat, z):
    lat_rad = math.radians(lat)
    n = 2 ** z

    x_tile = n * ((lon + 180.0) / 360.0)
    y_tile = n * (
        (1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi)
        / 2
    )
    return int(x_tile), int(y_tile)


###############################################
# 4. Download tile
###############################################
def download_tile(z, x, y, outdir="tiles"):
    os.makedirs(outdir, exist_ok=True)
    url = WMTS_URL.format(z=z, x=x, y=y)
    filename = f"{outdir}/tile_z{z}_x{x}_y{y}.jpeg"
    #print(url)
    #print(f"Downloading Z={z}, X={x}, Y={y} → {filename}")
    r = requests.get(url)
    r.raise_for_status()

    with open(filename, "wb") as f:
        f.write(r.content)

    return filename


###############################################
# 5. MAIN: Address → Tiles (z = 15 → 28)
###############################################
def download_tiles_for_address(address):
    lon, lat = geocode_address(address)
    #print(f"Address geocoded: {address}")
    #print(f" → lon={lon}, lat={lat}")

    z = 19
    x, y = lonlat_to_xyz(lon, lat, z)
    download_tile(z, x, y)


###############################################
# Run example
###############################################
if __name__ == "__main__":
    address = "Wiesendangerstrasse 22, 8003 Zürich"
    download_tiles_for_address(address)
