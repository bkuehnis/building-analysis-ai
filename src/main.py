import pandas as pd
from dotenv import load_dotenv
import os
import requests
from services.geocoding_service import GeocodingService
from services.streetview_service import StreetViewService
from services.map_service import MapService
from services.birdseye_service import BirdseyeService
from generators.pdf_generator import PDFGenerator

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
    birdseye_service = BirdseyeService()
    pdf_generator = PDFGenerator()
    
    # Process each address
    for index, row in df.iterrows():
        street = row['STRASSENNAME']
        house_number = row['HAUSNR']
        address = f"{street} {house_number}, Winterthur"
        print(address)
        
        # Geocode address to get coordinates
        lon, lat = geocoding_service.geocode_address(address)
        print(f" → lon={lon}, lat={lat}")
        
        # Fetch images using coordinates
        map_image = map_service.fetch_map(lon, lat)
        download_tile(map_image, 'map_image')
        
        street_view_image = street_view_service.fetch_street_view(lon, lat)        
        download_tile(street_view_image, 'street_view_image')
        exit()
        #birdseye_image = birdseye_service.fetch_birdseye_view(lon, lat)

        # Generate PDF for the address
        #pdf_generator.generate_pdf(address, street_view_image, map_image, birdseye_image)


def download_tile(url, name, outdir="tiles"):
    print(url)
    r = requests.get(url)
    r.raise_for_status()
    filename = f"{outdir}/tile_{name}.jpeg"
    with open(filename, "wb") as f:
        f.write(r.content)

    return filename

if __name__ == "__main__":
    main()