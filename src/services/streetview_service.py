import requests


class StreetViewService:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://maps.googleapis.com/maps/api/streetview"

    def fetch_street_view(self, lon, lat, size="600x300"):
        """Fetch street view image using lon/lat coordinates"""
        params = {
            "size": size,
            "location": f"{lat},{lon}",
            "key": self.api_key
        }
        
        response = requests.get(self.base_url, params=params)
        
        if response.status_code == 200:
            return response.content
        else:
            raise Exception(f"Error fetching street view: {response.status_code} - {response.text}")