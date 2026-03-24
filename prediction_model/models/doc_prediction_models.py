import pandas as pd
from pathlib import Path
from datetime import datetime

EXCEL_LOG_PATH = Path(__file__).resolve().parents[1] / "doc_prediction_models_new.xlsx"

def log_experiment(results: dict, filepath):

    row = {}
    row["Date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row["model"] = results.get("model")
    row["description"] = results.get("description")
    row["target"] = results.get("target")
    row["features"] = results.get("features")

    for i in range(1, 11):
        row[f"important_feature_{i}"] = (
            results.get("importance", [{}])[i - 1].get("feature")
            if len(results.get("importance", [])) >= i else None
        )
        row[f"importance_{i}"] = (
            results.get("importance", [{}])[i - 1].get("importance")
            if len(results.get("importance", [])) >= i else None
        )
    if results.get("data_points_train") is not None:
        row["data_points_train"] = results.get("data_points_train")
    if results.get("data_points_val") is not None:
        row["data_points_val"] = results.get("data_points_val")
    if results.get("data_points_total") is not None:
        row["data_points_total"] = results.get("data_points_total")
    klass_report = results.get("klassifikations_report")
    if klass_report is not None:
        for key in ["precision", "recall", "f1-score"]:
            weighted_val = klass_report.get("weighted avg", {}).get(key)
            macro_val = klass_report.get("macro avg", {}).get(key)

            row[f"{key}_weighted_avg"] = f"{weighted_val:.4f}" if weighted_val is not None else None
            row[f"{key}_macro_avg"] = f"{macro_val:.4f}" if macro_val is not None else None

        acc = klass_report.get("accuracy")
        row["accuracy"] = f"{acc:.4f}" if acc is not None else None

    if results.get("avg_f1_cv") is not None:
        row["avg_f1_cv"] = f"{results.get('avg_f1_cv'):.4f}"
    if results.get("std_f1_cv") is not None:
        row["std_f1_cv"] = f"{results.get('std_f1_cv'):.4f}"
    if results.get("confusion_matrix") is not None:
        row["confusion_matrix"] = results.get("confusion_matrix")

    df_new = pd.DataFrame([row])

    if filepath.exists():
        df_existing = pd.read_excel(filepath)

        # Drop completely empty columns (future-proof)
        df_existing = df_existing.dropna(axis=1, how="all")
        df_new_clean = df_new.dropna(axis=1, how="all")

        # Only concat non-empty DataFrames
        dfs = []
        if not df_existing.empty:
            dfs.append(df_existing)
        if not df_new_clean.empty:
            dfs.append(df_new_clean)

        df_all = pd.concat(dfs, ignore_index=True)

    else:
        df_all = df_new
        
    df_all.to_excel(filepath, index=False)



    