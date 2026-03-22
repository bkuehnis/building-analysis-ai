"""
Script to collect building data for a single address and save results in Excel.
Usage:
python -m prediction_model.collect_building_data --address "Guggenbühlstrasse 140a 8404 Winterthur"
"""
from prediction_model.services.geo_admin_service import GeoAdminService
from prediction_model.services.building_image_service import ImageService
from prediction_model.services.openai_feature_service import OpenAIFeatureService
from prediction_model.services.prediction_service import PredictionService 

import os
import argparse
import pandas as pd
from dotenv import load_dotenv
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]

def normalize_key(k: str) -> str:
    if k.endswith("_confidence"):
        return k[:-11].upper() + "_confidence"
    if k.endswith("_unit"):
        return k[:-5].upper() + "_unit"
    return k.upper()


def flatten_extraction(features: BuildingImageExtraction) -> dict:
    raw = features.model_dump()
    flat = {}

    for key, val in raw.items():
        out_key = normalize_key(key)

        if isinstance(val, dict):
            value_str = val.get("value_str")
            value_num = val.get("value_num")
            confidence = val.get("confidence")
            unit = val.get("unit")

            flat[out_key] = value_num if value_num is not None else value_str
            flat[f"{out_key}_confidence"] = confidence

            if unit is not None:
                flat[f"{out_key}_unit"] = unit
        else:
            flat[out_key] = val

    return flat

def clean_none_values(flat: dict) -> dict:
        for key, value in flat.items():
            
            # nur für value-Felder, nicht confidence
            if key.endswith("confidence"):
                continue
            
            if value is None:
                conf = flat.get(f"{key}_confidence", 0)

                if conf >= 0.6:
                    flat[key] = "NEIN"
                else:
                    flat[key] = "UNBEKANNT"

        return flat
    
