"""
to run:
python -m prediction_model.models.fassade_daemmung.train_RandomForest
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
MODEL_PATH = PROJECT_ROOT / os.getenv("OUTPUT_MODEL_PATH") / "fassade_daemmung" / "saved_models"

df = pd.read_excel(DATA_PATH)

# =========================
# Prepare Data
# =========================
TARGET = "FASSADE_DAEMMUNG"

# drop all except required columns + target
REQUIRED_COLUMNS = [
    "BAUJAHR",
    "TRAGWERK_FASSADE",
    "FASSADE_BEKLEIDUNG",
    "DACH_BEKLEIDUNG",
    "KONSTRUKTION_DACH",
    "HAUPTNUTZUNG",
]


# Select only required columns and target, drop missing values
df = df[REQUIRED_COLUMNS + [TARGET]].copy()
df = df.dropna(subset=[TARGET]).copy()
X = df.drop(columns=[TARGET])
y = df[TARGET]

# Encode categorical features
X_encoded = pd.get_dummies(X, drop_first=False)

# Save feature columns for prediction service
feature_columns = X_encoded.columns.tolist()
feature_columns_path = MODEL_PATH / "feature_columns.joblib" # .joblib because it's said to be better for storing lists than .pkl 
feature_columns_path.parent.mkdir(parents=True, exist_ok=True)
joblib.dump(feature_columns, feature_columns_path)

# Training configuration
N_SPLITS = 5
SEED = 5
DESCRIPTION = "NEW:"

# =========================
# K-Fold Cross-Validation for RandomForest
# =========================

skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)

f1_scores = []
fold_models = []
fold_infos = []

# Store out-of-fold predictions for aggregated evaluation
oof_preds = np.empty(len(y), dtype=object)

for fold, (train_index, val_index) in enumerate(skf.split(X_encoded, y), start=1):
    X_train_fold = X_encoded.iloc[train_index]
    X_val_fold = X_encoded.iloc[val_index]
    y_train_fold = y.iloc[train_index]
    y_val_fold = y.iloc[val_index]

    # Train RandomForest classifier
    model = RandomForestClassifier(
        n_estimators=500,
        max_depth=None,
        class_weight="balanced",
        random_state=SEED + fold,
        n_jobs=-1
    )
    model.fit(X_train_fold, y_train_fold)

    # save fold model
    fold_model_path = MODEL_PATH / "folds" / f"random_forest_fold_{fold}.joblib"
    fold_model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, fold_model_path)

    # Predict on validation fold
    y_pred_val = model.predict(X_val_fold)
    oof_preds[val_index] = y_pred_val

    # Calculate fold F1 score
    fold_f1 = f1_score(y_val_fold, y_pred_val, average="macro")
    f1_scores.append(fold_f1)
    fold_models.append(model)

    print(f"Fold {fold}: F1 = {fold_f1:.4f}")

    fold_infos.append({
        "fold": fold,
        "train_size": len(train_index),
        "val_size": len(val_index),
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

print("\nRF Cross-Validation Classification Report:\n")
print(classification_report(y_true, oof_preds))
print("Confusion Matrix RF CV:\n")
print(confusion_matrix(y_true, oof_preds))
print(f"RF CV F1 on validation folds: {cv_f1:.4f}")

# Average feature importance across all fold models
feature_importance_df_cv = pd.DataFrame({
    "feature": X_encoded.columns,
    "importance": np.mean([model.feature_importances_ for model in fold_models], axis=0)
}).sort_values(by="importance", ascending=False)


# =========================
# Log Results
# =========================

# Log fold-specific results
for model, info, fold_f1 in zip(fold_models, fold_infos, f1_scores):
    feature_importance_df = pd.DataFrame({
        "feature": X_encoded.columns,
        "importance": model.feature_importances_
    }).sort_values(by="importance", ascending=False)

    log_experiment(
        results={
            "model": f"RandomForest Fold {info['fold']}",
            "target": TARGET,
            "data_points_train": info["train_size"],
            "data_points_val": info["val_size"],
            "description": f"Fold {info['fold']} aus {N_SPLITS}-Fold Cross-Validation.",
            "features": ", ".join(X_encoded.columns),
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
        "model": "RandomForest CV Summary",
        "target": TARGET,
        "data_points_total": len(X_encoded),
        "description": (
            f"Aggregierte Auswertung der Out-of-Fold-Vorhersagen aus "
            f"{N_SPLITS}-Fold Cross-Validation. {DESCRIPTION}"
        ),
        "features": ", ".join(X_encoded.columns),
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
