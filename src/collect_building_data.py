"""
Script to collect building data for a single address and save results in Excel.
Usage:
    python -m src.collect_building_data --address "Guggenbühlstrasse 140a 8404 Winterthur"
"""
from services.geo_admin_service import GeoAdminService
from services.building_image_service import ImageService
from services.openai_feature_service import OpenAIFeatureService
import os
import argparse
import pandas as pd
from dotenv import load_dotenv

def flatten_extraction(features):
    flat = {}

    for field_name, field_value in features.model_dump().items():

        if not isinstance(field_value, dict):
            continue

        value_str = field_value.get("value_str")
        value_num = field_value.get("value_num")

        # value_str hat Priorität, sonst value_num
        if value_str is not None:
            flat[field_name] = value_str
        else:
            flat[field_name] = value_num

        flat[field_name + "_confidence"] = field_value.get("confidence")

        # optional: unit speichern
        unit = field_value.get("unit")
        if unit:
            flat[field_name + "_unit"] = unit

    return flat

def main():
    load_dotenv()

    # ---------------------------------------------------------
    # ENV CHECK
    # ---------------------------------------------------------
    google_api_key = os.getenv("API_KEY_GOOGLE_MAPS")
    if not google_api_key:
        raise ValueError("API_KEY_GOOGLE_MAPS not found in .env file")

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file")

    # ---------------------------------------------------------
    # CLI
    # ---------------------------------------------------------
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", type=str, required=True, help="Single address test")
    args = parser.parse_args()

    address = args.address
    print("Testing single address:", address)
    

    # ---------------------------------------------------------
    # GEO ADMIN SERVICE
    # ---------------------------------------------------------
    geo_service = GeoAdminService()

    try:
        result = geo_service.collect_building_data(address)
    except ValueError as e:
        print(f"❌ {e}")
        return

        print("✅ Address found:", (hit.get("attrs") or {}).get("label", ""))

    #  geocode
    lon, lat, feature_id, x, y = result.get("LON"), result.get("LAT"), result.get("EGID"), result.get("X"), result.get("Y")
    print("Coordinates:", lat, lon)
    print("Feature ID:", feature_id)

    print(result)

    #---------------------------------------------------------
    # IMAGE SERVICE
    #---------------------------------------------------------

    image_service = ImageService()

    result = geo_service.collect_building_data(address)

    lat = result["lat"]
    lon = result["lon"]
    x = result["x"]
    y = result["y"]
    feature_id = result["feature_id"]

    print("Coordinates:", lat, lon)
    print("Feature ID:", feature_id)

    tile_path = image_service.download_image(
        "https://maps.googleapis.com/maps/api/streetview"
        f"?size=600x400&location={lat},{lon}"
        f"&key={google_api_key}",
        name=f"streetview_{result['EGID']}",
        outdir="output/images",
    )

    e95, n95 = image_service.ensure_lv95_xy(x, y)

    # Orthofoto via WMS
    ortho_url = image_service.build_swissimage_wms_url(e95, n95, meters=80, width=1024, height=1024)

    ortho_path = image_service.download_image(
        ortho_url,
        name=f"swissimage_{feature_id}",
        outdir="output/images",          # ✅ gleiches outdir
    )
    print(f"LV95 coordinates for WMS: E={e95}, N={n95}")
    print("Orthofoto saved:", ortho_path)

    # markieren
    marked_path = image_service.draw_marker(
        ortho_path,
        out_path=f"output/images/marked_{feature_id}.jpeg",  # ✅ .jpeg konsistent
    )

    # ---------------------------------------------------------
    # DATAFRAME
    # ---------------------------------------------------------
    # 1) OpenAI Features holen + in result mergen
    feature_service = OpenAIFeatureService(api_key=openai_api_key, model="gpt-4o")

    features = feature_service.extract_features(
        image_paths=[tile_path, marked_path]  # streetview + marked orthophoto
    )

    result.update(flatten_extraction(features))

    # 2) DataFrame erst JETZT bauen (damit Features drin sind)
    df = pd.DataFrame([result])

    # 3) Adresse zerlegen (Parser)
    address_parts = GeoAdminService.parse_user_address(result.get("ADDRESS", ""))

    df["STRASSE"] = address_parts["street"]
    df["HAUSNR"] = address_parts["nr"]
    df["HAUSNRZUSATZ"] = address_parts["suffix"]
    df["PLZ"] = address_parts["plz"]
    df["ORT"] = address_parts["city"]

    # 4) Spaltenreihenfolge (Basis + Bildfeatures)
    cols = [
        "EGID", "GSW_STATUS", "STRASSE", "HAUSNR", "HAUSNRZUSATZ",
        "PLZ", "ORT", "STADTKREIS", "BAUJAHR",
        "HAUPTNUTZUNG", "NUTZUNG",

        # Bildfeatures (deine Felder)
        "tragwerk_fassade", "fassade_daemmung", "fassade_bekleidung",
        "fenster", "fensteranzahl", "daemmungsflaeche",
        "konstruktion_dach", "dach_bekleidung", "photovoltaik", "pv_flaeche",
        "konstruktion_decke", "bodenaufbau",
        "stahl", "stahl_lm", "stahlblech", "stahlblech_flaeche",
        "eternit", "eternit_flaeche", "steinplatten", "steinplatten_flaeche",
        "dachziegel", "dachziegel_flaeche", "beton", "beton_flaeche",
        "holz", "holz_lm", "holz_flaeche", "speziell", "speziell_flaeche", "extra",
    ]


    confidence_cols = [f + "_confidence" for f in cols]

    # Alle Spalten: Basis + Bildfeatures + confidence
    cols += confidence_cols

    # 5) robust: fehlende Spalten automatisch anlegen
    for c in cols:
        if c not in df.columns:
            df[c] = pd.NA

    df = df[cols].fillna(pd.NA)

    # ---------------------------------------------------------
    # SAVE
    # ---------------------------------------------------------
    output_file = "data/processed/collected_building_data.xlsx"
    os.makedirs("data/processed", exist_ok=True)
    df.to_excel(output_file, index=False)

    print(f"📁 Results saved to {output_file}")



if __name__ == "__main__":
    main()