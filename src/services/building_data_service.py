import requests
from bs4 import BeautifulSoup


class BuildingDataService:
    def __init__(self):
        self.base_url = "https://api3.geo.admin.ch/rest/services/ech/MapServer/ch.bfs.gebaeude_wohnungs_register"
    
    def fetch_building_data(self, egid):
        """Fetch detailed building data from geo.admin API
        
        Args:
            egid: Building EGID
            
        Returns:
            dict: Parsed building data
        """
        url = f"{self.base_url}/{egid}_0/extendedHtmlPopup?lang=de"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all table rows
            data = {}
            current_section = None
            
            table = soup.find('table')
            if table:
                for row in table.find_all('tr'):
                    cells = row.find_all('td')
                    
                    # Check if it's a header row
                    th = row.find('th')
                    if th:
                        current_section = th.get_text(strip=True)
                        if current_section not in data:
                            data[current_section] = {}
                        continue
                    
                    # Parse data rows
                    if len(cells) == 2 and current_section:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        data[current_section][key] = value
            
            return data
            
        except Exception as e:
            print(f"Error fetching building data for EGID {egid}: {e}")
            return {}