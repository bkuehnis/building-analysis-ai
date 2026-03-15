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
    row["Data points"] = results.get("Data points")
    row["accuracy"] = f"{results.get('accuracy'):.4f}"
    klass_report = results.get("klassifikations_report")
    if klass_report is not None:
        row["precision"] = f"{klass_report.get('weighted avg', {}).get('precision'):.4f}"
        row["recall"] = f"{klass_report.get('weighted avg', {}).get('recall'):.4f}"
        row["f1"] = f"{klass_report.get('weighted avg', {}).get('f1-score'):.4f}"
    row["cv_f1_scores"] = f"{results.get('cv_f1_scores')}"
    row["avg_f1_cv"] = f"{results.get('avg_f1_cv'):.4f}"
    row["std_f1_cv"] = f"{results.get('std_f1_cv'):.4f}"
    row["confusion_matrix"] = results.get("confusion_matrix")  

    df_new = pd.DataFrame([row])

    if filepath.exists():
        df_existing = pd.read_excel(filepath)
        df_all = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_all = df_new

    df_all.to_excel(filepath, index=False)



    