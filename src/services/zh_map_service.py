from playwright.sync_api import sync_playwright
import os


class ZhMapService:
    def __init__(self):
        self.base_url = "https://maps.zh.ch/"
    
    def fetch_zh_map_screenshot_by_egid(self, egid, address, output_dir="output/images"):
        """Fetch screenshot of Zürich map using EGID
        
        Args:
            egid: Building EGID
            address: Address string for filename
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Main map URL using EGID
        url_main = f"{self.base_url}?locate=egid&locations={egid}&collapsed=lrt&scale=600"
        
        # Ortho map URL using EGID with OrthoZH topic
        url_ortho = f"{self.base_url}?locate=egid&locations={egid}&collapsed=lrt&topic=OrthoZH"
        
        # Create safe filename from address
        safe_address = address.replace("/", "-").replace(" ", "_")
        filename_main = f"{output_dir}/{safe_address}_zh_map.png"
        filename_ortho = f"{output_dir}/{safe_address}_zh_map_ortho.png"
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            
            # Screenshot 1: Main map
            print(f"Taking screenshot of ZH map: {url_main}")
            page = browser.new_page(viewport={"width": 960, "height": 540})  # Half size: 1920/2, 1080/2
            page.goto(url_main, wait_until="networkidle")
            page.wait_for_timeout(5000)
            page.screenshot(path=filename_main, full_page=False)
            print(f"ZH map screenshot saved: {filename_main}")
            page.close()
            
            # Screenshot 2: Ortho/aerial view
            print(f"Taking screenshot of ZH ortho map: {url_ortho}")
            page = browser.new_page(viewport={"width": 960, "height": 540})  # Half size: 1920/2, 1080/2
            page.goto(url_ortho, wait_until="networkidle")
            page.wait_for_timeout(5000)
            page.screenshot(path=filename_ortho, full_page=False)
            print(f"ZH ortho screenshot saved: {filename_ortho}")
            page.close()
            
            browser.close()
        
        return filename_main, filename_ortho
    
    def fetch_zh_map_screenshot(self, x, y, address, scale=1530, output_dir="output/images"):
        """Fetch screenshot of Zürich map at given coordinates"""
        os.makedirs(output_dir, exist_ok=True)
        
        url = f"https://geo.zh.ch/maps?x={x}&y={y}&scale={scale}&basemap=arelkbackgroundzh"
        
        # Create safe filename from address
        safe_address = address.replace("/", "-").replace(" ", "_")
        filename = f"{output_dir}/{safe_address}_zh_map.png"
        
        print(f"Taking screenshot of ZH map: {url}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            
            # Navigate to URL
            page.goto(url, wait_until="networkidle")
            
            # Wait for map to load
            page.wait_for_timeout(3000)  # Wait 3 seconds for map to render
            
            # Take screenshot
            page.screenshot(path=filename, full_page=False)
            
            browser.close()
        
        print(f"ZH map screenshot saved: {filename}")
        return filename