"""
Streamlit App for Bausubstanz Erkennung (Building Substance Detection)

pip install:
- streamlit
- pandas
- numpy
- joblib

to run:
streamlit run MyApp.py

"""
import streamlit as st
import streamlit.components.v1 as components
import os
from services.combined_prediction_service import CombinedFoldEnsemble
from scripts.collect_building_data import collect_building_data
from openai_services.openai_final_analysis_service import OpenAIAnalysisService
from openai_services.additional_openai_prediction import AdditionalPredictionOpenAI
import pandas as pd
import numpy as np
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


def show_satellite_embed(lat: float, lon: float):
    api_key = os.getenv("API_KEY_GOOGLE_MAPS")

    if not api_key:
        st.error("API_KEY_GOOGLE_MAPS fehlt.")
        return

    url = (
        "https://www.google.com/maps/embed/v1/place"
        f"?key={api_key}"
        f"&q={lat},{lon}"
        f"&zoom=20"
        f"&maptype=satellite"
    )

    components.iframe(url, height=500, scrolling=False)

st.set_page_config(page_title="Gebäudemerkmale Erkennen", page_icon="🏠", layout="wide")
st.markdown("""
<style>
    .block-container {
        padding-top: 1.6rem;
    }
    div[data-testid="stHorizontalBlock"] {
        align-items: start;
    }
</style>
""", unsafe_allow_html=True)
col1 = st.columns(1)[0]
col2 =st.columns(1)[0]
col3 = st.columns(1)[0]

