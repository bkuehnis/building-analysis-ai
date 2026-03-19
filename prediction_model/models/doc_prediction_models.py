import pandas as pd
from pathlib import Path
from datetime import datetime

EXCEL_LOG_PATH = Path(__file__).resolve().parents[1] / "doc_prediction_models.xlsx"

def log_experiment(results: dict, filepath):

    row = {}
    row["Date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row["model"] = results.get("model")
    row["description"] = results.get("description")
    row["target"] = results.get("target")
    row["features"] = results.get("features")
    for i in range(1, 11):
        row[f"important_feature_{i}"] = results.get("importance", [{}])[i-1].get("feature") if len(results.get("importance", [])) >= i else None
        row[f"importance_{i}"] = results.get("importance", [{}])[i-1].get("importance") if len(results.get("importance", [])) >= i else None
    if results.get("data_points_train") is not None:
        row["data_points_train"] = results.get("data_points_train")
    if results.get("data_points_val") is not None:
        row["data_points_val"] = results.get("data_points_val")
    if results.get("data_points_test") is not None:
        row["data_points_test"] = results.get("data_points_test")
    if results.get("accuracy") is not None:
        row["accuracy"] = f"{results.get('accuracy'):.4f}"
    klass_report = results.get("klassifikations_report")
    if klass_report is not None:
        row["precision"] = f"{klass_report.get('weighted avg', {}).get('precision'):.4f}"
        row["recall"] = f"{klass_report.get('weighted avg', {}).get('recall'):.4f}"
        row["f1"] = f"{klass_report.get('weighted avg', {}).get('f1-score'):.4f}"
    if results.get("avg_f1_cv") is not None:
        row["avg_f1_cv"] = f"{results.get('avg_f1_cv'):.4f}"
    if results.get("std_f1_cv") is not None:
        row["std_f1_cv"] = f"{results.get('std_f1_cv'):.4f}"
    if results.get("confusion_matrix") is not None:
        row["confusion_matrix"] = results.get("confusion_matrix")

    df_new = pd.DataFrame([row])

    if filepath.exists():
        df_existing = pd.read_excel(filepath)
        df_all = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_all = df_new

    df_all.to_excel(filepath, index=False)



    