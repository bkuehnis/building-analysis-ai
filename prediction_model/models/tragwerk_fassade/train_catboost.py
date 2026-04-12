"""
run:
python -m prediction_model.models.tragwerk_fassade.train_catboost
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
from catboost import CatBoostClassifier, Pool
from prediction_model.models.doc_prediction_models import log_experiment

# =========================
# Paths
# =========================
PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")

DATA_PATH = PROJECT_ROOT / os.getenv("OUTPUT_DATASET_PATH")
MODEL_PATH = PROJECT_ROOT / os.getenv("OUTPUT_MODEL_PATH") / "tragwerk_fassade" /"saved_models"

df = pd.read_excel(DATA_PATH)

# =========================
# Prepare Data
# =========================
TARGET = "TRAGWERK_FASSADE"

# drop all except required columns + target
REQUIRED_COLUMNS = [
    "BAUJAHR",
    "HOLZ",
    "STAHL",
    "STAHLBLECH",
    "BETON",
    "HAUPTNUTZUNG",
    "FASSADE_BEKLEIDUNG",
    "KONSTRUKTION_DACH",
]


df = df[REQUIRED_COLUMNS + [TARGET]].copy()

# drop rows with missing target
df = df.dropna(subset=[TARGET]).copy()

# drop rows with missing values in required columns
X = df.drop(columns=[TARGET])
y = df[TARGET]

# Identify categorical columns
categorical_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()

# Convert categorical columns to string and replace NA
for col in categorical_cols:
    X[col] = X[col].astype(str)

# data count
print("Data shape:", X.shape)
print("Target distribution:")
print(y.value_counts())

# =========================
# Variables for logging/training
# =========================
N_SPLITS = 5
SEED = 5
DESCRIPTION = "NEW: changed test samples"

# =========================
# K-Fold Cross-Validation for CatBoost
# =========================
skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)

f1_scores = []
fold_models = []
fold_infos = []

# Store out-of-fold predictions for aggregated evaluation
oof_preds = np.empty(len(y), dtype=object)

for fold, (train_idx, val_idx) in enumerate(skf.split(X, y), start=1):
    X_train_fold = X.iloc[train_idx]
    y_train_fold = y.iloc[train_idx]
    X_val_fold = X.iloc[val_idx]
    y_val_fold = y.iloc[val_idx]

    train_pool = Pool(X_train_fold, y_train_fold, cat_features=categorical_cols)
    val_pool = Pool(X_val_fold, y_val_fold, cat_features=categorical_cols)

    model = CatBoostClassifier(
        iterations=500,
        depth=6,
        learning_rate=0.02,
        loss_function="MultiClass",
        eval_metric="TotalF1",
        random_seed=SEED + fold,
        verbose=0
    )

    model.fit(
        train_pool,
        eval_set=val_pool,
        use_best_model=True
    )

    # Save fold model
    fold_model_path = MODEL_PATH / "folds" / f"catboost_fold_{fold}.cbm"
    fold_model_path.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(fold_model_path))

    # Predict on validation fold
    y_pred_val = np.array(model.predict(val_pool)).flatten()
    oof_preds[val_idx] = y_pred_val

    # Calculate fold F1 score
    fold_f1 = f1_score(y_val_fold, y_pred_val, average="macro")
    f1_scores.append(fold_f1)
    fold_models.append(model)

    print(f"Fold {fold}: F1 = {fold_f1:.4f}")

    fold_infos.append({
        "fold": fold,
        "train_size": len(train_idx),
        "val_size": len(val_idx),
        "y_val_true": y_val_fold,
        "y_val_pred": y_pred_val
    })

# Print cross-validation summary
avg_f1_cv = np.mean(f1_scores)
std_f1_cv = np.std(f1_scores)
print(f"\nAverage F1 across {N_SPLITS} folds: {avg_f1_cv:.4f} ± {std_f1_cv:.4f}")

# =========================
# Aggregated CV Validation Results (Out-of-Fold Predictions)
# =========================
y_true = y.values

cv_accuracy = np.mean(oof_preds == y_true)
cv_f1 = f1_score(y_true, oof_preds, average="macro")

print("\nCatBoost Cross-Validation Classification Report:\n")
print(classification_report(y_true, oof_preds))
print("Confusion Matrix CatBoost CV:\n")
print(confusion_matrix(y_true, oof_preds))
print(f"CatBoost CV F1 on validation folds: {cv_f1:.4f}")

# Average feature importance across all fold models
feature_importance_df_cv = pd.DataFrame({
    "feature": X.columns,
    "importance": np.mean([model.get_feature_importance() for model in fold_models], axis=0)
}).sort_values(by="importance", ascending=False)

# =========================
# Log Results
# =========================

# Log fold-specific results
for model, info, fold_f1 in zip(fold_models, fold_infos, f1_scores):
    feature_importance_df = pd.DataFrame({
        "feature": X.columns,
        "importance": model.get_feature_importance()
    }).sort_values(by="importance", ascending=False)

    log_experiment(
        results={
            "model": f"CatBoost Fold {info['fold']}",
            "target": TARGET,
            "data_points_train": info["train_size"],
            "data_points_val": info["val_size"],
            "features": ", ".join(X.columns),
            "description": f"Fold {info['fold']} aus {N_SPLITS}-Fold Cross-Validation.",
            "importance": [
                {"feature": row["feature"], "importance": row["importance"]}
                for _, row in feature_importance_df.iterrows()
            ],
            "klassifikations_report": classification_report(
                info["y_val_true"],
                info["y_val_pred"],
                output_dict=True
            ),
            "fold_f1": fold_f1,
            "confusion_matrix": confusion_matrix(
                info["y_val_true"],
                info["y_val_pred"]
            ).tolist()
        },
        filepath=PROJECT_ROOT / "prediction_model" / "models" / "doc_prediction_models_new.xlsx"
    )

# Log aggregated CV results
log_experiment(
    results={
        "model": "CatBoost CV Summary",
        "target": TARGET,
        "data_points_train": len(y),
        "features": ", ".join(X.columns),
        "description": (
            f"Aggregierte Auswertung der Out-of-Fold-Vorhersagen aus "
            f"{N_SPLITS}-Fold Cross-Validation. {DESCRIPTION}"
        ),
        "importance": [
            {"feature": row["feature"], "importance": row["importance"]}
            for _, row in feature_importance_df_cv.iterrows()
        ],
        "accuracy": cv_accuracy,
        "klassifikations_report": classification_report(
            y_true,
            oof_preds,
            output_dict=True
        ),
        "avg_f1_cv": avg_f1_cv,
        "std_f1_cv": std_f1_cv,
        "f1_cv_aggregated": cv_f1,
        "confusion_matrix": confusion_matrix(y_true, oof_preds).tolist()
    },
    filepath=PROJECT_ROOT / "prediction_model" / "models" / "doc_prediction_models_new.xlsx"
)

print(f"\nFold-Modelle gespeichert unter: {MODEL_PATH / 'folds'}")