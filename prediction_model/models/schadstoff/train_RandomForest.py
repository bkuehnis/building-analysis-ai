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
# K-Fold training for RF ensemble
# =========================
N_SPLITS = 5
SEED = 5
DESCRIPTION = "NEW: "

skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)

f1_scores = []
fold_models = []
fold_infos = []

for fold, (train_idx, val_idx) in enumerate(skf.split(X_train_full, y_train_full), start=1):
    X_train_fold = X_train_full.iloc[train_idx]
    y_train_fold = y_train_full.iloc[train_idx]
    X_val_fold = X_train_full.iloc[val_idx]
    y_val_fold = y_train_full.iloc[val_idx]

    model = RandomForestClassifier(
        n_estimators=500,
        max_depth=None,
        class_weight="balanced",
        random_state=SEED,
        n_jobs=-1
    )

    model.fit(X_train_fold, y_train_fold)

    y_pred_val = model.predict(X_val_fold)
    fold_f1 = f1_score(y_val_fold, y_pred_val, average="weighted")

    f1_scores.append(fold_f1)
    fold_models.append(model)
    fold_infos.append({
        "fold": fold,
        "train_size": len(X_train_fold),
        "val_size": len(X_val_fold),
        "y_val_true": y_val_fold.copy(),
        "y_val_pred": y_pred_val.copy()
    })

    model_save_path = MODEL_PATH / "folds" / f"randomforest_fold_{fold}.pkl"
    model_save_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_save_path)

    print(f"Fold {fold}: F1 = {fold_f1:.4f}")

avg_f1_cv = np.mean(f1_scores)
std_f1_cv = np.std(f1_scores)

print(f"\nMean CV F1: {avg_f1_cv:.4f}")
print(f"Std CV F1: {std_f1_cv:.4f}")

# =========================
# Log each fold
# =========================
for model, info, fold_f1 in zip(fold_models, fold_infos, f1_scores):
    feature_importance_df = pd.DataFrame({
        "feature": X_train_full.columns,
        "importance": model.feature_importances_
    }).sort_values(by="importance", ascending=False)

    log_experiment(
        results={
            "model": f"RandomForest Fold {info['fold']}",
            "target": TARGET,
            "data_points_train": info["train_size"],
            "data_points_val": info["val_size"],
            "data_points_test": len(X_test),
            "description": f"Fold {info['fold']} aus {N_SPLITS}-Fold CV.",
            "features": ", ".join(X_train_full.columns),
            "importance": [
                {"feature": row["feature"], "importance": row["importance"]}
                for _, row in feature_importance_df.iterrows()
            ],
            "f1_cv": fold_f1,
            "confusion_matrix": confusion_matrix(info["y_val_true"], info["y_val_pred"]).tolist()
        },
        filepath=PROJECT_ROOT / "prediction_model" / "models" / "doc_prediction_models.xlsx"
    )

# =========================
# Ensemble prediction on test set
# =========================
y_test_array = np.array(y_test).flatten()

probas = [model.predict_proba(X_test) for model in fold_models]
mean_proba = np.mean(probas, axis=0)

class_labels = fold_models[0].classes_
ensemble_preds = class_labels[np.argmax(mean_proba, axis=1)]

ensemble_f1_test = f1_score(y_test_array, ensemble_preds, average="weighted")
ensemble_accuracy = np.mean(ensemble_preds == y_test_array)

print("\nRF Ensemble Classification Report:\n")
print(classification_report(y_test_array, ensemble_preds))
print("Confusion Matrix RF Ensemble:\n")
print(confusion_matrix(y_test_array, ensemble_preds))
print(f"RF Ensemble F1 on test set: {ensemble_f1_test:.4f}")

feature_importance_df_ensemble = pd.DataFrame({
    "feature": X_train_full.columns,
    "importance": np.mean([model.feature_importances_ for model in fold_models], axis=0)
}).sort_values(by="importance", ascending=False)

log_experiment(
    results={
        "model": "RandomForest Ensemble",
        "target": TARGET,
        "data_points_train": len(X_train_full),
        "data_points_test": len(X_test),
        "description": f"Ensemble aus {N_SPLITS} RandomForest-Folds, evaluiert auf Testset. {DESCRIPTION}",
        "features": ", ".join(X_train_full.columns),
        "importance": [
            {"feature": row["feature"], "importance": row["importance"]}
            for _, row in feature_importance_df_ensemble.iterrows()
        ],
        "accuracy": ensemble_accuracy,
        "klassifikations_report": classification_report(y_test_array, ensemble_preds, output_dict=True),
        "avg_f1_cv": avg_f1_cv,
        "std_f1_cv": std_f1_cv,
        "f1_test": ensemble_f1_test,
        "confusion_matrix": confusion_matrix(y_test_array, ensemble_preds).tolist()
    },
    filepath=PROJECT_ROOT / "prediction_model" / "models" / "doc_prediction_models.xlsx"
)

# =========================
# Train final model on full training data
# =========================
final_model = RandomForestClassifier(
    n_estimators=500,
    max_depth=None,
    class_weight="balanced",
    random_state=SEED,
    n_jobs=-1
)

final_model.fit(X_train_full, y_train_full)

y_pred_test = final_model.predict(X_test)
final_f1_test = f1_score(y_test, y_pred_test, average="weighted")

log_experiment(
    results={
        "model": "RandomForest Full",
        "target": TARGET,
        "description": f"Finales RandomForest-Modell, trainiert auf dem gesamten Trainingsdatensatz, evaluiert auf dem Testset. {DESCRIPTION}",
        "features": ", ".join(X_train_full.columns),
        "data_points_train": len(X_train_full),
        "data_points_test": len(X_test),
        "accuracy": final_model.score(X_test, y_test),
        "importance": [
            {"feature": row["feature"], "importance": row["importance"]}
            for _, row in feature_importance_df_ensemble.iterrows()
        ],
        "klassifikations_report": classification_report(y_test, y_pred_test, output_dict=True),
        "confusion_matrix": confusion_matrix(y_test, y_pred_test).tolist()
    },
    filepath=PROJECT_ROOT / "prediction_model" / "models" / "doc_prediction_models.xlsx"
)

print(classification_report(y_test, y_pred_test))
print("Confusion Matrix:")
print(confusion_matrix(y_test, y_pred_test))

# =========================
# Save the model
# =========================
model_save_path = MODEL_PATH / "random_forest_model.pkl"
model_save_path.parent.mkdir(parents=True, exist_ok=True)
joblib.dump(final_model, model_save_path)