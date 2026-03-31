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


def load_combined_model(model_dir):
    return CombinedFoldEnsemble(model_dir=model_dir)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

DATA_PATH = PROJECT_ROOT / os.getenv("OUTPUT_DATASET_PATH")
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

    for _, row in df.iloc[25:30].iterrows():
        X_new = pd.DataFrame([row])
        missing_value = pd.isna(row[target_col])

        try:
            pred = combined_model.predict(X_new=X_new)
            pred_value = pred["prediction"]

            results.append({
                "EGID": row["EGID"],
                "model_name": model_name,
                "target_col": target_col,
                "ground_truth": row[target_col],
                "prediction": pred_value,
                "correct": (row[target_col] == pred_value) if not missing_value else None,
                "missing_value": missing_value,
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
                "missing_value": missing_value,
                "error": str(e),
            })

results_df = pd.DataFrame(results)

# Nur Zeilen mit vorhandener Ground Truth und ohne Fehler für Metriken verwenden
eval_df = results_df[
    (~results_df["missing_value"]) &
    (results_df["error"].isna())
]

summary_df = eval_df.groupby("model_name")["correct"].mean().sort_values(ascending=False)
print(summary_df)

print(results_df.head())

results_df.to_csv(PROJECT_ROOT / "prediction_model/models/error_analysis_results.csv", index=False)

missing_summary = (
    results_df.groupby("model_name")["missing_value"]
    .sum()
    .reset_index(name="missing_value_count")
)
print(missing_summary)

errors_df = results_df[
    (results_df["correct"] == False) | (results_df["error"].notna())
]

error_cols = ["EGID", "model_name", "target_col", "ground_truth", "prediction", "correct", "missing_value", "error"]
input_cols = [col for col in df.columns if col != "EGID"]

errors_with_inputs_df = errors_df.merge(df, on="EGID", how="left")
errors_with_inputs_df = errors_with_inputs_df[error_cols + input_cols]

print(errors_with_inputs_df.head(20))

errors_with_inputs_df.to_csv(PROJECT_ROOT / "prediction_model/models/incorrect_predictions.csv", index=False)