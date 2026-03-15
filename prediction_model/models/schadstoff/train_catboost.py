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

#=========================
# Train/Test Split
#=========================
X_train_full, X_test, y_train_full, y_test = train_test_split(
    X, y, test_size=0.2, random_state=5, stratify=y
)

#=========================
# Cross-Validation with CatBoost
#=========================

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

f1_scores = []

for fold, (train_idx, val_idx) in enumerate(skf.split(X_train_full, y_train_full), start=1):
    X_train_fold = X_train_full.iloc[train_idx]
    X_val_fold = X_train_full.iloc[val_idx]
    y_train_fold = y_train_full.iloc[train_idx]
    y_val_fold = y_train_full.iloc[val_idx]

    train_pool = Pool(X_train_fold, y_train_fold, cat_features=categorical_cols)
    val_pool = Pool(X_val_fold, y_val_fold, cat_features=categorical_cols)

    model = CatBoostClassifier(
        iterations=500,
        depth=6,
        learning_rate=0.02,
        loss_function="MultiClass",
        eval_metric="TotalF1",
        random_seed=5,
        verbose=0
    )

    model.fit(train_pool, eval_set=val_pool, use_best_model=True)

    y_pred = model.predict(X_val_fold)
    y_pred = y_pred.flatten()  # wichtig, damit sklearn sauber rechnet

    fold_f1 = f1_score(y_val_fold, y_pred, average="weighted")
    f1_scores.append(fold_f1)

    model_save_path = MODEL_PATH / "folds" / f"catboost_fold_{fold}.cbm"
    model_save_path.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(model_save_path))


    print(f"Fold {fold}: F1 = {fold_f1:.4f}")

print(f"\nMean CV F1: {np.mean(f1_scores):.4f}")
print(f"Std CV F1: {np.std(f1_scores):.4f}")

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

# =========================
# Load fold models
# =========================
fold_models = []
for fold in range(1, 9):
    fold_model_path = MODEL_PATH / "folds" / f"catboost_fold_{fold}.cbm"
    if fold_model_path.exists():
        model = CatBoostClassifier()
        model.load_model(str(fold_model_path))
        fold_models.append(model)
    else:
        print(f"Warning: Fold model {fold_model_path} not found.")

y_test_array = np.array(y_test).flatten()

# use class labels from first fold model
class_labels = np.array(fold_models[0].classes_)
print("Class order:", class_labels)

# =========================
# Ensemble of fold models
# =========================
probs_list = [model.predict_proba(X_test) for model in fold_models]
mean_probs = np.mean(probs_list, axis=0)

final_pred_indices = np.argmax(mean_probs, axis=1)
final_preds = class_labels[final_pred_indices]

# Evaluation of ensemble


print("\nEnsemble Classification Report:\n")
print(classification_report(y_test_array, final_preds))
print("Confusion Matrix Ensemble:\n")
print(confusion_matrix(y_test_array, final_preds))
print("Ensemble weighted F1:", f"{f1_score(y_test_array, final_preds, average="weighted"): .4f}")

# save to log
log_experiment(
    results={
        "model": "CatBoost Ensemble",
        "target": TARGET,
        "Data points": len(X_train_fold),
        "features": ", ".join(X.columns),
        "description": "Start: Zusammenfassung der F1-Scores der einzelnen Folds, dann Ensemble durch Mittelung der Vorhersagewahrscheinlichkeiten und Auswahl der Klasse mit der höchsten durchschnittlichen Wahrscheinlichkeit als endgültige Vorhersage.",
        "accuracy": np.mean(final_preds == y_test_array),
        "klassifikations_report": classification_report(y_test_array, final_preds, output_dict=True),
        "cv_f1_scores": [f"{score:.4f}" for score in f1_scores],
        "avg_f1_cv": np.mean(f1_scores),
        "std_f1_cv": np.std(f1_scores),
        "confusion_matrix": confusion_matrix(y_test_array, final_preds).tolist()  # als Liste speichern, da DataFrame nicht direkt in Excel passt


    },
    filepath=PROJECT_ROOT / "prediction_model" / "models" / "doc_prediction_models.xlsx"
)

# Evaluation of final model trained on full data

final_preds_full = final_model.predict(X_test)
final_preds_full = np.array(final_preds_full).flatten()

preds = final_model.predict(X_test)
preds = preds.flatten()  # wichtig, damit sklearn sauber rechnet

print("\nFinal Model Classification Report:\n")
print(classification_report(y_test_array, final_preds_full))
print("Confusion Matrix Final Model:\n")
print(confusion_matrix(y_test_array, final_preds_full))
print("Final model weighted F1:", f"{f1_score(y_test_array, final_preds_full, average="weighted"): .4f}")

# save to log
log_experiment(
    results={
        "model": "CatBoost Final Model",
        "target": TARGET,
        "Data points": len(X_train_full),
        "features": ", ".join(X.columns),
        "description": "Finales Modell, trainiert auf dem gesamten Trainingsdatensatz, evaluiert auf dem Testset.",
        "accuracy": np.mean(final_preds_full == y_test_array),
        "klassifikations_report": classification_report(y_test_array, final_preds_full, output_dict=True),
        "avg_f1_cv": np.mean(f1_scores),
        "std_f1_cv": np.std(f1_scores),
        "confusion_matrix": confusion_matrix(y_test_array, final_preds_full).tolist()  # als Liste speichern, da DataFrame nicht direkt in Excel passt
    },
    filepath=PROJECT_ROOT / "prediction_model" / "models" / "doc_prediction_models.xlsx"
)

# =========================
# Feature Importance 
# =========================
importances = final_model.get_feature_importance(type="FeatureImportance")
feature_importance = pd.DataFrame({
    "feature": X.columns,
    "importance": importances
}).sort_values(by="importance", ascending=False)

print("\nTop Features:\n")
print(feature_importance.head(10))

# =========================
# Save models
# =========================
MODEL_PATH_CATBOOST = MODEL_PATH / "catboost_final_model.cbm"
MODEL_PATH_CATBOOST.parent.mkdir(parents=True, exist_ok=True)

final_model.save_model(MODEL_PATH_CATBOOST)


MODEL_PATH_CB_ENSEMBLE = MODEL_PATH / "catboost_ensemble.cbm"
MODEL_PATH_CB_ENSEMBLE.parent.mkdir(parents=True, exist_ok=True)
final_model.save_model(MODEL_PATH_CB_ENSEMBLE)




print(f"\nModel saved to: {MODEL_PATH}")