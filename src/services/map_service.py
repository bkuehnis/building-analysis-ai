import math
import requests
import os


class MapService:
    def __init__(self):
        #self.layer = "ch.swisstopo.pixelkarte-farbe"
        self.layer = "ch.swisstopo.pixelkarte-grau"
        self.wmts_url = (
            "https://wmts.geo.admin.ch/1.0.0/"
            + self.layer
            + "/default/current/3857/{z}/{x}/{y}.jpeg"
        )
       
    def lonlat_to_xyz(self, lon, lat, z):
        """Convert lon/lat to XYZ tile (EPSG:3857)"""
        lat_rad = math.radians(lat)
        n = 2 ** z

        x_tile = n * ((lon + 180.0) / 360.0)
        y_tile = n * (
            (1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi)
            / 2
        )
        return int(x_tile), int(y_tile)

    def download_tile(self, z, x, y, outdir="tiles"):
        """Download tile from SwissTopo WMTS"""
        os.makedirs(outdir, exist_ok=True)
        url = self.wmts_url.format(z=z, x=x, y=y)
        filename = f"{outdir}/tile_z{z}_x{x}_y{y}.jpeg"
        print(f"Downloading Z={z}, X={x}, Y={y} → {filename}")
        
        r = requests.get(url)
        r.raise_for_status()

        with open(filename, "wb") as f:
            f.write(r.content)

        return filename

    def fetch_map(self, lon, lat, zoom=19):
        """Fetch map image for the given address"""
        
        print(f" → lon={lon}, lat={lat}")

        x, y = self.lonlat_to_xyz(lon, lat, zoom)
        return self.download_tile(zoom, x, y)