"""
scripts/generate_model_dataset.py

Creates a clean Excel dataset for the Schadstoff (hazardous substances risk) model.

Assumptions (based on your last message):
- The actual table header starts in Excel row 9 (1-based)
  -> pandas header index = 8 (0-based)
- We extract ONLY these columns (if present) and all rows below:
  EGID, GSW_STATUS, BAUJAHR, Reale Baujahr, Schadstoffen,
  Tragwerk Fassade6, Fassade Dämmung, Fassade Bekleidung,
  Konstruktion Decke, Konstruktion Dach, Dach Bekleidung,
  Eternit, Holz, Holz Lm, Extra

- Input path is taken from .env:
  EXCEL_FILE_PATH=data/buildings/Gebaeudescreening_winti.xlsx

- Output path is taken from .env:
  OUTPUT_DATASET_PATH=data/processed/schadstoff_dataset.xlsx

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

EXCEL_FILE_PATH = os.getenv("EXCEL_FILE_PATH")
OUTPUT_DATASET_PATH = os.getenv("OUTPUT_DATASET_PATH")

if not EXCEL_FILE_PATH:
    raise ValueError("EXCEL_FILE_PATH missing in .env")
if not OUTPUT_DATASET_PATH:
    raise ValueError("OUTPUT_DATASET_PATH missing in .env")

INPUT_PATH = (PROJECT_ROOT / EXCEL_FILE_PATH).resolve()
OUTPUT_PATH = (PROJECT_ROOT / OUTPUT_DATASET_PATH).resolve()

if not INPUT_PATH.exists():
    raise FileNotFoundError(f"Excel not found: {INPUT_PATH}")

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

NUMMERIC_COLUMNS = [
    "BAUJAHR",
    "Reale Baujahr",
    "PV Fläche",
    "Fensteranzahl",
    "Dämmungsfläche",
    "Stahl Lm",
    "Fläche 6",
    "Fläche 7",
    "Fläche 8",
    "Fläche 9",
    "Fläche 10",
    "Holz Lm",
    "Fläche 12"
]

# Optional: normalize label values for the target column
LABEL_NORMALIZE = {
    "Ja": "JA",
    "Nein": "NEIN",
    "Hohe Chance": "HOHE_CHANCE",
    "Niedrige Chance": "NIEDRIGE_CHANCE",
    "Niedrig Chance": "NIEDRIGE_CHANCE",
    "h.W. Asbest, PCB, PAK": "HW_ASBEST_PCB_PAK",
    "h. W. Asbest, PCB, PAK": "HW_ASBEST_PCB_PAK",
    "h.W. Holzschutzmittel": "HW_HOLZSCHUTZMITTEL",
    "h. W. Holzschutzmittel": "HW_HOLZSCHUTZMITTEL",
}

YESNO_VALUES = {
    "ja": "JA",
    "j": "JA",
    "yes": "JA",
    "true": "JA",
    "1": "JA",
    "nein": "NEIN",
    "n": "NEIN",
    "no": "NEIN",
    "false": "NEIN",
    "0": "NEIN",
}

YESNO_LIKE_COLS = {"Eternit", "Holz","Stahl", "Stahlblech", "Beton", "Steinplatten"}  # extend if needed

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
    "Fläche 12": "HOLZ_FLAECHE"
}



# =========================
# HELPERS
# =========================
def _strip_obj(x: object) -> object:
    return x.strip() if isinstance(x, str) else x


def normalize_yes_no(x: object) -> object:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return pd.NA

    s = str(x).strip().lower()

    # exakter match zuerst
    if s in YESNO_VALUES:
        return YESNO_VALUES[s]

    # dann Wortsuche (z.B. "ja (glasdach)")
    if re.search(r"\bja\b", s):
        return "JA"
    if re.search(r"\bnein\b", s):
        return "NEIN"

    return pd.NA


def normalize_label(x: object) -> object:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return pd.NA
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


    # Clean columns and values
    df.columns = [str(c).strip() for c in df.columns]
    df = df.map(_strip_obj)

    # Keep only the required columns that are present
    keep_cols = [c for c in REQUIRED_COLUMNS if c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        print(f"⚠️ Missing columns (will be ignored): {missing}")

    out = df[keep_cols].copy()

    # Drop fully empty rows
    out = out.dropna(how="all")

    # Normalize columns
    if "Schadstoffen" in out.columns:
        out["Schadstoffen"] = out["Schadstoffen"].map(normalize_label)

    for c in YESNO_LIKE_COLS:
        if c in out.columns:
            out[c] = out[c].map(normalize_yes_no)

    # Coerce years
    if "BAUJAHR" in out.columns:
        out["BAUJAHR"] = coerce_year(out["BAUJAHR"])
    if "Reale Baujahr" in out.columns:
        out["Reale Baujahr"] = coerce_year(out["Reale Baujahr"])

    # Create an "effective year" column (prefer Reale Baujahr if present)
    if "BAUJAHR" in out.columns and "Reale Baujahr" in out.columns:
        out["Baujahr_effektiv"] = out["Reale Baujahr"].fillna(out["BAUJAHR"])
    elif "Reale Baujahr" in out.columns:
        out["Baujahr_effektiv"] = out["Reale Baujahr"]
    elif "BAUJAHR" in out.columns:
        out["Baujahr_effektiv"] = out["BAUJAHR"]


    # Überschreibe BAUJAHR mit dem effektiven Jahr
    out["BAUJAHR"] = out["Baujahr_effektiv"]

    # Entferne alte Spalten
    drop_cols = []
    if "Reale Baujahr" in out.columns:
        drop_cols.append("Reale Baujahr")
    if "Baujahr_effektiv" in out.columns:
        drop_cols.append("Baujahr_effektiv")

    out = out.drop(columns=drop_cols, errors="ignore")

    # Numerische Spalten sauber konvertieren
    numeric_cols = [
        "EGID",
        "BAUJAHR",
        "PV Fläche",
        "Fensteranzahl",
        "Dämmungsfläche",
        "Stahl lm",
        "Fläche",
        "Fläche 7",
        "Fläche 8",
        "Fläche 9",
        "Holz lm",
        "Fläche 11",
    ]

    for col in numeric_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")

    # Remove rows without target label
    out = out[~out["Schadstoffen"].isna()].copy()

    # Deduplicate on EGID if present
    if "EGID" in out.columns:
        out = out.drop_duplicates(subset=["EGID"], keep="first")

    # Rename columns to match collected building data
    out = out.rename(columns=COLUMN_RENAME)

    # Write output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_excel(OUTPUT_PATH, index=False)

    print(f"✅ Fertig: {len(out):,} Zeilen × {len(out.columns)} Spalten")
    print(f"📁 Gespeichert unter: {OUTPUT_PATH}")
    print("Spalten:", out.columns.tolist())
    
if __name__ == "__main__":
    main()