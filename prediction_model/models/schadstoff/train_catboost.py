"""
to run: 
python -m prediction_model.models.schadstoff.train_catboost

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
from catboost import CatBoostClassifier, Pool
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
# Train/Test Split
# =========================
X_train_full, X_test, y_train_full, y_test = train_test_split(
    X, y, test_size=0.2, random_state=5, stratify=y
)

N_SPLITS = 5
SEED = 5
DESCRIPTION = "NEW: "

# =========================
# K-Fold training
# =========================
skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)

f1_scores = []
fold_models = []

for fold, (train_idx, val_idx) in enumerate(skf.split(X_train_full, y_train_full), start=1):
    X_train_fold = X_train_full.iloc[train_idx]
    y_train_fold = y_train_full.iloc[train_idx]
    X_val_fold = X_train_full.iloc[val_idx]
    y_val_fold = y_train_full.iloc[val_idx]

    train_pool = Pool(X_train_fold, y_train_fold, cat_features=categorical_cols)
    val_pool = Pool(X_val_fold, y_val_fold, cat_features=categorical_cols)

    model = CatBoostClassifier(
        iterations=500,
        depth=6,
        learning_rate=0.02,
        loss_function="MultiClass",
        eval_metric="TotalF1",
        random_seed=SEED,
        verbose=0
    )

    model.fit(train_pool, eval_set=val_pool, use_best_model=True)

    y_pred = np.array(model.predict(val_pool)).flatten()
    fold_f1 = f1_score(y_val_fold, y_pred, average="weighted")

    f1_scores.append(fold_f1)
    fold_models.append(model)

    model_save_path = MODEL_PATH / "folds" / f"catboost_fold_{fold}.cbm"
    model_save_path.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(model_save_path))

    print(f"Fold {fold}: F1 = {fold_f1:.4f}")

avg_f1_cv = np.mean(f1_scores)
std_f1_cv = np.std(f1_scores)

# =========================
# Ensemble prediction on test set
# =========================
y_test_array = np.array(y_test).flatten()

probas = [model.predict_proba(X_test) for model in fold_models]
mean_proba = np.mean(probas, axis=0)

class_labels = np.array(fold_models[0].classes_)
ensemble_preds = class_labels[np.argmax(mean_proba, axis=1)]

ensemble_f1_test = f1_score(y_test_array, ensemble_preds, average="weighted")

# =========================
# Evaluation of ensemble on test set
# =========================

print(f"\nMean CV F1: {avg_f1_cv:.4f}")
print(f"Std CV F1: {std_f1_cv:.4f}")
print("\nEnsemble Classification Report:\n")
print(classification_report(y_test_array, ensemble_preds))
print("Confusion Matrix Ensemble:\n")
print(confusion_matrix(y_test_array, ensemble_preds))
print("Ensemble F1 on test set:", f"{ensemble_f1_test:.4f}")

# =========================
# Log each fold's results
# =========================
for i, (model, fold_f1) in enumerate(zip(fold_models, f1_scores), start=1):
    feature_importances = model.get_feature_importance()
    feature_importance_df_fold = pd.DataFrame({
        "feature": X.columns,
        "importance": feature_importances
    }).sort_values(by="importance", ascending=False)

    y_pred_fold = np.array(model.predict(X_test)).flatten()

    log_experiment(
        results={
            "model": f"CatBoost Fold {i}",
            "target": TARGET,
            "data_points_train": len(X_train_full) - len(X_val_fold),
            "data_points_val": len(X_val_fold),
            "data_points_test": len(X_test),
            "features": ", ".join(X.columns),
            "description": f"Fold {i} aus {N_SPLITS}-Fold CV, evaluiert auf Testset.",
            "importance": [
                {"feature": row["feature"], "importance": row["importance"]}
                for _, row in feature_importance_df_fold.iterrows()
            ],
            "accuracy": np.mean(y_pred_fold == y_test_array),
            "klassifikations_report": classification_report(y_test_array, y_pred_fold, output_dict=True),
            "f1_cv": fold_f1,
            "f1_test": f1_score(y_test_array, y_pred_fold, average="weighted"),
            "confusion_matrix": confusion_matrix(y_test_array, y_pred_fold).tolist()
        },
        filepath=PROJECT_ROOT / "prediction_model" / "models" / "doc_prediction_models.xlsx"
    )

# =========================
# Log ensemble results
# =========================
feature_importance_df = pd.DataFrame({
    "feature": X.columns,
    "importance": np.mean([model.get_feature_importance() for model in fold_models], axis=0)
}).sort_values(by="importance", ascending=False)

log_experiment(
    results={
        "model": "CatBoost Ensemble",
        "target": TARGET,
        "data_points_train": len(X_train_full),
        "data_points_test": len(X_test),
        "features": ", ".join(X.columns),
        "description": f"Ensemble aus {N_SPLITS}-Fold CV {DESCRIPTION}", 
        "importance": [
            {"feature": row["feature"], "importance": row["importance"]}
            for _, row in feature_importance_df.iterrows()
        ],
        "accuracy": np.mean(ensemble_preds == y_test_array),
        "klassifikations_report": classification_report(y_test_array, ensemble_preds, output_dict=True),
        "avg_f1_cv": avg_f1_cv,
        "std_f1_cv": std_f1_cv,
        "f1_test": ensemble_f1_test,
        "confusion_matrix": confusion_matrix(y_test_array, ensemble_preds).tolist()
    },
    filepath=PROJECT_ROOT / "prediction_model" / "models" / "doc_prediction_models.xlsx"
)
#=========================
# Train final model on full training data
#=========================
train_pool_full = Pool(X_train_full, y_train_full, cat_features=categorical_cols)
test_pool = Pool(X_test, y_test, cat_features=categorical_cols) 

final_model = CatBoostClassifier(
    iterations=500,
    depth=6,
    learning_rate=0.02,
    loss_function="MultiClass",
    eval_metric="TotalF1",
    random_seed=5,
    verbose=60
)

final_model.fit(train_pool_full, eval_set=test_pool, use_best_model=True)

# Evaluation of final model trained on full data

final_preds_full = final_model.predict(X_test)
final_preds_full = np.array(final_preds_full).flatten()

preds = final_model.predict(X_test)
preds = preds.flatten()  # wichtig, damit sklearn sauber rechnet


f1_test_full = f1_score(y_test_array, final_preds_full, average="weighted")

print("\nFinal Model Classification Report:\n")
print(classification_report(y_test_array, final_preds_full))
print("Confusion Matrix Final Model:\n")
print(confusion_matrix(y_test_array, final_preds_full))
print("Final model F1:", f"{f1_test_full: .4f}")

# save to log
log_experiment(
    results={
        "model": "CatBoost Final Model",
        "target": TARGET,
        "data_points_train": len(X_train_full),
        "data_points_test": len(X_test),
        "features": ", ".join(X.columns),
        "description": f"Trainiert auf dem gesamten Trainingsdatensatz, evaluiert auf dem Testset. {DESCRIPTION}",
        "importance": [dict(feature=row['feature'], importance=row['importance']) for _, row in feature_importance_df.iterrows()],
        "accuracy": np.mean(final_preds_full == y_test_array),
        "klassifikations_report": classification_report(y_test_array, final_preds_full, output_dict=True),
        "confusion_matrix": confusion_matrix(y_test_array, final_preds_full).tolist()  # als Liste speichern, da DataFrame nicht direkt in Excel passt
    },
    filepath=PROJECT_ROOT / "prediction_model" / "models" / "doc_prediction_models.xlsx"
)


# =====================
# Save models
# =========================
MODEL_PATH_CATBOOST = MODEL_PATH / "catboost_final_model.cbm"
MODEL_PATH_CATBOOST.parent.mkdir(parents=True, exist_ok=True)

final_model.save_model(MODEL_PATH_CATBOOST)


MODEL_PATH_CB_ENSEMBLE = MODEL_PATH / "catboost_ensemble.cbm"
MODEL_PATH_CB_ENSEMBLE.parent.mkdir(parents=True, exist_ok=True)
final_model.save_model(MODEL_PATH_CB_ENSEMBLE)




print(f"\nModel saved to: {MODEL_PATH}")