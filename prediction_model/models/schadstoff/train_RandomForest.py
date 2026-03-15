"""
to run:
python -m prediction_model.models.schadstoff.train_RandomForest
because we import log_experiment from doc_prediction_models, we need to run this as a module from the project root

"""

from __future__ import annotations
import os
from pathlib import Path
import joblib
import pandas as pd
from dotenv import load_dotenv
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from prediction_model.models.doc_prediction_models import log_experiment


# =========================
# Paths
# =========================
PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")

DATA_PATH = PROJECT_ROOT / os.getenv("OUTPUT_DATASET_PATH")
MODEL_PATH = PROJECT_ROOT / os.getenv("OUTPUT_MODEL_PATH")

df = pd.read_excel(DATA_PATH)

# =========================
# Prepare Data
# =========================
TARGET = "Schadstoffen"

# drop all except required columns + target
REQUIRED_COLUMNS = [
    "BAUJAHR",
    "TRAGWERK_FASSADE",
    "FASSADE_DAEMMUNG",
    "FASSADE_BEKLEIDUNG",
    "KONSTRUKTION_DACH",
    "DACH_BEKLEIDUNG",
    "PHOTOVOLTAIK",
    "FENSTER"
]


df = df[REQUIRED_COLUMNS + [TARGET]].copy()

# drop rows with missing target
df = df.dropna(subset=[TARGET]).copy()

X = df.drop(columns=[TARGET])
y = df[TARGET]

X_encoded = pd.get_dummies(X, drop_first=False)

# =========================
# Train/Test Split
# =========================
X_train_full, X_test, y_train_full, y_test = train_test_split(
    X_encoded,
    y,
    test_size=0.2,
    random_state=5,
    stratify=y
)

# =========================
# Cross-validation withoout saving folds
# =========================

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
rf_model = RandomForestClassifier(
    n_estimators=500,
    max_depth=None,
    class_weight="balanced",
    random_state=5,
    n_jobs=-1
)
cv_scores = cross_val_score(rf_model, X_train_full, y_train_full, cv=cv, scoring="f1_macro")
print(f"Cross-validation F1 scores: {cv_scores}")
print(f"Mean CV F1 score: {np.mean(cv_scores)}")

# Essembly of folds - RandomForest doesn't need this because it already does exactly that --IGNORE--

# =========================
# Train final model on full training data
# =========================
final_model = RandomForestClassifier(
    n_estimators=500,
    max_depth=None,
    class_weight="balanced",
    random_state=5,
    n_jobs=-1
)   

final_model.fit(X_train_full, y_train_full)

log_experiment(
    results={
        "model": "RandomForest",
        "target": TARGET,
        "description": "Finales Modell, trainiert auf dem gesamten Trainingsdatensatz, evaluiert auf dem Testset.",
        "features": list(X_train_full.columns),
        "Data points": len(X_train_full),
        "accuracy": final_model.score(X_test, y_test),
        "klassifikations_report": classification_report(y_test, final_model.predict(X_test), output_dict=True),
        "cv_f1_scores": [f"{score:.4f}" for score in cv_scores],
        "avg_f1_cv": np.mean(cv_scores),
        "std_f1_cv": np.std(cv_scores),
        "confusion_matrix": confusion_matrix(y_test, final_model.predict(X_test)).tolist()

    },
    filepath=PROJECT_ROOT / "prediction_model" / "models" / "doc_prediction_models.xlsx"
)

# =========================
# Evaluate on test set
# =========================

y_pred_test = final_model.predict(X_test)

print(classification_report(y_test, y_pred_test))

print("Confusion Matrix:")
print(confusion_matrix(y_test, y_pred_test))

# =========================
# Save the model
# =========================
model_save_path = MODEL_PATH / "random_forest_model.pkl"
model_save_path.parent.mkdir(parents=True, exist_ok=True)

joblib.dump(final_model, model_save_path)   