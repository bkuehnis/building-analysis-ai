"""
to run:
python -m prediction_model.models.model_error_analysis
"""
from __future__ import annotations
import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

from prediction_model.services.combined_prediction_service import CombinedFoldEnsemble
from prediction_model.services.combined_prediction_service import (
    FEATURE_COLUMNS_FASSADEN_BEKLEIDUNG,
    FEATURE_COLUMNS_DACH_BEKLEIDUNG,
    FEATURE_COLUMNS_KONSTRUKTION_DACH,
    FEATURE_COLUMNS_TRAGWERK_FASSADE,
    FEATURE_COLUMNS_FASSADEN_DAEMMUNG,
    FEATURE_COLUMNS_FENSTER,
    FEATURE_COLUMNS_BODENAUFBAU,
    FEATURE_COLUMNS_KONSTRUKTION_DECKE,
    FEATURE_COLUMNS_SCHADSTOFFE,
)


def load_combined_model(model_dir):
    return CombinedFoldEnsemble(model_dir=model_dir)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

DATA_PATH = PROJECT_ROOT / os.getenv("TEST_DATASET")
df = pd.read_excel(DATA_PATH)

model_configs = [
    ("prediction_model/models/fassade_bekleidung/saved_models", "Fassade Bekleidung", "FASSADE_BEKLEIDUNG"),
    ("prediction_model/models/dach_bekleidung/saved_models", "Dach Bekleidung", "DACH_BEKLEIDUNG"),
    ("prediction_model/models/konstruktion_dach/saved_models", "Konstruktion Dach", "KONSTRUKTION_DACH"),
    ("prediction_model/models/tragwerk_fassade/saved_models", "Tragwerk Fassade", "TRAGWERK_FASSADE"),
    ("prediction_model/models/fassade_daemmung/saved_models", "Fassade Dämmung", "FASSADE_DAEMMUNG"),
    ("prediction_model/models/fenster/saved_models", "Fenster", "FENSTER"),
    ("prediction_model/models/bodenaufbau/saved_models", "Bodenaufbau", "BODENAUFBAU"),
    ("prediction_model/models/konstruktion_decke/saved_models", "Konstruktion Decke", "KONSTRUKTION_DECKE"),
    ("prediction_model/models/schadstoff/saved_models", "Schadstoffe", "SCHADSTOFFEN"),
]

results = []

for model_dir, model_name, target_col in model_configs:
    print(f"Running model: {model_name}")
    combined_model = load_combined_model(model_dir)

    # --> ground truth test examples: 5
    for _, row in df.iterrows():
        X_new = pd.DataFrame([row])
        missing_target_value = pd.isna(row[target_col])


        try:
            pred = combined_model.predict(X_new=X_new)
            pred_value = pred["prediction"]

            if isinstance(pred_value, (list, tuple)):
                pred_value = pred_value[0]
            elif hasattr(pred_value, "shape"):
                pred_value = pred_value[0]
            elif hasattr(pred_value, "__len__") and not isinstance(pred_value, str):
                pred_value = pred_value[0]

            missing_target_value = pd.isna(row[target_col])

            results.append({
                "EGID": row["EGID"],
                "model_name": model_name,
                "target_col": target_col,
                "ground_truth": row[target_col],
                "prediction": pred_value,
                "correct": (row[target_col] == pred_value) if not missing_target_value else None,
                "missing_target_value": missing_target_value,
                "error": None,
            })

        except Exception as e:
            results.append({
                "EGID": row["EGID"],
                "model_name": model_name,
                "target_col": target_col,
                "ground_truth": row[target_col],
                "prediction": None,
                "correct": None,
                "missing_target_value": missing_target_value,
                "error": str(e),
            })

results_df = pd.DataFrame(results)

error_cols = [
    "EGID", "model_name", "target_col", "ground_truth",
    "prediction", "correct", "missing_target_value", "error"
]

eval_df = results_df[
    (~results_df["missing_target_value"]) &
    (results_df["error"].isna())
].copy()

eval_df["correct"] = eval_df["correct"].astype(bool)

summary_df = eval_df.groupby("model_name")["correct"].mean().sort_values(ascending=False)
print(summary_df)


print(results_df.head())

if not (PROJECT_ROOT / "prediction_model/models/1_error_analysis").exists():
    (PROJECT_ROOT / "prediction_model/models/1_error_analysis").mkdir(parents=True)
#results_df.to_csv(PROJECT_ROOT / "prediction_model/models/1_error_analysis/error_analysis_results.csv", index=False)

# Technische Fehler
technical_errors_df = results_df[
    results_df["error"].notna()
]

technical_errors_with_inputs_df = technical_errors_df.merge(df, on="EGID", how="left")
technical_errors_with_inputs_df.to_csv(
    PROJECT_ROOT / "prediction_model/models/1_error_analysis/technical_errors.csv",
    index=False
)

# Fehlende Ground Truth
missing_summary = (
    results_df.groupby("model_name")["missing_target_value"]
    .sum()
    .reset_index(name="missing_value_count")
)
print(missing_summary)

missing_target_df = results_df[
    results_df["missing_target_value"] == True
]

missing_target_with_inputs_df = missing_target_df.merge(df, on="EGID", how="left")
missing_target_with_inputs_df.to_csv(
    PROJECT_ROOT / "prediction_model/models/1_error_analysis/missing_target_predictions.csv",
    index=False
)

# Falsche Predictions
incorrect_df = results_df[
    results_df["correct"] == False
]

incorrect_with_inputs_df = incorrect_df.merge(df, on="EGID", how="left")

model_feature_map = {
    "Fassade Bekleidung": FEATURE_COLUMNS_FASSADEN_BEKLEIDUNG,
    "Dach Bekleidung": FEATURE_COLUMNS_DACH_BEKLEIDUNG,
    "Konstruktion Dach": FEATURE_COLUMNS_KONSTRUKTION_DACH,
    "Tragwerk Fassade": FEATURE_COLUMNS_TRAGWERK_FASSADE,
    "Fassade Dämmung": FEATURE_COLUMNS_FASSADEN_DAEMMUNG,
    "Fenster": FEATURE_COLUMNS_FENSTER,
    "Bodenaufbau": FEATURE_COLUMNS_BODENAUFBAU,
    "Konstruktion Decke": FEATURE_COLUMNS_KONSTRUKTION_DECKE,
    "Schadstoffe": FEATURE_COLUMNS_SCHADSTOFFE,
}

output_dir = PROJECT_ROOT / "prediction_model/models/1_error_analysis/incorrect_predictions"
output_dir.mkdir(parents=True, exist_ok=True)

for model_name, feature_cols in model_feature_map.items():
    subset_df = incorrect_with_inputs_df[
        incorrect_with_inputs_df["model_name"] == model_name
    ][error_cols + feature_cols].copy()

    if not subset_df.empty:
        file_name = model_name.lower().replace(" ", "_").replace("ä", "ae") + "_errors.csv"
        subset_df.to_csv(output_dir / file_name, index=False)