def main():
    with st.container():

        with col1:
            st.markdown("### Gebäudemerkmale Erkennen")

            if "locked" not in st.session_state:
                st.session_state["locked"] = False

            if "address" not in st.session_state:
                st.session_state["address"] = ""

            col_address, col_button = st.columns([5, 2])

            with col_address:
                address = st.text_input(
                    "Bitte Adresse des Gebäudes eingeben:",
                    value=st.session_state["address"],
                    disabled=st.session_state["locked"],
                    help="Geben Sie die vollständige Adresse des Gebäudes ein, z.B. 'Musterstrasse 1, 1234 Musterstadt'."
                )
                st.session_state["address"] = address
            with st.spinner("Daten werden gesammelt und analysiert mit openAI..."):

                with col_button:
                    btn_col1, btn_col2 = st.columns(2)
                    
                    with btn_col1:
                        st.write(" ")  # Platzhalter für vertikale Zentrierung
                        st.write(" ")  # Platzhalter für vertikale Zentrierung
                        if st.button("Starten", disabled=st.session_state["locked"], use_container_width=True):
                            if not address:
                                st.error("Bitte geben Sie eine Adresse ein, um die Einschätzung zu starten.")
                            else:
                                try:
                                    df = collect_building_data(address)
                                    st.info("Adresse gefunden: " + "\n" + st.session_state["address"])
                                except Exception:
                                    st.error("Adresse konnte nicht gefunden werden.")
                                    return

                                if df is None or df.empty:
                                    st.error("Es konnten keine Gebäudedaten gefunden werden.")
                                else:
                                    st.session_state["input_data"] = df
                                    st.session_state["locked"] = True
                                    st.session_state["address"] = address

                                    if "lat" in df.columns and "lon" in df.columns:
                                        st.session_state["lat"] = df["lat"].iloc[0]
                                        st.session_state["lon"] = df["lon"].iloc[0]

                                    st.rerun()

                    with btn_col2:
                        st.write(" ")  # Platzhalter für vertikale Zentrierung
                        st.write(" ")  # Platzhalter für vertikale Zentrierung
                        if st.button("Neue Adresse", use_container_width=True):
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
                                "results_df",
                                "analysis_result",
                                "comparison_result"
                            ]:
                                st.session_state.pop(key, None)
                            st.rerun()
    with st.container(horizontal=True):

            if st.session_state["locked"]:
                with col2:
                    st.markdown("#### Grundbuchdaten")
                    st.table(st.session_state["input_data"].iloc[:, 0:10].reset_index(drop=True))
                with col3:
                    st.markdown("#### Erkannte Gebäudemerkmale mit openAI und Einschätzungssicherheit")

                    # lat und lon nicht anzeigen, daher start 12
                    df_img = st.session_state["input_data"].iloc[:, 13:].copy()
                    df_img = df_img.replace(["None", ""], np.nan)
                    df_img = df_img.dropna(axis=1, how="all")

                    row_data = {}
                    for col in df_img.columns:
                        if "_confidence" in col.lower():
                            continue

                        value = df_img.iloc[0][col]
                        if pd.isna(value):
                            continue

                        confidence_col = f"{col}_confidence"
                        confidence = df_img[confidence_col].iloc[0] if confidence_col in df_img.columns else None

                        label = col.replace("_", " ").title()
                        if confidence is not None and not pd.isna(confidence):
                            confidence_text = f"{round(confidence * 100)}%"
                            row_data[label] = f"{value} ({confidence_text})"
                        else:
                            row_data[label] = value

                    if row_data:
                        st.dataframe(pd.DataFrame([row_data]), use_container_width=True, hide_index=True)

                df = st.session_state.get("input_data")
                if df is None or df.empty:
                    st.error("Keine Eingabedaten vorhanden.")
                    return
                try:
                    with col3:
                        df = st.session_state.get("input_data")
                        if df is None or df.empty:
                            return

                        if "comparison_result" not in st.session_state:
                            with st.spinner("Einschätzung wird durchgeführt..."):
                                model_configs = [
                                    ("prediction_model/models/fassade_bekleidung/saved_models", "Fassade Bekleidung"),
                                    ("prediction_model/models/konstruktion_dach/saved_models", "Konstruktion Dach"),
                                    ("prediction_model/models/dach_bekleidung/saved_models", "Dach Bekleidung"),
                                    ("prediction_model/models/tragwerk_fassade/saved_models", "Tragwerk Fassade"),
                                    ("prediction_model/models/fassade_daemmung/saved_models", "Fassaden Dämmung"),
                                    ("prediction_model/models/fenster/saved_models", "Fenster"),
                                    ("prediction_model/models/bodenaufbau/saved_models", "Bodenaufbau"),
                                    ("prediction_model/models/konstruktion_decke/saved_models", "Konstruktion Decke"),
                                    ("prediction_model/models/schadstoff/saved_models", "Schadstoffe"),
                                ]

                                results_list = []
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

                                df.to_excel("data/collected_building_data.xlsx", index=False)

                                results_df = pd.DataFrame(results_list)
                                st.session_state["prediction_result"] = results_list
                                st.session_state["input_data"] = df
                                st.session_state["results_df"] = results_df

                                results_dict = {
                                    item["Attribut"]: {
                                        "prediction": item["Einschätzung"],
                                        "confidence": item["Sicherheit"],
                                    }
                                    for item in results_list
                                }

                                EGID = df["EGID"].iloc[0]
                                openai_predictor = AdditionalPredictionOpenAI(model="gpt-4o-mini")
                                llm_result = openai_predictor.analyze(
                                    df=df,
                                    predictions=results_dict,
                                    egid=EGID,
                                    image_dir="buildings",
                                )

                                rows = []
                                for key, value in llm_result.items():
                                    if key.endswith("_sicherheit") or key == "begruendung":
                                        continue

                                    sicherheit_key = f"{key}_sicherheit"
                                    sicherheit = llm_result.get(sicherheit_key)

                                    rows.append({
                                        "Attribut": key,
                                        "Einschätzung": value.lower().capitalize() if isinstance(value, str) else value,
                                        "Sicherheit": f"{round(sicherheit)} %" if sicherheit is not None else None
                                    })

                                llm_df = pd.DataFrame(rows)

                                def clean_value(val):
                                    if isinstance(val, (list, tuple, np.ndarray)):
                                        return val[0]
                                    if isinstance(val, str):
                                        return val.lower().capitalize()
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

                                st.session_state["llm_result"] = llm_result
                                st.session_state["llm_result_table"] = rows
                                st.session_state["comparison_result"] = comparison_df

                        st.markdown("#### Einschätzungsergebnisse")
                        comparison_df = st.session_state.get("comparison_result")
                        if comparison_df is not None:
                                                    # sortiert nach der höchsten Sicherheit der eigenen Modellen
                                                    sort_col = next(
                                                        (c for c in ["Sicherheit_modell", "Sicherheit"] if c in comparison_df.columns),
                                                        None,
                                                    )

                                                    if sort_col is not None:
                                                        sorted_df = comparison_df.assign(
                                                            _sort_conf=pd.to_numeric(
                                                                comparison_df[sort_col].astype(str).str.replace("%", "", regex=False).str.strip(),
                                                                errors="coerce",
                                                            )
                                                        ).sort_values("_sort_conf", ascending=False).drop(columns=["_sort_conf"])
                                                        st.dataframe(sorted_df, hide_index=True)
                                                    else:
                                                        st.dataframe(comparison_df, hide_index=True)


                except Exception as e:
                    st.error(f"Fehler: {e}")

    with st.container(horizontal=True):
        col4, col5 = st.columns([1, 3])

        with col4:
            input_data = st.session_state.get("input_data")
            prediction_result = st.session_state.get("prediction_result")
            
            if input_data is None or prediction_result is None:
                return

            EGID = input_data["EGID"].iloc[0]
            image_path_google = Path(f"buildings/{EGID}/streetview_2_{EGID}.jpeg")

            if image_path_google.exists():

                if image_path_google.exists():
                    st.write("Beachte: Das Street View Bild zeigt möglicherweise nicht das gesuchte Objekt, sondern könnte ein benachbartes Gebäude darstellen.")
                    st.image(str(image_path_google), caption="Gefundenes Google Street View Bild", width='content')
                else:
                    st.warning("Kein Street View Bild")

            else:
                st.warning("Keine Bilder gefunden für die angegebene Adresse.")                    
        with col5:
            lat = st.session_state.get("lat")
            lon = st.session_state.get("lon") 

            if lat is None or lon is None:
                return

            st.markdown("#### Interaktive Street View Ansicht")
            st.write("Bitte beachten Sie das Referenzbild auf der linken Seite, um das Gebäude zu identifizieren. Es könnte sein, dass das Street View Bild ein benachbartes Gebäude zeigt. Zur Prüfung kann die Adressanzeige auf der Karte genutzt werden.")
            show_streetview_embed(lat, lon)

    with st.container():
        col6, col7, col8, col9 = st.columns(4)

        lat = st.session_state.get("lat")
        lon = st.session_state.get("lon")
        input_data = st.session_state.get("input_data")

        EGID = None
        image_path_cadastral = None
        image_path_zh_map = None
        image_path_zh_map_ortho = None

        if input_data is not None and not input_data.empty:
            EGID = input_data["EGID"].iloc[0]
            image_path_cadastral = Path(f"buildings/{EGID}/cadastral_{EGID}_0.png")
            image_path_zh_map = Path(f"buildings/{EGID}/zh_map.png")
            image_path_zh_map_ortho = Path(f"buildings/{EGID}/zh_map_ortho.png")

        with col6:
            st.markdown("#### Interaktive Satellitenansicht")
            if lat is None or lon is None:
                st.info("Keine Koordinaten für die Satellitenansicht verfügbar.")
            else:
                show_satellite_embed(lat, lon)

        with col7:
            st.markdown("#### ZH-Karte Orthofoto Ausschnitt")
            if image_path_zh_map_ortho and image_path_zh_map_ortho.exists():
                st.image(str(image_path_zh_map_ortho), width="content")
            else:
                st.warning("Kein ZH-Karte Orthofoto Bild")

        with col8:
            st.markdown("#### Katasterplan Ausschnitte")
            if image_path_cadastral and image_path_cadastral.exists():
                st.image(str(image_path_cadastral), width="content", caption="GeoAdmin")
            else:
                st.warning("Kein Katasterplan Bild")

        with col9:
            if input_data is not None and not input_data.empty and "ZH_MAP_URL" in input_data.columns:
                zh_map_url = input_data["ZH_MAP_URL"].iloc[0]
                st.link_button("🗺️ Geoportal Kanton Zürich", zh_map_url)

            if image_path_zh_map and image_path_zh_map.exists():
                st.image(str(image_path_zh_map), width="content", caption="ZH-Karte")
            else:
                st.warning("Kein ZH-Karte Bild")
    col10 = st.columns(1)[0]
    with col10:

        with st.spinner("Analyse der Einschätzung..."):
            if "analysis_result" not in st.session_state:
                analysis_service = OpenAIAnalysisService(api_key=None)
                predictions = [item["Einschätzung"] for item in st.session_state["prediction_result"]]
                st.session_state["analysis_result"] = analysis_service.analyze(
                    st.session_state["input_data"], predictions
                )

            analysis = st.session_state["analysis_result"]
            st.markdown("#### Einschätzung")
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
