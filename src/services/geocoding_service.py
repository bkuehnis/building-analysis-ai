import requests


class GeocodingService:
    def __init__(self):
        self.search_url = "https://api3.geo.admin.ch/rest/services/api/SearchServer"
    
    def geocode_address(self, address):
        """Convert address to lon/lat via SwissTopo API"""
        params = {
            "searchText": address,
            "type": "locations",
        }

        r = requests.get(self.search_url, params=params)
        r.raise_for_status()
        data = r.json()

        if not data["results"]:
            raise ValueError(f"No geocoding result for: {address}")

        attrs = data["results"][0]["attrs"]
        return attrs["lon"], attrs["lat"]