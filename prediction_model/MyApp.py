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
import streamlit.components.v1 as components
import os
from services.combined_prediction_service import CombinedFoldEnsemble
from collect_building_data import collect_building_data
from services.openai_analysis_service import OpenAIAnalysisService
from models.additional_openai_prediction import AdditionalPredictionOpenAI
import pandas as pd
import numpy as np
import joblib
from pathlib import Path

@st.cache_resource
def load_combined_model(model_dir):
    model_dir = model_dir
    combined_model = CombinedFoldEnsemble(model_dir=model_dir)
    return combined_model

def show_streetview_embed(lat: float, lon: float):
    api_key = os.getenv("API_KEY_GOOGLE_MAPS")

    if not api_key:
        st.error("API_KEY_GOOGLE_MAPS fehlt.")
        return

    url = (
        "https://www.google.com/maps/embed/v1/streetview"
        f"?key={api_key}"
        f"&location={lat},{lon}"
        f"&radius=23"
        f"&source=outdoor"
        f"&fov=100"
    )

    components.iframe(url, height=500, scrolling=False)

st.set_page_config(page_title="Gebäudemerkmale Erkennen", page_icon="🏠", layout="wide")
col1, col2, col3 = st.columns([0.35, 1.5 ,1])
col4, col5 = st.columns([1, 3])
col6, col7 = st.columns([1.5, 2])
def main():
    with st.container():
        with col1:
            st.title("Gebäude- merkmale Erkennen")
            st.write("Hier können Sie die Merkmale eines Gebäudes vorhersagen.")
            st.write("Bitte geben Sie die Adresse ein:")

            if "locked" not in st.session_state:
                st.session_state["locked"] = False

            if "address" not in st.session_state:
                st.session_state["address"] = ""

            address = st.text_area(
                "Adresse des Gebäudes",
                value=st.session_state["address"],
                disabled=st.session_state["locked"],
                height=100,
                help="Geben Sie die vollständige Adresse des Gebäudes ein, z.B. 'Musterstrasse 1, 1234 Musterstadt'."
            )

            st.session_state["address"] = address

            col_start, col_reset = st.columns(2)

            with col_start:
                if st.button("Einschätzung starten", disabled=st.session_state["locked"]):
                    if not address:
                        st.error("Bitte geben Sie eine Adresse ein, um die Einschätzung zu starten.")
                    else:
                        try:
                            with st.spinner("Daten werden gesammelt..."):
                                df = collect_building_data(address)
                        except Exception:
                            st.error("Adresse konnte nicht gefunden werden.")
                            return
                            

                        if df is None or df.empty:
                            st.error("Es konnten keine Gebäudedaten gefunden werden.")
                        else:
                            st.session_state["input_data"] = df
                            st.session_state["locked"] = True

                            if "lat" in df.columns and "lon" in df.columns:
                                st.session_state["lat"] = df["lat"].iloc[0]
                                st.session_state["lon"] = df["lon"].iloc[0]

                            st.rerun()

            with col_reset:
                if st.button("Neue Adresse eingeben 🔄"):
                    for key in [
                        "locked",
                        "address",
                        "input_data",
                        "prediction_result",
                        "llm_result",
                        "llm_result_table",
                        "comparison_result",
                        "lat",
                        "lon",
                    ]:
                        st.session_state.pop(key, None)
                    st.rerun()

            if st.session_state["locked"]:
                st.info("Adresse gefunden: " + "\n" + st.session_state["address"])
                with col2:
                    st.subheader("Offizielle Gebäudedaten des Bundes")
                    st.table(st.session_state["input_data"].iloc[:, 0:10])

                    st.subheader("Mittels KI-Bildanalyse erkannte Merkmale:")

                    df_img = st.session_state["input_data"].iloc[:, 10:].copy()
                    df_img = df_img.replace(["None", ""], np.nan)
                    df_img = df_img.dropna(axis=1, how="all")

                    chunk_size = 8

                    for start in range(0, len(df_img.columns), chunk_size):
                        chunk_df = df_img.iloc[:, start:start + chunk_size]
                        st.table(chunk_df)

                df = st.session_state.get("input_data")
                if df is None or df.empty:
                    st.error("Keine Eingabedaten vorhanden.")
                    return
                try:
                    with col3:
                        with st.spinner("Einschätzung wird durchgeführt..."):
                           
                            

                            with st.container(horizontal=True):
                                model_configs = [
                                    ("prediction_model/models/fassade_bekleidung/saved_models", "Fassade Bekleidung"),
                                    ("prediction_model/models/konstruktion_dach/saved_models", "Konstruktion Dach"),
                                    ("prediction_model/models/dach_bekleidung/saved_models", "Dach Bekleidung"),
                                    ("prediction_model/models/tragwerk_fassade/saved_models", "Tragwerk Fassade"),
                                    ("prediction_model/models/fassade_daemmung/saved_models", "Fassaden Dämmung"),
                                    ("prediction_model/models/fenster/saved_models", "Fenster"),
                                    ("prediction_model/models/bodenaufbau/saved_models", "Bodenaufbau"),
                                    ("prediction_model/models/konstruktion_decke/saved_models", "Konstruktion Dach"),
                                    ("prediction_model/models/schadstoff/saved_models", "Schadstoffe")
                                ]
                                
                                results_list = []
                                st.subheader("Einschätzungsergebnisse")
                                
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
                            st.session_state["results_df"] = results_df

                            # Für AdditionalPredictionOpenAI als dict aufbereiten
                            results_dict = {
                                item["Attribut"]: {
                                    "prediction": item["Einschätzung"],
                                    "confidence": item["Sicherheit"],
                                }
                                for item in results_list
                            }
                            df = st.session_state.get("input_data")
                            EGID = df["EGID"].iloc[0] 
                            openai_predictor = AdditionalPredictionOpenAI(model="gpt-4o-mini")
                            llm_result = openai_predictor.analyze(
                                df=df,
                                predictions=results_dict,
                                egid=EGID,
                                image_dir="prediction_model/output/images",
                                )


                            rows = []

                            for key, value in llm_result.items():
                                if key.endswith("_sicherheit") or key == "begruendung":
                                    continue

                                sicherheit_key = f"{key}_sicherheit"
                                sicherheit = llm_result.get(sicherheit_key)

                                rows.append({
                                    "Attribut": key,
                                    "Einschätzung": value,
                                    "Sicherheit": f"{round(sicherheit)} % " if sicherheit is not None else None                                })
                            
                            llm_df = pd.DataFrame(rows)

                            def clean_value(val):
                                if isinstance(val, (list, tuple, np.ndarray)):
                                    return val[0]
                                return val
                            results_df["Einschätzung"] = results_df["Einschätzung"].apply(clean_value)
                            results_df["Sicherheit"] = results_df["Sicherheit"].apply(clean_value) 
                            results_df["Sicherheit"] = (results_df["Sicherheit"] * 100).round(0).astype(int).astype(str) + " %"
                                                       
                            comparison_df = results_df.merge(
                                llm_df,
                                on="Attribut",
                                how="outer",
                                suffixes=("_modell", "_openai")
                            )

                            st.dataframe(comparison_df, hide_index=True)
                            st.session_state["llm_result"] = llm_result
                            st.session_state["llm_result_table"] = rows
                            st.session_state["comparison_result"] = comparison_df
                            


                except Exception as e:
                    st.error(f"Fehler: {e}")

    with st.container(horizontal=True):
        with col4:
            input_data = st.session_state.get("input_data")
            prediction_result = st.session_state.get("prediction_result")
            
            if input_data is None or prediction_result is None:
                return

            EGID = input_data["EGID"].iloc[0]
            image_path_google = Path(f"prediction_model/output/images/{EGID}/streetview_2_{EGID}.jpeg")

            if image_path_google.exists() or image_path_google.exists():

                if image_path_google.exists():
                    st.image(str(image_path_google), caption="Google Street View Bild", width='content')
                else:
                    st.warning("Kein Street View Bild")

            else:
                st.warning("Keine Bilder gefunden für die angegebene Adresse.")                    
            with col5:
                lat = st.session_state.get("lat")
                lon = st.session_state.get("lon") 

                if lat is None or lon is None:
                    return

                
                st.subheader("Interaktive Street View Ansicht")
                show_streetview_embed(lat, lon)

    with st.container(horizontal=True):
        with col6:

            col_start, col_end = st.columns([1, 1])
            with col_start:
                EGID = st.session_state["input_data"]["EGID"].iloc[0]
                image_path_swissimage = Path(f"prediction_model/output/images/{EGID}/swissimage_zoomed_{EGID}_0.jpeg")
                impage_path_cadstral = Path(f"prediction_model/output/images/{EGID}/cadastral_{EGID}_0.png")       
            
                if image_path_swissimage.exists():
                    st.image(str(image_path_swissimage), caption="Extrahiertes Flugbild", width='content')
                else:
                    st.warning("Kein Luftbild")

            with col_end:
                if impage_path_cadstral.exists():
                    st.image(str(impage_path_cadstral), caption="Katasterplan Ausschnitt", width='content')
                else:
                    st.warning("Kein Katasterplan Bild")


        with col7:
            with st.spinner("Analyse der Einschätzung..."):
                analysis_service = OpenAIAnalysisService(api_key=None)
                predictions = [item["Einschätzung"] for item in st.session_state["prediction_result"]]
                analysis = analysis_service.analyze(st.session_state["input_data"], predictions)

                st.subheader("Einschätzung")
                comparison_df = st.session_state.get("comparison_result")
                summary = analysis.get("summary", "")
                if summary:
                    st.markdown(f"**Zusammenfassung:** {summary}")

                st.markdown("**Begründung:**")
                reasoning = analysis.get("reasoning", [])
                if reasoning:
                    for reason in reasoning:
                        if isinstance(reason, dict):
                            attribute = reason.get("attribute", "-")
                            assessment = reason.get("assessment", "-")
                            reason_text = reason.get("reason", "-")
                            st.markdown(
                                f"- **{attribute}**: {assessment}  \n  _Begründung:_ {reason_text}"
                            )
                        else:
                            st.markdown(f"- {reason}")
                else:
                    st.markdown("Keine Begründung verfügbar.")

                st.markdown("**Unsicherheiten:**")
                uncertainty = analysis.get("uncertainty", [])
                if uncertainty:
                    for item in uncertainty:
                        if isinstance(item, dict):
                            attribute = item.get("attribute", "-")
                            reason_text = item.get("reason", "-")
                            st.markdown(f"- **{attribute}**: {reason_text}")
                        else:
                            st.markdown(f"- {item}")
                else:
                    st.markdown("Keine Unsicherheiten angegeben.")



if __name__ == "__main__":
    main()
