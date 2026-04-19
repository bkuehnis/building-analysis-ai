# Building Attribute Prediction System

## 📌 Project Overview

This project aims to develop a prototype system that predicts building characteristics using:

Tabular data (e.g., construction year, registry data)
Image data (e.g., facade / street view images)

The system combines machine learning models with AI-based image analysis to infer building attributes such as:

Facade type
Roof type
Windows
Hazardous materials (Schadstoff)

## Features

- Data extraction from Excel and GeoAdmin
- Integration with Swiss geodata (GeoAdmin)
- Image retrieval via Google Street View API
- AI-based image feature extraction (OpenAI)
- Machine Learning models (CatBoost, Random Forest)
- Combined prediction pipeline
- Confidence-based predictions

## Project Structure
```
dff_architectur/
│
├── prediction_model/              # Project Base
│   ├── data/                      # Model datasets
│   │   ├── collected_building_data.xlsx
│   │   └── model_dataset.xlsx
│   │
│   ├── models/                    # Trained models per attribute
|   |   ├── 1_error_analysis/             
│   │   ├── fassade_bekleidung/
│   │   ├── dach_bekleidung/
│   │   ├── fenster/
│   │   ├── schadstoff/
│   │   └── ...
│   │
|   ├── output/
|   |   └── images/...
|   |   
|   ├── services/                      # Core logic & pipelines
|   │   ├── building_image_service.py
|   │   ├── cb_prediction_service.py
|   │   ├── combined_prediction_service.py
|   │   ├── geo_admin_service.py
|   │   ├── openai_analysis_service.py
|   │   ├── openai_feature_service.py
|   │   ├── rf_prediction_service.py
│   |
|   ├── collect_building_data.py
|   ├── generate_model_dataset.py
|   ├── model_dataset_analysis.py
|   ├── MyApp.py
|   ├── ReadMe.md
│   └──...
|
├── pyproject.toml
├── requirements.txt
├── .env.example
└── README.md       # read me main branch
```

## Data Sources

- GeoAdmin (Swiss geodata)
- Building registry data (EGID-based)
- Street View images (Google API)

## Project Setup

## **⚠️ Important ⚠️**

This project requires:

- Python 3.14
- scikit-learn==1.6.1

On Windows, this combination fails to build from source.

➡️ Therefore, you must use WSL (Ubuntu).

### 1. Install WSL (Ubuntu)

**In PowerShell:**
```
wsl --install -d Ubuntu
```

Restart your computer if prompted.

### 2. Setup Ubuntu

**Open Ubuntu and run:**
```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y build-essential git curl libnss3 libasound2t64
```
### 3. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```
Verify installation:

```bash
uv --version
```
### 4. Clone Project inside WSL

```bash
git clone <repository-url>
cd dff_architectur
```

**OR** if you use VSC ➡️ connect to WSL and clone Git Repository

### 5. Create Virtual Environment & Install Dependencies

```bash
uv venv --python 3.14
source .venv/bin/activate
uv sync
```
### 6. add missing modules
```bash
uv add streamlit
uv add catboost
```

### 6. Configure Environment Variables

```bash
cp .env.example .env
```
Edit .env:

```env
API_KEY_GOOGLE_MAPS=your_google_maps_key
OPENAI_API_KEY=your_openai_api_key
```

### 7. Configure allowed Websites for Google API Key

- go to Google Cloud -> API KEYS -> Credibility
- add websites that allow the use of the API KEY
- is used in MyApp.py for map integration

## Running Predictions

**first activate:** source .venve/bin/activate
**run streamlit interface:** streamlit run prediction_model/MyApp.py

**Predictions are handled via:** prediction_model/services/combined_prediction_service.py

every python script has their own run command noted

### Pipeline Overview
Input: Address
GeoAdmin → retrieve building data
Google API → fetch images
OpenAI → extract visual features
ML models → predict attributes
(comming soon) OpenAI → validate/correct predictions with own prediction

## Development Resources

**Git Repository branch: feature/ml-pipeline**
https://github.com/bkuehnis/dff_architectur/tree/feature/ml-pipeline/prediction_model

**Kanbanboard for time and activity management**
https://stubrainst.atlassian.net/jira/software/projects/PM/boards/2

**rough goal table**
![alt text](goalTimeTable.png)