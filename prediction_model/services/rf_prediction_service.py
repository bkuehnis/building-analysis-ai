from __future__ import annotations
from pathlib import Path
import joblib
import numpy as np
import pandas as pd


class RandomForestFoldEnsemble:
    def __init__(self, model_dir: str | Path, feature_columns: list[str] | None = None, required_columns: list[str] | None = None):
        self.model_dir = Path(model_dir)
        self.models = self._load_models()
        if feature_columns is None:
            feature_columns = self._load_feature_columns()
        self.feature_columns = feature_columns
        if required_columns is None:
            required_columns = feature_columns
        self.required_columns = required_columns
        self.classes_ = self.models[0].classes_

    def _load_models(self):
        fold_dir = self.model_dir / "folds"
        model_paths = sorted(fold_dir.glob("random_forest_fold_*.joblib"))
        if not model_paths:
            raise FileNotFoundError(f"Keine RF-Fold-Modelle gefunden in {fold_dir}")

        return [joblib.load(path) for path in model_paths]

    def _load_feature_columns(self):
        feature_path = self.model_dir / "feature_columns.joblib"
        if not feature_path.exists():
            raise FileNotFoundError(f"feature_columns.joblib nicht gefunden: {feature_path}")
        return joblib.load(feature_path)

    def _prepare_input(self, X_new: pd.DataFrame) -> pd.DataFrame:
        X = X_new.copy()

        # fehlende Spalten hinzufügen
        for col in self.required_columns:
            if col not in X.columns:
                X[col] = np.nan

        X = X[self.required_columns]

        # 👉 ALLE object-Spalten behandeln (kein categorical_cols nötig)
        for col in X.columns:
            if X[col].dtype == "object":
                X[col] = X[col].fillna("UNBEKANNT").astype(str)

        # one-hot encoding
        X_encoded = pd.get_dummies(X, drop_first=False)

        # gleiche Spalten wie Training
        X_encoded = X_encoded.reindex(columns=self.feature_columns, fill_value=0)

        return X_encoded

    def predict_proba(self, X_new: pd.DataFrame) -> np.ndarray:
        X_prepared = self._prepare_input(X_new)

        probas = np.array([model.predict_proba(X_prepared) for model in self.models])
        mean_probas = probas.mean(axis=0)

        return mean_probas

    def predict(self, X_new: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        mean_probas = self.predict_proba(X_new)
        class_indices = np.argmax(mean_probas, axis=1)

        predictions = self.classes_[class_indices]
        confidences = mean_probas.max(axis=1)

        return predictions, confidences, mean_probas