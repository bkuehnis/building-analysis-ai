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
        
        # Create safe filename from address
        safe_address = address.replace("/", "-").replace(" ", "_")
        filename_main = f"{output_dir}/{safe_address}_zh_map.png"
        filename_ortho = f"{output_dir}/{safe_address}_zh_map_ortho.png"
        
        # Check if files already exist
        main_exists = os.path.exists(filename_main)
        ortho_exists = os.path.exists(filename_ortho)
        
        if main_exists and ortho_exists:
            return filename_main, filename_ortho
        
        # Main map URL using EGID
        url_main = f"{self.base_url}?locate=egid&locations={egid}&collapsed=lrt&scale=600"
        
        # Ortho map URL using EGID with OrthoZH topic
        url_ortho = f"{self.base_url}?locate=egid&locations={egid}&collapsed=lrt&topic=OrthoZH"
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            
            # Screenshot 1: Main map (only if not exists)
            if not main_exists:
                page = browser.new_page(viewport={"width": 960, "height": 540})
                page.goto(url_main, wait_until="networkidle")
                page.wait_for_timeout(3000)
                page.screenshot(path=filename_main, full_page=False)
                page.close()
            
            # Screenshot 2: Ortho/aerial view (only if not exists)
            if not ortho_exists:
                page = browser.new_page(viewport={"width": 960, "height": 540})
                page.goto(url_ortho, wait_until="networkidle")
                page.wait_for_timeout(3000)
                page.screenshot(path=filename_ortho, full_page=False)
                page.close()
            
            browser.close()
        
        return filename_main, filename_ortho
    
    def fetch_zh_map_screenshot(self, x, y, address, scale=1530, output_dir="output/images"):
        """Fetch screenshot of Zürich map at given coordinates"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Create safe filename from address
        safe_address = address.replace("/", "-").replace(" ", "_")
        filename = f"{output_dir}/{safe_address}_zh_map.png"
        
        # Check if file already exists
        if os.path.exists(filename):
            return filename
        
        url = f"https://geo.zh.ch/maps?x={x}&y={y}&scale={scale}&basemap=arelkbackgroundzh"
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            
            # Navigate to URL
            page.goto(url, wait_until="networkidle")
            
            # Wait for map to load
            page.wait_for_timeout(3000)
            
            # Take screenshot
            page.screenshot(path=filename, full_page=False)
            
            browser.close()
        
        return filename