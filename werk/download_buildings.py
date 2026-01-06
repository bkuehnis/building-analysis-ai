#!/usr/bin/env python3
"""
Script to download building data from werk-material.crb.ch
Task 1: Extract building IDs from Excel file
Task 2: Download HTML, metadata JSON, and images for each building
"""

import pandas as pd
import requests
import json
import os
from pathlib import Path
from typing import List
import time
from playwright.sync_api import sync_playwright

# Base paths
BASE_DIR = Path(__file__).parent.parent
EXCEL_FILE = BASE_DIR / "data/251118 Textbeschreibung Werk-material/5_Matrix_Konstruktionstypologie WERK Objekte gui.xlsx"
DATA_DIR = BASE_DIR / "data/werk"
AUTH_STATE_FILE = BASE_DIR / "werk/.auth_state.json"

# API endpoints
HTML_URL = "https://werk-material.crb.ch/api/projects-view/{id}/html?lang=de"
METADATA_URL = "https://werk-material.crb.ch/api/project-media/{id}/metadata"


def extract_building_ids() -> List[str]:
    """
    Task 1: Extract building IDs from Excel file column B (werk.material)
    """
    print(f"Reading Excel file: {EXCEL_FILE}")
    df = pd.read_excel(EXCEL_FILE)
    
    # Check available columns
    print(f"Available columns: {df.columns.tolist()}")
    
    # Find the werk.material column (column B)
    if 'werk.material' in df.columns:
        ids = df['werk.material'].dropna().astype(int).astype(str).tolist()
    else:
        # Try to use column B by index (column B is index 1)
        ids = df.iloc[:, 1].dropna().astype(int).astype(str).tolist()
    
    print(f"Found {len(ids)} building IDs: {ids}")
    return ids


def download_html(building_id: str) -> bool:
    """
    Download HTML datasheet for a building using Playwright with saved auth state
    """
    url = HTML_URL.format(id=building_id)
    output_dir = DATA_DIR / building_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "datasheet.html"
    
    try:
        print(f"  Downloading HTML from {url}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            
            # Use saved auth state if available
            if AUTH_STATE_FILE.exists():
                context = browser.new_context(storage_state=str(AUTH_STATE_FILE))
            else:
                context = browser.new_context()
            
            page = context.new_page()
            
            # Navigate to URL
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Wait for content to load
            page.wait_for_timeout(2000)
            
            # Get the HTML content
            html_content = page.content()
            
            browser.close()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"  ✓ Saved to {output_file}")
        return True
    except Exception as e:
        print(f"  ✗ Error downloading HTML: {e}")
        return False


