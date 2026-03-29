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
def load_combined_model(model_dir):
    model_dir = model_dir
    combined_model = CombinedFoldEnsemble(model_dir=model_dir)
    return combined_model

st.set_page_config(page_title="Gebäudemerkmale Erkennen", page_icon="🏠", layout="wide")
col1, col2 = st.columns([1, 3])
col3, col4 = st.columns([1, 3])
def main():
    with st.container():
        with col1:
            st.title("Gebäudemerkmale Erkennen")
            st.write("Hier können Sie die Merkmale eines Gebäudes vorhersagen.")
            st.write("Bitte geben Sie die Adresse ein:")

            address = st.text_input(
                "Adresse des Gebäudes",
                "",
                help="Geben Sie die vollständige Adresse des Gebäudes ein, z.B. 'Musterstrasse 1, 1234 Musterstadt'."
            )
            
            if st.button("Einschätzung starten"):
                if not address:
                    st.error("Bitte geben Sie eine Adresse ein, um die Einschätzung zu starten.")
                    return
                

                try:
                    with st.spinner("Daten werden extrahiert und Einschätzung wird durchgeführt..."):
                        with col2:
                            df = collect_building_data(address)
                            

                            with st.container(horizontal=True):
                                model_configs = [
                                    ("prediction_model/models/fassade_bekleidung/saved_models", "Fassade Bekleidung"),
                                    ("prediction_model/models/dach_bekleidung/saved_models", "Dach Bekleidung"),
                                    ("prediction_model/models/konstruktion_dach/saved_models", "Konstruktion Dach"),
                                    ("prediction_model/models/tragwerk_fassade/saved_models", "Tragwerk Fassade"),
                                    ("prediction_model/models/fassade_daemmung/saved_models", "Fassaden Dämmung"),
                                    ("prediction_model/models/fenster/saved_models", "Fenster"),
                                    ("prediction_model/models/bodenaufbau/saved_models", "Bodenaufbau"),
                                    ("prediction_model/models/konstruktion_decke/saved_models", "Konstruktion Dach"),
                                    ("prediction_model/models/schadstoff/saved_models", "Schadstoffe")
                                ]
                                
                                results_list = []
                                st.subheader("Einschätzungsergebnis")
                                
                                for model_dir, label in model_configs:
                                    model = load_combined_model(model_dir=model_dir)
                                    result = model.predict(df)
                                    results_list.append({
                                        "Attribut": result["model_name"],
                                        "Einschätzung": result["prediction"],
                                        "Sicherheit": result["confidence"]
                                    })
                                    model_col = str(result["model_name"]).upper()
                                    df[model_col] = result["prediction"]
                                    
                                    # Save updated dataframe to Excel file
                                    output_file = "prediction_model/data/collected_building_data.xlsx"
                                    df.to_excel(output_file, index=False)

                                results_df = pd.DataFrame(results_list)
                                st.session_state["prediction_result"] = results_list
                                st.session_state["input_data"] = df
                                st.dataframe(results_df)

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
                predictions = [item["Einschätzung"] for item in st.session_state["prediction_result"]]
                analysis = analysis_service.analyze(st.session_state["input_data"], predictions)

                st.subheader("Einschätzung")
                st.write(analysis["summary"])

if __name__ == "__main__":
    main()
