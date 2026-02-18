#!/usr/bin/env python3
"""
Generate PDF documents for building addresses.

Fetches maps, Street View images, and building data for each address in an Excel file,
then generates a PDF with all the information.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
from dotenv import load_dotenv
import os
import requests
from services.geocoding_service import GeocodingService
from services.streetview_service import StreetViewService
from services.map_service import MapService
from services.zh_map_service import ZhMapService
from services.building_data_service import BuildingDataService
from generators.pdf_generator import PDFGenerator
import urllib.parse
from tqdm import tqdm
import time

def generate_google_links(lat, lon, address, feature_id, egid):
    # Encode the address for URLs
    encoded_address = urllib.parse.quote(address)

    # Normal Google Maps link centered at coordinates
    maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

    # Street View link (interactive panorama)
    streetview_url = (
        f"https://www.google.com/maps/@?api=1"
        f"&map_action=pano"
        f"&viewpoint={lat},{lon}&pitch=25"
    )
    
    # --- Swiss geo.admin.ch map ---
    geo_admin_register_url = (
        f"https://api3.geo.admin.ch/rest/services/api/MapServer/ch.bfs.gebaeude_wohnungs_register/{feature_id}"
    )
    
    # --- Zürich map using EGID ---
    zh_map_url = f"https://maps.zh.ch/?locate=egid&locations={egid}&collapsed=lrt&scale=600"
    
    return {
        "address": address,
        "maps_url": maps_url,
        "streetview_url": streetview_url,
        "geo_admin_register_url": geo_admin_register_url,
        "zh_map_url": zh_map_url
    }

def download_tile(url, name, outdir="output/images"):
    os.makedirs(outdir, exist_ok=True)
    r = requests.get(url)
    r.raise_for_status()
    filename = f"{outdir}/{name}.jpeg"
    if os.path.exists(filename):
        return filename
    with open(filename, "wb") as f:
        f.write(r.content)
    return filename

def main():
    load_dotenv()
    api_key = os.getenv('API_KEY_GOOGLE_MAPS')
    if not api_key:
        raise ValueError("API_KEY_GOOGLE_MAPS not found in .env file")
    
    # Load addresses from an Excel file
    df = pd.read_excel('data/0 251111 gesendet kuhs + gava/EGID_Export_Winti-ReUse_Gebauede_OK_Mit_Baujahr_UNIQUE 251030 gui.xlsx')

    # Initialize services
    geocoding_service = GeocodingService()
    street_view_service = StreetViewService(api_key)
    map_service = MapService()
    zh_map_service = ZhMapService()
    building_data_service = BuildingDataService()
    pdf_generator = PDFGenerator()
    
    # Process each address with progress bar
    for index, row in tqdm(df.iterrows(), total=len(df), desc="Processing addresses"):
        egid = row['EGID']
        street = row['STRASSENNAME']
        house_number = row['HAUSNR']
        hauptnutzung = row['HAUPTNUTZUNG']
        nutzung = row['NUTZUNG']
        gs_eigentumskat = row['GS_EIGENTUMSKATEGORIE']
        gs_eigentumskat_zusatz = row['GS_EIGENTUMSKAT_ZUSATZ']
        baujahr = row['BAUJAHR']

        address = f"{street} {house_number}, Winterthur"
        
        # Check if PDF already exists
        safe_address = address.replace("/", "-").replace(" ", "_")
        pdf_filename = f"output/pdfs/{safe_address}.pdf"
        
        if os.path.exists(pdf_filename):
            tqdm.write(f"Skipping {address} (EGID: {egid}) - PDF already exists")
            continue
        
        try:
            # Geocode address to get coordinates
            lon, lat, feature_id, x, y = geocoding_service.geocode_address(address)
            
            # Fetch detailed building data from geo.admin API
            building_data_api = building_data_service.fetch_building_data(egid)
            
            # Fetch all map types
            map_urls = map_service.fetch_all_maps(lon, lat)
            map_image_paths = {}
            for map_type, url in map_urls.items():
                map_image_paths[map_type] = download_tile(url, f'map_{map_type}_{index}')
            
            # Fetch street view (API image)
            street_view_url = street_view_service.fetch_street_view(lon, lat)
            street_view_image_path = download_tile(street_view_url, f'streetview_{index}')
            
            # Fetch street view screenshot (interactive)
            street_view_screenshot_path = street_view_service.fetch_street_view_screenshot(lon, lat, address)
            map_image_paths['streetview-interactive'] = street_view_screenshot_path
            
            # Fetch ZH map screenshots using EGID
            zh_map_main, zh_map_ortho = zh_map_service.fetch_zh_map_screenshot_by_egid(egid, address)
            map_image_paths['zh-map'] = zh_map_main
            if zh_map_ortho:
                map_image_paths['zh-map-ortho'] = zh_map_ortho
            
            # Generate URLs
            urls = generate_google_links(lat, lon, address, feature_id, egid)
            
            # Prepare building info from Excel
            building_info = {
                'hauptnutzung': hauptnutzung,
                'nutzung': nutzung,
                'gs_eigentumskat': gs_eigentumskat,
                'gs_eigentumskat_zusatz': gs_eigentumskat_zusatz,
                'baujahr': baujahr
            }

            # Generate PDF for the address
            pdf_generator.generate_pdf(address, egid, street_view_image_path, map_image_paths, urls, building_info, building_data_api)
            
        except Exception as e:
            tqdm.write(f"Error processing {address} (EGID: {egid}): {e}")
            continue
        
        time.sleep(1)
        


if __name__ == "__main__":
    main()