def download_metadata(building_id: str) -> dict:
    """
    Download metadata JSON for a building using Playwright with saved auth state
    """
    url = METADATA_URL.format(id=building_id)
    output_dir = DATA_DIR / building_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "metadata.json"
    
    try:
        print(f"  Downloading metadata from {url}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            
            # Use saved auth state if available
            if AUTH_STATE_FILE.exists():
                context = browser.new_context(storage_state=str(AUTH_STATE_FILE))
            else:
                context = browser.new_context()
            
            page = context.new_page()
            
            # Navigate to URL
            response = page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Wait for content to load
            page.wait_for_timeout(2000)
            
            # Get the JSON content
            content = page.content()
            
            # Try to extract JSON from the page
            # The API might return JSON directly or wrapped in HTML
            try:
                # First try to get it from the page text
                json_text = page.locator('body').inner_text()
                metadata = json.loads(json_text)
            except:
                # If that fails, try to parse the whole content
                metadata = json.loads(content)
            
            browser.close()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Saved to {output_file}")
        return metadata
    except Exception as e:
        print(f"  ✗ Error downloading metadata: {e}")
        # Try with requests as fallback
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            metadata = response.json()
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            print(f"  ✓ Saved to {output_file} (via requests fallback)")
            return metadata
        except Exception as e2:
            print(f"  ✗ Fallback also failed: {e2}")
            return {}


def download_images(building_id: str, metadata: dict) -> None:
    """
    Download images from metadata using Playwright for protected URLs
    Images are at: https://werk-material.crb.ch/api/project-media/{project_id}/{image_id}
    Metadata format: [{"id":68602,"name":"Bild","mimeType":"image/jpeg","order":0,...},...]
    """
    if not metadata:
        return
    
    output_dir = DATA_DIR / building_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract image data from metadata
    # Metadata should be a list of image objects with 'id', 'name', 'mimeType', etc.
    images = []
    
    if isinstance(metadata, list):
        images = metadata
    elif isinstance(metadata, dict):
        # Check if there's an images/media array in the metadata
        if 'images' in metadata:
            images = metadata['images']
        elif 'media' in metadata:
            images = metadata['media']
        elif 'data' in metadata:
            images = metadata['data']
    
    if not images:
        print(f"  No images found in metadata")
        return
    
    print(f"  Found {len(images)} images to download")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # Use saved auth state if available
        if AUTH_STATE_FILE.exists():
            context = browser.new_context(storage_state=str(AUTH_STATE_FILE))
        else:
            context = browser.new_context()
        
        for idx, image_info in enumerate(images, 1):
            try:
                # Extract image ID and name from metadata
                if isinstance(image_info, dict):
                    image_id = image_info.get('id')
                    image_name = image_info.get('name', f'image_{idx}')
                    mime_type = image_info.get('mimeType', 'image/jpeg')
                    
                    # Determine file extension from mime type
                    ext = mime_type.split('/')[-1] if '/' in mime_type else 'jpg'
                    
                    # Create safe filename from image name
                    safe_name = image_name.replace('/', '-').replace('\\', '-').replace(' ', '_')
                    filename = f"{image_info.get('order', idx):02d}_{safe_name}.{ext}"
                    
                    # Construct the image URL
                    image_url = f"https://werk-material.crb.ch/api/project-media/{building_id}/{image_id}"
                else:
                    # Fallback if metadata format is unexpected
                    continue
                
                output_file = output_dir / filename
                
                print(f"    Downloading image {idx}/{len(images)}: {filename}")
                
                # Use Playwright to fetch the image
                page = context.new_page()
                response = page.goto(image_url, timeout=60000)
                
                if response and response.ok:
                    # Save the image
                    with open(output_file, 'wb') as f:
                        f.write(response.body())
                    print(f"    ✓ Saved to {output_file}")
                else:
                    print(f"    ✗ Failed to fetch image (status: {response.status if response else 'unknown'})")
                
                page.close()
                time.sleep(0.5)
                
            except Exception as e:
                print(f"    ✗ Error downloading image: {e}")
        
        browser.close()


def login_and_save_state():
    """
    Interactive login and save browser state to file
    """
    print("\n" + "=" * 60)
    print("AUTHENTICATION: Manual Login Required")
    print("=" * 60)
    print(f"\nOpening browser to: https://werk-material.crb.ch")
    print("Please log in manually in the browser window.")
    print(f"After logging in, press ENTER in this terminal to save the session.")
    print(f"Session will be saved to: {AUTH_STATE_FILE}\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        page.goto("https://werk-material.crb.ch", wait_until="networkidle", timeout=60000)
        
        print("Press ENTER when you have finished logging in...")
        input()
        
        # Save the entire session state
        context.storage_state(path=str(AUTH_STATE_FILE))
        print(f"\n✓ Session saved to: {AUTH_STATE_FILE}")
        print("You can now run the script without --login to download data.\n")
        
        browser.close()


def main():
    """
    Main function to execute Task 1 and Task 2
    """
    import sys
    
    # Check if login is needed
    if not AUTH_STATE_FILE.exists():
        print("=" * 60)
        print("AUTHENTICATION REQUIRED")
        print("=" * 60)
        print(f"Auth state file not found: {AUTH_STATE_FILE}")
        print("\nTo login and save your session:")
        print("  python download_buildings.py --login")
        print("\nThen run without --login to download data")
        
        if len(sys.argv) > 1 and sys.argv[1] == "--login":
            login_and_save_state()
            return
        else:
            print("\nError: Please login first with --login flag")
            return
    
    print("=" * 60)
    print("TASK 1: Extract building IDs")
    print("=" * 60)
    
    building_ids = extract_building_ids()
    
    print("\n" + "=" * 60)
    print("TASK 2: Download data for each building")
    print("=" * 60)
    
    for building_id in building_ids:
        print(f"\nProcessing building ID: {building_id}")
        print("-" * 60)
        
        output_dir = DATA_DIR / building_id
        metadata_file = output_dir / "metadata.json"
        
        # Check if metadata.json already exists
        if metadata_file.exists():
            print(f"  metadata.json already exists, skipping downloads")
            continue
        
        # Download HTML datasheet
        download_html(building_id)
        
        # Download metadata JSON
        metadata = download_metadata(building_id)
        
        # Download images
        download_images(building_id, metadata)
        
        # Be polite to the server
        time.sleep(1)
    
    print("\n" + "=" * 60)
    print("COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
