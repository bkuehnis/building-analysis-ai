from collections import defaultdict, Counter
import pandas as pd
from itertools import combinations
import os
from pathlib import Path
from dotenv import load_dotenv

"""
run:
python -m scripts.model_dataset_analysis
"""

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

#input dataset has path defined in .env file as OUTPUT_DATASET_PATH
INPUT_DATASET = os.getenv("OUTPUT_DATASET_PATH")  

# Constants for reading the dataset
SHEET_NAME = "Sheet1"  # Set to your actual sheet name
HEADER_ROW_INDEX = 0  # Set to your actual header row index

def analyze_dataset(dataset_path):
    # Read the dataset
    df = pd.read_excel(dataset_path, sheet_name=SHEET_NAME, header=HEADER_ROW_INDEX)
    
    #for every atribute show the most common values and their names
    for column in df.columns:
        print(f"Column: {column}")
        print(df[column].value_counts().head(5))  # Show top 5 most common values
        print("\n")
    # Analyze combinations of attributes
    combo_counter = Counter()
    for _, row in df.iterrows():
        # Create a tuple of the attribute values for the current row, filling NaN values with "N/A"
        combo = tuple(row.fillna("N/A"))
        combo_counter[combo] += 1
    combo_df = pd.DataFrame(combo_counter.items(), columns=['Combination', 'Count'])

    return combo_df

def get_combinations(df, cols):
    return (
        df[cols]
        .fillna("NaN")
        .groupby(cols, as_index=False)
        .size()
        .rename(columns={"size": "Count"})
        .sort_values(by=cols[0], ascending=False)
    )

