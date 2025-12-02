from playwright.sync_api import sync_playwright
import os


class StreetViewService:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://maps.googleapis.com/maps/api/streetview"

    def fetch_street_view(self, lon, lat, size="1600x1600"):
        """Fetch street view image using lon/lat coordinates"""
        params = {
            "size": size,
            "pitch": 25,
            "location": f"{lat},{lon}",
            "key": self.api_key
        }
        
        url = f"{self.base_url}?size={params['size']}&location={params['location']}&pitch={params['pitch']}&key={params['key']}"
        return url
    
    def fetch_street_view_screenshot(self, lon, lat, address, output_dir="output/images"):
        """Fetch interactive Street View screenshot using Playwright"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Interactive Street View URL
        url = f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat},{lon}&pitch=25"
        
        # Create safe filename from address
        safe_address = address.replace("/", "-").replace(" ", "_")
        filename = f"{output_dir}/{safe_address}_streetview_interactive.png"
        
        print(f"Taking screenshot of Street View: {url}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 960, "height": 540})  # Half size: 1920/2, 1080/2
            
            # Navigate to URL
            page.goto(url, wait_until="networkidle")
            
            # Try to accept cookies if the dialog appears
            try:
                # Wait for cookie consent button and click it
                accept_button = page.locator('button:has-text("Accept all"), button:has-text("Alle akzeptieren"), button:has-text("Tout accepter")')
                if accept_button.count() > 0:
                    accept_button.first.click()
                    print("Accepted cookies")
                    page.wait_for_timeout(2000)
            except Exception as e:
                print(f"No cookie dialog or couldn't click: {e}")
            
            # Wait for Street View to load
            page.wait_for_timeout(5000)  # Wait 5 seconds for Street View to render
            
            # Take screenshot
            page.screenshot(path=filename, full_page=False)
            
            browser.close()
        
        print(f"Street View screenshot saved: {filename}")
        return filename