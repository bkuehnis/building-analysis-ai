"""
Streamlit App for Bausubstanz Erkennung (Building Substance Detection)

pip install:
- streamlit
- pandas
- numpy
- joblib

to run:
streamlit run prediction_model/MyApp.py
"""
import streamlit as st
from services.combined_prediction_service import CombinedFoldEnsemble
from collect_building_data import collect_building_data
from services.openai_analysis_service import OpenAIAnalysisService
import pandas as pd
import numpy as np
import joblib
from pathlib import Path

@st.cache_resource
def load_combined_model():
    model_dir = 'prediction_model/models/schadstoff/saved_models'
    combined_model = CombinedFoldEnsemble(model_dir=model_dir)
    return combined_model

st.set_page_config(page_title="Bausubstanz Erkennung", page_icon="🏠", layout="wide")
col1, col2 = st.columns([1, 3])
col3, col4 = st.columns([1, 3])
def main():
    with st.container():
        with col1:
            st.title("Bausubstanz Erkennung")
            st.write("Hier können Sie die Bausubstanz eines Gebäudes vorhersagen.")
            st.write("Bitte geben Sie die Adresse ein:")

            address = st.text_input(
                "Adresse des Gebäudes",
                "",
                help="Geben Sie die vollständige Adresse des Gebäudes ein, z.B. 'Musterstrasse 1, 1234 Musterstadt'."
            )

            if st.button("Vorhersage starten"):
                if not address:
                    st.error("Bitte geben Sie eine Adresse ein, um die Vorhersage zu starten.")
                    return

                try:
                    with st.spinner("Daten werden extrahiert und Vorhersage wird durchgeführt..."):
                        with col2:
                            df = collect_building_data(address)

                            with st.container(horizontal=True):
                                model = load_combined_model()
                                result = model.predict(df)

                                new_df = pd.DataFrame({
                                    "Attribut": [result["model_name"]],
                                    "Vorhersage": [result["prediction"]],
                                    "Sicherheit": [result["confidence"]]
                                })
                                st.session_state["prediction_result"] = result
                                st.session_state["input_data"] = df
                                st.subheader("Vorhersageergebnis")
                                st.dataframe(new_df)

                except Exception as e:
                    st.error(f"Fehler: {e}")

    with st.container(horizontal=True):
        with col3:
            input_data = st.session_state.get("input_data")
            prediction_result = st.session_state.get("prediction_result")
                                       
            
            if input_data is None or prediction_result is None:
                return

            EGID = input_data["EGID"].iloc[0]
            for i in range(1, 3):
                image_path = Path(f"prediction_model/output/images/{EGID}/streetview_{i}_{EGID}.jpeg")
                if image_path.exists():
                    st.image(str(image_path), caption="Extrahiertes Street View Bild", width=400)
                else:
                    st.warning("Kein Street View Bild gefunden für die angegebene Adresse.")

        with col4:
            with st.spinner("Analyse der Einschätzung..."):
                analysis_service = OpenAIAnalysisService(api_key=None)
                analysis = analysis_service.analyze(st.session_state["input_data"], [st.session_state["prediction_result"]["prediction"]])

                st.subheader("Einschätzung")
                st.write(analysis["summary"])

if __name__ == "__main__":
    main()
