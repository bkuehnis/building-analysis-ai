class StreetViewService:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://maps.googleapis.com/maps/api/streetview"

    def fetch_street_view(self, lon, lat, size="1600x1600"):
        """Fetch street view image using lon/lat coordinates"""
        params = {
            "size": size,
            "pitch" : 25,
            "location": f"{lat},{lon}",
            "key": self.api_key
        }
        
        url = f"{self.base_url}?size={params['size']}&location={params['location']}&pitch={params['pitch']}&key={params['key']}"
        return url