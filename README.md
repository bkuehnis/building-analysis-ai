# DFF Architecture

This project generates a PDF document for each address provided in an Excel file. Each PDF includes a Google Maps Street View image (if available), a map from the Swiss geo.admin.ch service, and a bird's eye view image.

In addition it collects the data from https://werk-material.crb.ch/ and saves them locally (see ./werk). This part also has a mcp server to expose the data to a mcp client.

## Project Structure

```
DFF_ARCHITECTURE
├── src
│   ├── main.py                # Entry point of the application
│   ├── services               # Contains services for fetching images
│   │   ├── streetview_service.py  # Service for Google Maps Street View
│   │   ├── map_service.py         # Service for geo.admin.ch maps
│   │   └── birdseye_service.py    # Service for bird's eye view images
│   ├── generators              # Contains PDF generation logic
│   │   └── pdf_generator.py    # PDF generation class
│   └── utils                  # Utility functions and configurations
│       └── config.py          # Configuration settings and API keys
├── werk                      # Scripts and data pipelines for Werk-material extraction
│   ├── .auth_state.json       # Saved Playwright authentication state
│   ├── compare_truth.py       # Compare extractions to ground truth
│   ├── download_buildings.py  # Downloads Werk-material datasets
│   ├── download.md           # Task notes for Werk-material pipeline
│   ├── image_analysis.py      # Experimenting with OpenAI image inputs
│   ├── mcp_server.py          # FastMCP server exposing Werk data
│   ├── openai_compare_werk.py # Runs Task 4/5/6 extractions and comparisons
│   └── transform_datasheet.py # Converts datasheet.html into datasheet.json
├── requirements.txt           # Project dependencies
├── .env.example               # Example environment variables
└── README.md                  # Project documentation
```

## Setup Instructions

1. **Clone the repository:**
   ```
   git clone <repository-url>
   cd address-pdf-generator
   ```

2. **Create a virtual environment:**
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   - Copy `.env.example` to `.env` and fill in the required API keys and settings.

## Usage

1. Prepare an Excel file containing the addresses you want to process.
2. Run the application:
   ```
   python src/main.py <path-to-excel-file>
   ```
3. The generated PDFs will be saved in the specified output directory.

## Examples

- To generate PDFs for addresses change the excel referenced in src/main.py
  ```
  python src/main.py
  ```