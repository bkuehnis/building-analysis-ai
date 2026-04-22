"""
Creates a clean Excel dataset for the Schadstoff (hazardous substances risk) model.

Assumptions (based on your last message):
- The actual table header starts in Excel row 9 (1-based)
  -> pandas header index = 8 (0-based)
- We extract ONLY these columns (if present) and all rows below:
  EGID, GSW_STATUS, BAUJAHR, Reale Baujahr, Schadstoffen,
  Tragwerk Fassade6, Fassade Dämmung, Fassade Bekleidung,
  Konstruktion Decke, Konstruktion Dach, Dach Bekleidung,
  Eternit, Holz, Holz Lm, Extra

Install dependencies:
  pip install pandas openpyxl python-dotenv

Run from project root:
  python scripts/generate_model_dataset.py
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Optional

import pandas as pd
from dotenv import load_dotenv


# =========================
# ENV + PATHS
# =========================
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

INPUT_PATH = (PROJECT_ROOT / os.getenv("EXCEL_FILE_PATH")).resolve()
OUTPUT_PATH = (PROJECT_ROOT / os.getenv("OUTPUT_DATASET_PATH")).resolve()
TEST_DATASET_PATH = (PROJECT_ROOT / os.getenv("TEST_DATASET_PATH")).resolve()

if not INPUT_PATH.exists():
    raise FileNotFoundError(f"Input Excel file not found: {INPUT_PATH}")
if not OUTPUT_PATH.parent.exists():
    raise FileNotFoundError(f"Output directory does not exist: {OUTPUT_PATH.parent}")
if not TEST_DATASET_PATH.parent.exists():
    raise FileNotFoundError(f"Test dataset directory does not exist: {TEST_DATASET_PATH.parent}")
    
# =========================
# CONFIG
# =========================
SHEET_NAME: Optional[int | str] = 0  # use first sheet by default
HEADER_ROW_INDEX = 8  # Excel row 9 -> pandas header index 8

REQUIRED_COLUMNS: List[str] = [
    "EGID",
    "GSW_STATUS",
    "HAUPTNUTZUNG",
    "NUTZUNG",
    "BAUJAHR",
    "Reale Baujahr",
    "Schadstoffen",
    "Tragwerk Fassade6",
    "Fassade Dämmung",
    "Fassade Bekleidung",
    "Konstruktion Decke",
    "Bodenaufbau",
    "Konstruktion Dach",
    "Dach Bekleidung",
    "Photovoltaik",
    "PV Fläche",
    "Fenster",
    "Fensteranzahl",
    "Dämmungsfläche",
    "Stahl",
    "Stahl lm",
    "Stahlblech",
    "Fläche 6",
    "Eternit",
    "Fläche 7",
    "Steinplatten",
    "Fläche 8",
    "Dachziegel",
    "Fläche 9",
    "Beton",
    "Fläche 10",
    "Holz",
    "Holz lm",
    "Fläche 12"
]

# Numerische Spalten sauber konvertieren
numeric_cols = [
        "EGID",
        "BAUJAHR",
        "PV Fläche",
        "Fensteranzahl",
        "Dämmungsfläche",
        "Stahl lm",
        "Fläche 6",
        "Fläche 7",
        "Fläche 8",
        "Fläche 9",
        "Fläche 10",
        "Holz lm",
        "Fläche 12",
]

# Optional: normalize label values for the target column
LABEL_NORMALIZE = {
    "Hohe Chance": "HOHE_CHANCE",
    "Niedrige Chance": "NIEDRIGE_CHANCE",
    "Niedrig Chance": "NIEDRIGE_CHANCE",
    "h.W. Asbest, PCB, PAK": "HW_ASBEST_PCB_PAK",
    "h. W. Asbest, PCB, PAK": "HW_ASBEST_PCB_PAK",
    "h.W. Holzschutzmittel": "HW_HOLZSCHUTZMITTEL",
    "h. W. Holzschutzmittel": "HW_HOLZSCHUTZMITTEL",
    "Ab 1990": "AB_1990",
    "Bevor 1990": "VOR_1990",
    "bestehend": "Bestehend",
    "im Bau": "Im Bau",
    "projektiert": "Projektiert"
}

YESNO_VALUES = {
    "ja": "JA",
    "j": "JA",
    "js": "JA",
    "ja (dach)": "JA",
    "Ja": "JA",
    "J": "JA",
    "yes": "JA",
    "true": "JA",
    "1": "JA",
    "nein": "NEIN",
    "n": "NEIN",
    "Nein": "NEIN",
    "N": "NEIN",
    "no": "NEIN",
    "false": "NEIN",
    "0": "NEIN",
}

YESNO_LIKE_COLS = {"Eternit", "Holz","Stahl", "Stahlblech", "Beton", "Steinplatten", "Dachziegel", "Photovoltaik"}

#rename columns to match collected building data   
COLUMN_RENAME = {
    "Tragwerk Fassade6": "TRAGWERK_FASSADE",
    "Fassade Dämmung": "FASSADE_DAEMMUNG",
    "Fassade Bekleidung": "FASSADE_BEKLEIDUNG",
    "Konstruktion Decke": "KONSTRUKTION_DECKE",
    "Bodenaufbau": "BODENAUFBAU",
    "Konstruktion Dach": "KONSTRUKTION_DACH",
    "Dach Bekleidung": "DACH_BEKLEIDUNG",
    "Photovoltaik": "PHOTOVOLTAIK",
    "PV Fläche": "PV_FLAECHE",
    "Fenster": "FENSTER",
    "Fensteranzahl": "FENSTERANZAHL",
    "Dämmungsfläche": "DAEMMUNGSFLAECHE",
    "Stahl": "STAHL",
    "Stahl lm": "STAHL_LM",
    "Stahlblech": "STAHLBLECH",
    "Fläche 6": "STAHLBLECH_FLAECHE",
    "Eternit": "ETERNIT", 
    "Fläche 7": "ETERNIT_FLAECHE",
    "Steinplatten": "STEINPLATTEN",
    "Fläche 8": "STEINPLATTEN_FLAECHE",
    "Dachziegel": "DACHZIEGEL",
    "Fläche 9": "DACHZIEGEL_FLAECHE",
    "Beton": "BETON",
    "Fläche 10": "BETON_FLAECHE",
    "Holz": "HOLZ",
    "Holz lm": "HOLZ_LM",
    "Fläche 12": "HOLZ_FLAECHE",
    "Schadstoffen": "SCHADSTOFFEN",
}

# =========================
# HELPERS
# =========================
def _strip_obj(x: object) -> object:
    return x.strip() if isinstance(x, str) else x


def normalize_yes_no(x: object) -> object:
    if pd.isna(x):
        return pd.NA

    s = str(x).strip().lower()
    # if the value starts with "ja" or "nein but has no ? replace to JA NEIN
    for prefix in ["ja", "nein"]:
        if s.startswith(prefix) and not s.endswith("?" or "(?)"):
            return YESNO_VALUES.get(prefix, s)
    return YESNO_VALUES.get(s, s)


def normalize_label(x: object) -> object:
    if isinstance(x, str):
        s = x.strip()
        return LABEL_NORMALIZE.get(s, s)
    return x


def coerce_year(series: pd.Series) -> pd.Series:
    """Extract 4-digit year and convert to nullable Int64."""
    def to_year(v: object):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        if isinstance(v, (int)) and not pd.isna(v):
            y = int(v)
            return y if 1400 <= y <= 2100 else None
        if isinstance(v, str):
            m = re.search(r"(19\d{2}|20\d{2})", v)
            if m:
                y = int(m.group(1))
                return y if 1400 <= y <= 2100 else None
        return None

    return series.map(to_year).astype("Int64")


# =========================
# MAIN
# =========================
def main() -> None:
    print(f"Using Excel file: {INPUT_PATH}")

    df = pd.read_excel(
        INPUT_PATH,
        sheet_name=SHEET_NAME,
        header=HEADER_ROW_INDEX,
        dtype=object,
        engine="openpyxl",
    )

    # Limit to first 400 rows
    df = df.head(400)

    # Clean columns and values
    df.columns = [str(c).strip() for c in df.columns]
    df = df.map(_strip_obj)

    # Keep only the required columns that are present
    keep_cols = [c for c in REQUIRED_COLUMNS if c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        print(f"⚠️ Missing columns (will be ignored): {missing}")

    df_model= df[keep_cols].copy()

    # Drop fully empty rows
    df_model= df_model.dropna(how="all")

    for col in numeric_cols:
        if col in df_model.columns:
            df_model[col] = pd.to_numeric(df_model[col], errors="coerce").astype("Int64")

    # Normalize yes/no columns
    for col in YESNO_LIKE_COLS:
        if col in df_model.columns:
            df_model[col] = df_model[col].apply(normalize_yes_no)
            df_model[col] = df_model[col].where(df_model[col].isin(["JA", "NEIN"]))

    # Normalize all lables
    for col in df_model.columns:
        df_model[col] = df_model[col].apply(normalize_label)

    
    # convert KEIN to NA in all columns
    df_model= df_model.replace("KEIN", pd.NA)
    df_model= df_model.replace("KEINE", pd.NA)
    df_model= df_model.replace("nein", pd.NA)
    df_model= df_model.replace(0, pd.NA)
    df_model= df_model.replace("unklar", pd.NA)

    if df_model["HAUPTNUTZUNG"].str.contains("Industrie und Gerwerbe", case=False, na=False).any():
        df_model["HAUPTNUTZUNG"]. replace("Industrie und Gerwerbe", "Industrie und Gewerbe", inplace=True)
    
    if df_model["Fassade Dämmung"].str.contains("Mineraldämmung oder leichte Dämmelemnte", case=False, na=False).any():
        df_model["Fassade Dämmung"].replace("Mineraldämmung oder leichte Dämmelemnte", "Mineraldämmung oder leichte Dämmelemente", inplace=True)

    if df_model["Tragwerk Fassade6"].str.contains("Punktuel Beton mit Backsteinwände", case=False, na=False).any():
        df_model["Tragwerk Fassade6"].replace("Punktuel Beton mit Backsteinwände", "Punktuell Beton mit Backsteinwänden", inplace=True)
    if df_model["Tragwerk Fassade6"].str.contains("Zweischalenmauwerk, Backstein", case=False, na=False).any():
        df_model["Tragwerk Fassade6"].replace("Zweischalenmauwerk, Backstein", "Zweischalenmauerwerk, Backstein", inplace=True)


    if df_model["Bodenaufbau"].str.contains("Flachdach, ungedämmt", case=False, na=False).any():
        df_model["Bodenaufbau"].replace("Flachdach, ungedämmt", "Flachdach ungedämmt", inplace=True)
    
    if df_model["Konstruktion Dach"].str.contains("Tonnegewölbe, Holz?", case=False, na=False).any():
        df_model["Konstruktion Dach"].replace("Tonnegewölbe, Holz?", pd.NA, inplace=True)
    if df_model["Konstruktion Dach"].str.contains("FlachdachStahlkonstruktion", case=False, na=False).any():
        df_model["Konstruktion Dach"].replace("FlachdachStahlkonstruktion", "Flachdach Stahlkonstruktion", inplace=True)

    # Coerce years
    if "BAUJAHR" in df_model.columns:
        df_model["BAUJAHR"] = coerce_year(df_model["BAUJAHR"])

    if "Reale Baujahr" in df_model.columns:
        df_model["Reale Baujahr"] = coerce_year(df_model["Reale Baujahr"])

    # Prefer real year
    if "Reale Baujahr" in df_model.columns:
        df_model["BAUJAHR"] = df_model["Reale Baujahr"].fillna(df_model["BAUJAHR"])

    # Remove helper column
    df_model.drop(columns=["Reale Baujahr"], errors="ignore", inplace=True)

    # Deduplicate on EGID if present
    if "EGID" in df_model.columns:
        df_model= df_model.drop_duplicates(subset=["EGID"], keep="first")

    # Rename columns
    df_model = df_model.rename(columns=COLUMN_RENAME)

    # 👉 Nur erste 400 Zeilen verwenden
    df_subset = df_model.iloc[:400]

    # Kategorien filtern (auf Subset!)
    hoch = df_subset[df_subset["SCHADSTOFFEN"] == "HOHE_CHANCE"]
    niedrig = df_subset[df_subset["SCHADSTOFFEN"] == "NIEDRIGE_CHANCE"]
    nein = df_subset[df_subset["SCHADSTOFFEN"] == "NEIN"]

    # Sampling
    test_sample_df = pd.concat([
        hoch.sample(n=2, random_state=42),
        niedrig.sample(n=1, random_state=42),
        nein.sample(n=2, random_state=42),
    ])


    # Excel speichern
    test_sample_df.to_excel(
        TEST_DATASET_PATH,
        index=False
    )

    # Optional weiterhin als Liste nutzen
    test_rows = test_sample_df.to_dict(orient="records")

    # Aus Haupt-DF entfernen
    df_model = df_model.drop(test_sample_df.index)
    
    # Write output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_model.to_excel(OUTPUT_PATH, index=False)

    print(f"✅ Fertig: {len(df_model):,} Zeilen × {len(df_model.columns)} Spalten")
    print(f"📁 Gespeichert unter: {OUTPUT_PATH}")
    print("Spalten:", df_model.columns.tolist())
     
if __name__ == "__main__":
    main()