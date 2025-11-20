# Address PDF Generator

This project generates a PDF document for each address provided in an Excel file. Each PDF includes a Google Maps Street View image (if available), a map from the Swiss geo.admin.ch service, and a bird's eye view image.

## Project Structure

```
address-pdf-generator
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

- To generate PDFs for addresses in `addresses.xlsx`, run:
  ```
  python src/main.py addresses.xlsx
  ```

## Contributing

Feel free to submit issues or pull requests for improvements or bug fixes.