import pandas as pd
from dotenv import load_dotenv
import os
import requests
from services.geocoding_service import GeocodingService
from services.streetview_service import StreetViewService
from services.map_service import MapService
from services.birdseye_service import BirdseyeService
from generators.pdf_generator import PDFGenerator
import urllib.parse

def generate_google_links(lat, lon, address, feature_id):
    # Encode the address for URLs
    encoded_address = urllib.parse.quote(address)

    # Normal Google Maps link centered at coordinates
    maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

    # Street View link (interactive panorama)
    streetview_url = (
        f"https://www.google.com/maps/@?api=1"
        f"&map_action=pano"
        f"&viewpoint={lat},{lon}"
    )
    
    # --- Swiss geo.admin.ch map ---
    geo_admin_register_url = (
        f"https://api3.geo.admin.ch/rest/services/api/MapServer/ch.bfs.gebaeude_wohnungs_register/{feature_id}"
    )
    print(geo_admin_register_url)
    return {
        "address": address,
        "maps_url": maps_url,
        "streetview_url": streetview_url,
        "geo_admin_register_url": geo_admin_register_url
    }

def download_tile(url, name, outdir="output/images"):
    os.makedirs(outdir, exist_ok=True)
    print(f"Downloading: {url}")
    r = requests.get(url)
    r.raise_for_status()
    filename = f"{outdir}/{name}.jpeg"
    with open(filename, "wb") as f:
        f.write(r.content)
    return filename

def main():
    load_dotenv()
    api_key = os.getenv('API_KEY_GOOGLE_MAPS')
    if not api_key:
        raise ValueError("API_KEY_GOOGLE_MAPS not found in .env file")
    
    # Load addresses from an Excel file
    df = pd.read_excel('data/0 251111 gesendet kuhs + gava/1_EGID_Export_Winti-ReUse_nur Adresse_UNIQUE 251011.xlsx')

    # Initialize services
    geocoding_service = GeocodingService()
    street_view_service = StreetViewService(api_key)
    map_service = MapService()
    pdf_generator = PDFGenerator()
    
    # Process each address
    for index, row in df.iterrows():
        street = row['STRASSENNAME']
        house_number = row['HAUSNR']
        address = f"{street} {house_number}, Winterthur"
        print(f"\nProcessing: {address}")
        
        # Geocode address to get coordinates
        lon, lat, feature_id = geocoding_service.geocode_address(address)
        print(f" → lon={lon}, lat={lat}", f"feature_id={feature_id}")
        
        # Fetch all map types
        map_urls = map_service.fetch_all_maps(lon, lat)
        map_image_paths = {}
        for map_type, url in map_urls.items():
            map_image_paths[map_type] = download_tile(url, f'map_{map_type}_{index}')
        
        # Fetch street view
        street_view_url = street_view_service.fetch_street_view(lon, lat)
        street_view_image_path = download_tile(street_view_url, f'streetview_{index}')
        
        # Generate URLs
        urls = generate_google_links(lat, lon, address, feature_id)
        
        # Generate PDF for the address
        pdf_generator.generate_pdf(address, street_view_image_path, map_image_paths, urls)
        
        print("-" * 50)
        
        if index == 4:
            break

if __name__ == "__main__":
    main()