# DFF Architecture

A modular project for generating PDF documents from building addresses and extracting structured data from Werk-material building datasets.

**Features:**
- Generate PDFs with Street View images, maps, and building data from Swiss government APIs
- Download and organize building data from https://werk-material.crb.ch/
- Extract structured fields from building datasheets using OpenAI
- MCP server for accessing building data
- Reusable data pipelines for future ML projects

## Project Structure

```
dff_architectur/
├── data/                              # All data (input/output)
│   ├── raw/                           # External data sources
│   │   └── 251118 Textbeschreibung... # Source Excel files
│   ├── werk/                          # Downloaded werk-material data
│   │   ├── {building_id}/
│   │   │   ├── datasheet.json
│   │   │   ├── datasheet.html
│   │   │   ├── metadata.json
│   │   │   └── images/
│   │   └── ...
│   └── external/                      # Reference data
│
├── src/                               # Source code
│   ├── core/                          # Shared utilities
│   │   ├── __init__.py
│   │   └── config.py                  # Centralized configuration
│   │
│   ├── pipelines/                     # Reusable data pipelines
│   │   ├── werk/
│   │   │   ├── __init__.py
│   │   │   ├── download.py            # Download from werk-material.crb.ch
│   │   │   ├── parser.py              # Parse HTML to JSON
│   │   │   └── extractor.py           # Extract fields with OpenAI
│   │   └── buildings/
│   │       └── ...
│   │
│   ├── services/                      # External API clients
│   │   ├── geocoding_service.py
│   │   ├── streetview_service.py
│   │   ├── map_service.py
│   │   ├── zh_map_service.py
│   │   └── building_data_service.py
│   │
│   ├── generators/                    # Output generators
│   │   └── pdf_generator.py           # PDF generation
│   │
│   ├── models/                        # Data models (future ML)
│   │   └── __init__.py
│   │
│   └── utils/                         # Helpers
│       └── config.py
│
├── scripts/                           # CLI entry points
│   ├── download_werk.py               # Download building data
│   ├── extract_fields.py              # Extract with OpenAI
│   ├── compare_truth.py               # Compare to truth data
│   ├── mcp_server.py                  # Start MCP server
│   └── generate_pdfs.py               # Generate PDFs
│
├── notebooks/                         # Jupyter notebooks (analysis, exploration)
│
├── tests/                             # Unit tests
│
├── output/                            # Generated outputs
│   ├── pdfs/
│   ├── images/
│   └── task4_openai/                  # OpenAI extraction results
│
├── pyproject.toml
├── requirements.txt
├── .env.example
└── README.md
```

## Setup Instructions (uv)

1. **Clone the repository:**
  ```bash
  git clone <repository-url>
  cd dff_architectur
  ```

2. **Create the uv environment and install dependencies:**
  ```bash
  uv venv --python 3.14
  uv sync
  ```

3. **Configure environment variables:**
  ```bash
  cp .env.example .env
  # Edit .env with your API keys:
  # - API_KEY_GOOGLE_MAPS
  # - OPENAI_API_KEY
  ```

Notes:
- Dependencies are now defined in pyproject.toml for uv.
- requirements.txt is no longer the source of truth.

## Usage

### Generate PDFs from Address List

```bash
python scripts/generate_pdfs.py
```
- Reads addresses from Excel file (configured in script)
- Fetches maps, Street View, and building data
- Generates PDFs in `output/pdfs/`

### Download Werk-Material Data

```bash
# First time: authenticate and save session
python scripts/download_werk.py --login

# Download data
python scripts/download_werk.py
```
- Downloads datasheets, metadata, and images
- Saves to `data/werk/{building_id}/`

### Parse HTML Datasheets to JSON

```bash
from src.pipelines.werk.parser import main
main()
```
- Converts `datasheet.html` → `datasheet.json` for all buildings

### Extract Structured Fields with OpenAI

```bash
# Extract from single building
python scripts/extract_fields.py --id 57403

# Extract from all buildings
python scripts/extract_fields.py --all

# Dry-run (preview without API calls)
python scripts/extract_fields.py --all --dry-run
```
- Uses OpenAI gpt-4 vision to extract fields
- Supports text-only, images-only, and combined modes
- Outputs: `output/task4_openai/{id}_text.json`, `{id}_images.json`, etc.

### Compare Extractions to Ground Truth

```bash
python scripts/compare_truth.py --dry-run
```
- Compares AI extractions vs. Excel truth values
- Calculates similarity scores
- Outputs CSV: `output/task4_openai/comparison.csv`

### Start MCP Server

```bash
python scripts/mcp_server.py [port]
```
- Starts FastMCP server (default port 8000)
- Exposes building data via MCP protocol
- Image server on port 8001

## Architecture Notes

### Separation of Concerns

- **Pipelines** (`src/pipelines/`): Reusable data extraction/transformation logic
  - Can be imported into future ML projects
  - Stateless, composable functions
- **Services** (`src/services/`): External API clients
  - Thin wrappers around APIs
  - Used by scripts for document generation
- **Scripts** (`scripts/`): User-facing CLI entry points
  - Import from pipelines or services
  - Handle argument parsing and orchestration

### Data Flow

```
Excel Data
  ↓
scripts/download_werk.py → data/werk/{id}/ (HTML, metadata, images)
  ↓
src/pipelines/werk/parser.py → datasheet.json
  ↓
src/pipelines/werk/extractor.py (OpenAI) → output/task4_openai/
  ↓
scripts/compare_truth.py → comparison.csv
```

### For Future ML Projects

1. **Reuse pipelines**: Import from `src.pipelines.werk` in ML training scripts
2. **Add models**: Define Pydantic models in `src/models/`
3. **Organize notebooks**: Use `notebooks/` for exploratory analysis
4. **Add tests**: Unit tests in `tests/`

## Environment Variables

Required in `.env`:

```
API_KEY_GOOGLE_MAPS=your-key
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4-turbo  # or gpt-5-nano for testing
```