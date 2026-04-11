# Project organisation

## Project Goal

The goal is to develop a prototype system that predicts building characteristics based on:
- Tabular data (e.g. construction year)
- Image data (e.g. facade photos)

## Features

- Data extraction from Excel and GeoAdmin
- Image-based feature extraction using AI (openai pot. CV)
- Machine learning models (so far CatBoost, Random Forest)
- Prediction service with confidence scores

## Data Sources

- GeoAdmin (Swiss geodata)
- Building registry data (EGID-based)
- Street View images (Google API)

## Git Repository branch: feature/ml-pipeline
https://github.com/bkuehnis/dff_architectur/tree/feature/ml-pipeline/prediction_model

## Kanbanboard for time and activity management
https://stubrainst.atlassian.net/jira/software/projects/PM/boards/2

##  rough goal table
![alt text](goalTimeTable.png)

# Project Structure
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
# 🚀 Project Setup

# ⚠️ Important

This project requires:

**Python 3.14**

**scikit-learn==1.6.1**

On Windows, this combination fails to build from source.

➡️ Therefore, you must use WSL (Ubuntu).

## 1. Install WSL (Ubuntu)

**In PowerShell:**
```
wsl --install -d Ubuntu
```

Restart your computer if prompted.

## 2. Setup Ubuntu

**Open Ubuntu and run:**
```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y build-essential git curl libnss3 libasound2t64
```
## 3. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```
Verify installation:

```bash
uv --version
```
## 4. Clone Project inside WSL

```bash
git clone <repository-url>
cd dff_architectur
```

**OR** if you use VSC ➡️ connect to WSL and clone Git Repository

## 5. Create Virtual Environment & Install Dependencies

```bash
uv venv --python 3.14
source .venv/bin/activate
uv sync
```

## 7. Configure Environment Variables

```bash
cp .env.example .env
```
Edit .env:

```env
API_KEY_GOOGLE_MAPS=your_google_maps_key
OPENAI_API_KEY=your_openai_api_key
```