def derive_material_flags(flat: dict) -> dict:
    fassade = flat.get("FASSADE_BEKLEIDUNG")
    if isinstance(fassade, str):
        fassade_upper = fassade.upper()

        if "HOLZ" in fassade_upper:
            flat["HOLZ"] = "JA"
        if "STAHLBLECH" in fassade_upper:
            flat["STAHLBLECH"] = "JA"
        if "STAHL" in fassade_upper:
            flat["STAHL"] = "JA"
        if "ETERNIT" in fassade_upper:
            flat["ETERNIT"] = "JA"
        if "STEINPLATTEN" in fassade_upper or "STEIN" in fassade_upper:
            flat["STEINPLATTEN"] = "JA"
        if "BETON" in fassade_upper:
            flat["BETON"] = "JA"

    dach = flat.get("DACH_BEKLEIDUNG")
    if isinstance(dach, str):
        dach_upper = dach.upper()

        if "DACHZIEGEL" in dach_upper or "ZIEGEL" in dach_upper:
            flat["DACHZIEGEL"] = "JA"
        if "STAHLBLECH" in dach_upper:
            flat["STAHLBLECH"] = "JA"
        if "ETERNIT" in dach_upper:
            flat["ETERNIT"] = "JA"
        if "DACHZIEGEL" in dach_upper or "ZIEGEL" in dach_upper:
            flat["DACH_BEKLEIDUNG"] = "ZIEGEL"

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
    
    i = 0
    lat += 0.00005  # leicht versetzen, damit Google unterschiedliche Bilder liefert
    lon += 0.00005
    for i in range(i, 3):
        print(f"Downloading Street View image {i+1}/3...")

        street_path = image_service.download_image(
            "https://maps.googleapis.com/maps/api/streetview"
            f"?size=640x640"
            f"&location={lat},{lon}"
            f"&radius=23"
            f"&source=outdoor"
            f"&fov=90"
            f"&key={google_api_key}",
            name=f"streetview_{i+1}_{result['EGID']}",
            outdir=f"prediction_model/output/images/{result['EGID']}",
        )
        lat -= 0.00005  # leicht versetzen, damit Google unterschiedliche Bilder liefert
        lon -= 0.00005

    i = 0
    lat += 0.00005  # leicht versetzen, damit Google unterschiedliche Bilder liefert
    lon += 0.00005
    for i in range (i, 3):
        print(f"Downloading zoomed Street View image {i+1}/3...")

        street_path_zoomed = image_service.download_image(
            "https://maps.googleapis.com/maps/api/streetview"
            f"?size=640x640"
            f"&location={lat},{lon}"
            f"&radius=10"
            f"&source=outdoor"
            f"&fov=60"
            f"&key={google_api_key}",
            name=f"streetview_zoomed_{i+1}_{result['EGID']}",
            outdir=f"prediction_model/output/images/{result['EGID']}",
        )
        lat -= 0.00005  # leicht versetzen, damit Google unterschiedliche Bilder liefert
        lon -= 0.00005
    
    
    e95, n95 = image_service.ensure_lv95_xy(x, y)

    print(f"LV95 coordinates for WMS: E={e95}, N={n95}")


    # Orthofoto (50m) + Orthofoto (20m) + Katasterplan (50m)
    ortho_url = image_service.build_wms_url(e95, n95, layer="ch.swisstopo.swissimage", meters=50, width=1024, height=1024,image_format="image/jpeg")
    ortho_zoomed_url = image_service.build_wms_url(e95, n95, layer="ch.swisstopo.swissimage", meters=20, width=1024, height=1024,image_format="image/jpeg")
    plain_url = image_service.build_wms_url(e95, n95, layer="ch.swisstopo-vd.amtliche-vermessung", meters=50, width=1024, height=1024, image_format="image/png")

    ortho_path = image_service.download_image(
        ortho_url,
        name=f"swissimage_{feature_id}",
        outdir=f"prediction_model/output/images/{result['EGID']}",          # ✅ gleiches outdir
    )
    print("Orthofoto saved:", ortho_path)

    ortho_zoomed_path = image_service.download_image(
        ortho_zoomed_url,
        name=f"swissimage_zoomed_{feature_id}",
        outdir=f"prediction_model/output/images/{result['EGID']}",          # ✅ gleiches outdir
    )
    print("Orthofotos saved:", ortho_zoomed_path)

    plain_path = image_service.download_image(
        plain_url,
        name=f"cadastral_{feature_id}",
        outdir=f"prediction_model/output/images/{result['EGID']}",          # ✅ gleiches outdir
    )
    print("Cadastral map saved:", plain_path)

    

    # Gebäude markieren und in ordner "marked" speichern
    os.makedirs(f"prediction_model/output/images/{result['EGID']}/marked", exist_ok=True)

    marked_ortho_path = image_service.draw_marker(
        ortho_path,  # ✅ URL mit layer-Parameter
        out_path=f"prediction_model/output/images/{result['EGID']}/marked/{result['EGID']}.jpeg",  # ✅ .jpeg konsistent
    )

    marked_zoomed_ortho_path = image_service.draw_marker(
        ortho_zoomed_path,  # ✅ URL mit layer-Parameter
        out_path=f"prediction_model/output/images/{result['EGID']}/marked/zoomed_{result['EGID']}.jpeg",  #✅ .jpeg konsistent
    )

    marked_plain_path = image_service.draw_marker(
        plain_path,  # ✅ URL mit layer-Parameter
        out_path=f"prediction_model/output/images/{result['EGID']}/marked/cadastral_{result['EGID']}.jpeg",  # ✅ .jpeg konsistent
    )
    
    
    # ---------------------------------------------------------
    # DATAFRAME
    # ---------------------------------------------------------
    print("Extracting features with OpenAI...")

    feature_service = OpenAIFeatureService(api_key=openai_api_key, model="gpt-4o")

    features = feature_service.extract_features(
        image_paths=[street_path, street_path_zoomed, marked_ortho_path, marked_plain_path, marked_zoomed_ortho_path]
    )

    flat = flatten_extraction(features)
    flat = {k: (v.upper() if isinstance(v, str) else v) for k, v in flat.items()}

    flat = derive_material_flags(flat)
    flat = clean_none_values(flat)

    print("Extracted features:", flat)

    result.update(flat)

    df = pd.DataFrame([result])

    address_parts = GeoAdminService.parse_user_address(result.get("ADDRESS", ""))
    df["STRASSE"] = address_parts.get("street", "").title()
    df["HAUSNR"] = address_parts.get("nr", "")
    df["HAUSNRZUSATZ"] = address_parts.get("suffix", "")
    df["ORT"] = address_parts.get("city", "").title()
    df["PLZ"] = address_parts.get("plz", "")

    df["FENSTER"] = df.apply(
        lambda row: "AB 1990" if pd.notna(row["BAUJAHR"]) and row["BAUJAHR"] > 1990 else row["FENSTER"],
        axis=1
    )

    df["FENSTER_confidence"] = df.apply(
        lambda row: 1.0 if pd.notna(row["BAUJAHR"]) and row["BAUJAHR"] > 1990 else row.get("FENSTER_confidence", 0.0),
        axis=1
    )

    base_cols = [
        "EGID", "GSW_STATUS", "STRASSE", "HAUSNR", "HAUSNRZUSATZ",
        "PLZ", "ORT", "BAUJAHR"
    ]
    feature_cols = list(flat.keys())

    drop_cols = {"ADDRESS", "lat", "lon", "x", "y", "feature_id"}

    # wenn spalten fehlen hinzufügen
    REQUIRED_COLS = [
    
        "EGID", "GSW_STATUS", "HAUPTNUTZUNG", "NUTZUNG", "BAUJAHR",
        "TRAGWERK_FASSADE", "FASSADE_DAEMMUNG", "FASSADE_BEKLEIDUNG", "KONSTRUKTION_DECKE",
        "BODENAUFBAU", "KONSTRUKTION_DACH", "DACH_BEKLEIDUNG", "PHOTOVOLTAIK", "PV_FLAECHE",
        "FENSTER", "FENSTERANZAHL", "DAEMMUNGSFLAECHE", "STAHL", "STAHL_LM", "STAHLBLECH",
        "STAHLBLECH_FLAECHE", "ETERNIT", "ETERNIT_FLAECHE", "STEINPLATTEN",
        "STEINPLATTEN_FLAECHE", "DACHZIEGEL", "DACHZIEGEL_FLAECHE", "BETON", "BETON_FLAECHE",
        "HOLZ", "HOLZ_LM", "HOLZ_FLAECHE", "STRASSE", "HAUSNR", "HAUSNRZUSATZ", "PLZ", "ORT"
    
    ]
    cols = base_cols + feature_cols
    cols = [col for col in cols if col not in drop_cols]
    cols = list(dict.fromkeys(cols + REQUIRED_COLS))

    df = df.reindex(columns=cols)

    # ---------------------------------------------------------
    # SAVE
    # ---------------------------------------------------------
    output_file = "prediction_model/data/collected_building_data.xlsx"
    os.makedirs("prediction_model/data", exist_ok=True)
    df.to_excel(output_file, index=False)

    print(f"📁 Results saved to {output_file}")

    # ---------------------------------------------------------
    # prediction service call with services/prediction_service.py
    # ---------------------------------------------------------
  
    MODEL_PATH = PROJECT_ROOT / os.getenv("OUTPUT_MODEL_PATH")

    #tragwerk_fassade prediction
    CB_MODEL_PATH_TRAGWERK = MODEL_PATH / "tragwerk_fassade" / "saved_models" / "catboost_final_model.cbm"
    prediction_service_tragwerk = PredictionService(model_path=CB_MODEL_PATH_TRAGWERK, required_columns=["BAUJAHR",
    "HOLZ",
    "STAHL",
    "STAHLBLECH",
    "BETON",
    "HAUPTNUTZUNG",
    "FASSADE_DAEMMUNG",
    "FASSADE_BEKLEIDUNG",
    "KONSTRUKTION_DACH",])  
    pred_tragwerk = prediction_service_tragwerk.predict(features=df.iloc[0].to_dict())
    print("\n""Tragwerk Fassade Prediction result:", pred_tragwerk)

    prediction_service_rf_tragwerk = PredictionService(model_path=MODEL_PATH / "tragwerk_fassade" / "saved_models" / "random_forest_model.pkl", 
    required_columns=["BAUJAHR",
    "HOLZ",
    "STAHL",
    "STAHLBLECH",
    "BETON",
    "HAUPTNUTZUNG",
    "FASSADE_DAEMMUNG",
    "FASSADE_BEKLEIDUNG",
    "KONSTRUKTION_DACH"],
    feature_columns_path= MODEL_PATH / "tragwerk_fassade" / "saved_models" / "feature_columns.pkl")
    pred_rf_tragwerk = prediction_service_rf_tragwerk.predict(features=df.iloc[0].to_dict())
    print("\n""Tragwerk Fassade Random Forest Prediction result:", pred_rf_tragwerk)

    #save prediciton of tragewerk_fassade in df
    df["TRAGWERK_FASSADE"] = pred_tragwerk.get("prediction", "UNBEKANNT")
    df["TRAGWERK_FASSADE_confidence"] = pred_tragwerk.get("confidence", 0.0)

    df.to_excel(output_file, index=False)
    print(f"📁 Predictions saved to {output_file}")

    # schadstoffen
    CB_MODEL_PATH = MODEL_PATH / "schadstoff" / "saved_models" / "catboost_final_model.cbm"  # Beispiel: Pfad zum gespeicherten CatBoost-Modell
    #call prediction service
    prediction_service = PredictionService(model_path=CB_MODEL_PATH, required_columns=["BAUJAHR",
    "TRAGWERK_FASSADE",
    "FASSADE_DAEMMUNG",
    "FASSADE_BEKLEIDUNG",
    "KONSTRUKTION_DACH",
    "DACH_BEKLEIDUNG",
    "PHOTOVOLTAIK",
    "FENSTER"])  
    pred = prediction_service.predict(features=df.iloc[0].to_dict())  # Vorhersage für die gesammelten Daten der Adresse
    print("\n""Prediction result:", pred)

    prediction_service_rf = PredictionService(
        model_path=MODEL_PATH / "schadstoff" / "saved_models" / "random_forest_model.pkl",
        required_columns=["BAUJAHR",
    "TRAGWERK_FASSADE",
    "FASSADE_DAEMMUNG",
    "FASSADE_BEKLEIDUNG",
    "KONSTRUKTION_DACH",
    "DACH_BEKLEIDUNG",
    "PHOTOVOLTAIK",
    "FENSTER"],
        feature_columns_path= MODEL_PATH / "schadstoff" / "saved_models" / "feature_columns.pkl",
    )
    pred_rf = prediction_service_rf.predict(features=df.iloc[0].to_dict())  # Vorhersage für die gesammelten Daten der Adresse
    print("\n""Random Forest Prediction result:", pred_rf)

if __name__ == "__main__":
    main()