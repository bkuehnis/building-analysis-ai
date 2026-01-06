#!/usr/bin/env python3
"""
Transform HTML datasheet files to JSON format
Reads datasheet.html and creates datasheet.json for each building
"""

import json
from pathlib import Path
from bs4 import BeautifulSoup

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data/werk"


def parse_html_datasheet(html_file: Path) -> dict:
    """
    Parse HTML datasheet and extract data into a dictionary
    HTML format: table with rows containing header (thick) and value cells
    """
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find the table
        table = soup.find('table')
        if not table:
            print(f"    No table found in {html_file}")
            return {}
        
        # Extract rows
        data = {}
        rows = table.find_all('tr')
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 2:
                # First cell is the header (key)
                header_cell = cells[0]
                value_cell = cells[1]
                
                # Extract text from cells
                key = header_cell.get_text(strip=True)
                value = value_cell.get_text(strip=True)
                
                # Add to data dictionary
                if key:
                    data[key] = value
        
        return data
    
    except Exception as e:
        print(f"    Error parsing {html_file}: {e}")
        return {}


def transform_building_datasheet(building_id: str) -> bool:
    """
    Transform datasheet.html to datasheet.json for a building
    """
    building_dir = DATA_DIR / building_id
    html_file = building_dir / "datasheet.html"
    json_file = building_dir / "datasheet.json"
    
    if not html_file.exists():
        print(f"  ✗ HTML file not found: {html_file}")
        return False
    
    try:
        print(f"  Transforming datasheet.html to datasheet.json")
        
        # Parse HTML
        data = parse_html_datasheet(html_file)
        
        if not data:
            print(f"    ✗ No data extracted from HTML")
            return False
        
        # Save to JSON
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Saved to {json_file}")
        return True
    
    except Exception as e:
        print(f"  ✗ Error transforming datasheet: {e}")
        return False


def main():
    """
    Transform all building datasheets from HTML to JSON
    """
    print("=" * 60)
    print("TRANSFORM HTML DATASHEETS TO JSON")
    print("=" * 60)
    
    # Find all building directories
    building_dirs = [d for d in DATA_DIR.iterdir() if d.is_dir()]
    
    if not building_dirs:
        print("No building directories found")
        return
    
    building_ids = sorted([d.name for d in building_dirs])
    
    print(f"Found {len(building_ids)} buildings\n")
    
    success_count = 0
    
    for building_id in building_ids:
        print(f"Processing building ID: {building_id}")
        
        if transform_building_datasheet(building_id):
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"COMPLETED: {success_count}/{len(building_ids)} datasheets transformed")
    print("=" * 60)


if __name__ == "__main__":
    main()
