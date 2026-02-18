import pandas as pd
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer

from src.services.geocoding_service import GeocodingService
from src.services.building_data_service import BuildingDataService

# 1) Load data
df = pd.read_excel(
    "data/buildings/Gebaeudescreening_winti.xlsx",
    sheet_name="Gebaeude Screening",
    header=8
)

# 2) Target conversion (multi-class, impute missing)
df["Tragwerk Fassade6"] = df["Tragwerk Fassade6"].fillna("unknown").astype(str)

# 3) Basic feature cleanup
df["HAUSNR"] = pd.to_numeric(df["HAUSNR"], errors="coerce")
df["PLZ4"] = pd.to_numeric(df["PLZ4"], errors="coerce")
df["BAUJAHR"] = pd.to_numeric(df["BAUJAHR"], errors="coerce")

# 4) Build address (for geocoding)
df["address"] = (
    df["STRASSENNAME"].fillna("") + " " + df["HAUSNR"].fillna("").astype(str) + ", " + df["ORT"].fillna("")
).str.strip()

# 5) Derived features from services
geo = GeocodingService()
building_service = BuildingDataService()

def enrich_row(row):
    features = {}
    try:
        lon, lat, feature_id, x, y = geo.geocode_address(row["address"])
        features.update({
            "lon": lon,
            "lat": lat,
            "feature_id": feature_id,
            "x_lv95": x,
            "y_lv95": y,
        })
    except Exception:
        features.update({
            "lon": None,
            "lat": None,
            "feature_id": None,
            "x_lv95": None,
            "y_lv95": None,
        })

    # Use EGID to pull structured building data
    try:
        building_data = building_service.fetch_building_data(row["EGID"])
        # Flatten a few example fields (choose what you want)
        # Example: "Allgemein" section, "Gebäudeart", etc.
        for section, values in building_data.items():
            if isinstance(values, dict):
                for k, v in values.items():
                    col = f"bd_{section}_{k}"
                    features[col] = v
    except Exception:
        pass

    return pd.Series(features)

derived = df.apply(enrich_row, axis=1)

# 6) Combine raw + derived features
df_all = pd.concat([df, derived], axis=1)

# 7) Define feature columns
numeric_features = [
    "EGID", "GEB_GEBID", "HAUSNR", "PLZ4", "BAUJAHR",
    "lon", "lat", "x_lv95", "y_lv95"
]

categorical_features = [
    "GSW_STATUS", "STRASSENNAME", "HAUSNRZUSATZ", "ORT", "STADTKREIS",
    "HAUPTNUTZUNG", "NUTZUNG", "GS_EIGENTUMSKATEGORIE", "GS_EIGENTUMSKAT_ZUSATZ"
]

# 8) Encode categorical features
preprocessor = ColumnTransformer(
    transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
    ],
    remainder="passthrough"
)

X = df_all[numeric_features + categorical_features]
y = df_all["Tragwerk Fassade6"]