if __name__ == "__main__":

    dataset_path = os.path.join(INPUT_DATASET)
    df = pd.read_excel(dataset_path, sheet_name=SHEET_NAME, header=HEADER_ROW_INDEX)
    
    # remove 'EGID' column for analysis
    if "EGID" in df.columns:
        df = df.drop(columns=['EGID'])

    df["BAUJAHR_GRUPPE"] = df["BAUJAHR"].apply(
    lambda x: "vor_1990" if x <= 1990 else "nach_1990"
    )

    df["BAUPERIODE_PERIOD"] = df["BAUJAHR"].apply(
    lambda x: "vor_1900" if x < 1900 else ("1901-1950" if x <= 1950 else  ("1951-1990" if x <= 1990 else "nach_1990"))
)
    # To DO: analyse and remove unnecessary combinations with no real value
    analysen = {
        # baujahr analysieren
        "baujahr_gr": ["BAUJAHR_GRUPPE"],
        "baujahr_p": ["BAUPERIODE_PERIOD"],

        "baujahr_fassade_schad": ["BAUPERIODE_PERIOD", "FASSADE_BEKLEIDUNG", "SCHADSTOFFEN"],
        "baujahr_fenster_schad": ["BAUPERIODE_PERIOD", "FENSTER", "SCHADSTOFFEN"],

        # schadstoffen analysieren
        "schad_Baujahr_gr": ["SCHADSTOFFEN", "BAUJAHR_GRUPPE"],
        "schad_Baujahr_p": ["SCHADSTOFFEN", "BAUPERIODE_PERIOD"],
        "schad_fassaden_bekleidung": ["SCHADSTOFFEN", "FASSADE_BEKLEIDUNG"],
        "schad_fassaden_daemmung": ["SCHADSTOFFEN", "FASSADE_DAEMMUNG"],
        "schad_dach_bekleidung": ["SCHADSTOFFEN", "DACH_BEKLEIDUNG"],
        "schad_dach_konstruktion": ["SCHADSTOFFEN", "KONSTRUKTION_DACH"],
        "schad_fenster": ["SCHADSTOFFEN", "FENSTER"],
        "schadstoffen_eterni": ["SCHADSTOFFEN", "ETERNIT"],


        # fassaden analysieren tragwerk
        "fassaden_Baujahr_gr": ["TRAGWERK_FASSADE", "BAUJAHR_GRUPPE"],
        "fassaden_Baujahr_p": ["TRAGWERK_FASSADE", "BAUPERIODE_PERIOD"],
        #"fassade_holz": ["TRAGWERK_FASSADE", "HOLZ"],
        "fassade_stahl": ["TRAGWERK_FASSADE", "STAHL"],
        "fassade_blech": ["TRAGWERK_FASSADE", "STAHLBLECH"],
        #"fassade_beton": ["TRAGWERK_FASSADE", "BETON"],
        "fassade_hauptnutzung": ["TRAGWERK_FASSADE", "HAUPTNUTZUNG"],
        "fassade_Nutzung": ["TRAGWERK_FASSADE", "NUTZUNG"],

        # fassaden analysieren dämmung
        "fassaden_tragwerk_daemmung": ["TRAGWERK_FASSADE", "FASSADE_DAEMMUNG"],
        # tragwerk, dämmung und baujahr sind evt. stark abhängig -> gute erkenntnisse
        "fassaden_tragwerk_daemmung_j_gr": ["TRAGWERK_FASSADE", "FASSADE_DAEMMUNG", "BAUJAHR_GRUPPE"],
        "fassaden_daemmung_j_gr": ["FASSADE_DAEMMUNG", "BAUJAHR_GRUPPE"],
        #"fassaden_daemmung_bekleidung": ["FASSADE_DAEMMUNG", "FASSADE_BEKLEIDUNG"],
        "fassaden_daemmung_dach_b": ["FASSADE_DAEMMUNG", "DACH_BEKLEIDUNG"],
        "fassaden_daemmung_dach_k": ["FASSADE_DAEMMUNG", "KONSTRUKTION_DACH"],
        "fassaden_daemmung_fenster": ["FASSADE_DAEMMUNG", "FENSTER"],
        "fassaden_daemmung_boden": ["FASSADE_DAEMMUNG", "BODENAUFBAU"],
        "fassaden_daemmung_hauptnutzung": ["FASSADE_DAEMMUNG", "HAUPTNUTZUNG"],


        # fassaden analysieren bekleidung
        "fassaden_bekleidung_j_gr": ["FASSADE_BEKLEIDUNG", "BAUJAHR_GRUPPE"],
        "fassaden_bekleidung_j_p": ["FASSADE_BEKLEIDUNG", "BAUPERIODE_PERIOD"],
        #"fassaden_bekleidung_holz": ["FASSADE_BEKLEIDUNG", "HOLZ"],
        #"fassaden_bekleidung_stahl": ["FASSADE_BEKLEIDUNG", "STAHL"],
        #"fassaden_bekleidung_beton": ["FASSADE_BEKLEIDUNG", "BETON"],
        #"fassaden_bekleidung_blech": ["FASSADE_BEKLEIDUNG", "STAHLBLECH"],

        # dach analysieren konstruktion
        "dach_Baujahr_gr": ["KONSTRUKTION_DACH", "BAUJAHR_GRUPPE"],
        "dach_Baujahr_p": ["KONSTRUKTION_DACH", "BAUPERIODE_PERIOD"],
        "dach_konstruktion_bekleidung": ["KONSTRUKTION_DACH", "DACH_BEKLEIDUNG"],
        #"dach_konstruktion_tragwerk": ["KONSTRUKTION_DACH", "TRAGWERK_FASSADE"],
        "dach_konstruktion_holz": ["KONSTRUKTION_DACH", "HOLZ"],
        #"dach_konstruktion_stahl": ["KONSTRUKTION_DACH", "STAHL"],

        # dach analysieren bekleidung
        "dach_Baujahr_gr_bekleidung": ["DACH_BEKLEIDUNG", "BAUJAHR_GRUPPE"],
        "dach_Baujahr_p_bekleidung": ["DACH_BEKLEIDUNG", "BAUPERIODE_PERIOD"],
        #"dach_bekleidung_holz": ["DACH_BEKLEIDUNG", "HOLZ"],
        #"dach_bekleidung_stahl": ["DACH_BEKLEIDUNG", "STAHL"],
        #"dach_bekleidung_beton": ["DACH_BEKLEIDUNG", "BETON"],
        #"dach_bekleidung_blech": ["DACH_BEKLEIDUNG", "STAHLBLECH"],


        # konstruktion decke
        "decke_Baujahr_gr": ["KONSTRUKTION_DECKE", "BAUJAHR_GRUPPE"],
        "decke_Baujahr_p": ["KONSTRUKTION_DECKE", "BAUPERIODE_PERIOD"],
        #"decke_konstruktion_holz": ["KONSTRUKTION_DECKE", "HOLZ"],
        #"decke_konstruktion_stahl": ["KONSTRUKTION_DECKE", "STAHL"],
        #"decke_konstruktion_beton": ["KONSTRUKTION_DECKE", "BETON"],
        #"decke_konstruktion_blech": ["KONSTRUKTION_DECKE", "STAHLBLECH"],

        #bodenaufbau analysieren
        "boden_Baujahr_gr": ["BODENAUFBAU", "BAUJAHR_GRUPPE"],
        "boden_Baujahr_p": ["BODENAUFBAU", "BAUPERIODE_PERIOD"],
        "boden_tragwerk_fassade": ["BODENAUFBAU", "TRAGWERK_FASSADE"],
        "boden_aufb_daemmung": ["BODENAUFBAU", "FASSADE_DAEMMUNG"],
        "boden_aufb_bekleidung": ["BODENAUFBAU", "FASSADE_BEKLEIDUNG"],
        "boden_aufb_fenster": ["BODENAUFBAU", "FENSTER"],

        # fenster analysieren
        "fenster_Baujahr_gr": ["FENSTER", "BAUJAHR_GRUPPE"],
        "fenster_Baujahr_p": ["FENSTER", "BAUPERIODE_PERIOD"],
        "fenster_tragwerk_fassade": ["FENSTER", "TRAGWERK_FASSADE"],
        "fenster_daemmung": ["FENSTER", "FASSADE_DAEMMUNG"],

    
    }

    results = {}

    for name, cols in analysen.items():
        results[name] = get_combinations(df, cols)


    #a = analyze_dataset(dataset_path)
    #print(a.head(10))

    #save the combination analysis to a new Excel file
    output_path = os.path.join(PROJECT_ROOT / "prediction_model", "var_combinations.xlsx")
    
    with pd.ExcelWriter(output_path) as writer:
        for name, combo_df in results.items():

            combo_df.to_excel(writer, sheet_name=name, index=False)
    print(f"Combination analysis saved to {output_path}")