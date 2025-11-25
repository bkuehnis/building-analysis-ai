import math
import os


class MapService:
    def __init__(self):
        self.maps = {
            "pixelkarte-grau": {
                "layer": "ch.swisstopo.pixelkarte-grau",
                "format": "jpeg"
            },
            "pixelkarte-farbe": {
                "layer": "ch.swisstopo.pixelkarte-farbe",
                "format": "jpeg"
            },
            "swisstlm3d-karte-farbe": {
                "layer": "ch.swisstopo.swisstlm3d-karte-farbe",
                "format": "png"
            }
        }
        self.base_wmts_url = "https://wmts.geo.admin.ch/1.0.0/{layer}/default/current/3857/{z}/{x}/{y}.{format}"
       
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
        

    def fetch_map(self, lon, lat, map_type="pixelkarte-grau", zoom=16):
        """Fetch map image URL for the given coordinates
        
        Args:
            lon: Longitude
            lat: Latitude
            map_type: Map style - one of 'pixelkarte-grau', 'pixelkarte-farbe', 'swisstlm3d-karte-farbe'
            zoom: Zoom level (default 16)
        
        Returns:
            URL string for the map tile
        """
        
        if map_type not in self.maps:
            raise ValueError(f"Invalid map type. Choose from: {list(self.maps.keys())}")
        
        map_config = self.maps[map_type]
        layer = map_config["layer"]
        image_format = map_config["format"]
        
        print(f" → lon={lon}, lat={lat}, map_type={map_type}, format={image_format}")

        x, y = self.lonlat_to_xyz(lon, lat, zoom)
        url = self.base_wmts_url.format(layer=layer, z=zoom, x=x, y=y, format=image_format)
        return url
    
    def fetch_all_maps(self, lon, lat, zoom=16):
        """Fetch all available map types for the given coordinates
        
        Returns:
            Dictionary with map_type as key and URL as value
        """
        urls = {}
        for map_type in self.maps.keys():
            urls[map_type] = self.fetch_map(lon, lat, map_type, zoom)
        return urls