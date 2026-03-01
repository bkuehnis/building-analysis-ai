import requests
from typing import Optional, Tuple, Dict, Any
import re
import html as html_lib


class GeoAdminService:

    BASE_SEARCH_URL = "https://api3.geo.admin.ch/rest/services/api/SearchServer"
    BASE_IDENTIFY_URL = "https://api3.geo.admin.ch/rest/services/api/MapServer"
    BASE = "https://api3.geo.admin.ch/rest/services/swisstopo/MapServer/ch.bfs.gebaeude_wohnungs_register"

    def __init__(self, sr: int = 2056, lang: str = "de"):
        self.sr = sr
        self.lang = lang
    
    # ---------------------------------------------------------
    # Helper functions
    # ---------------------------------------------------------

    @staticmethod
    def strip_html(s: str) -> str:
        return re.sub(r"<[^>]+>", "", s or "")

    @staticmethod
    def parse_user_address(s: str) -> dict:
        s = s.strip()
        s = re.sub(r"[,\s]+", " ", s)

        m = re.match(r"^(.*?)\s+(\d+)\s*([A-Za-z]?)\s+(\d{4})\s+(.+)$", s)
        if not m:
            return {"street": None, "nr": None, "suffix": None, "plz": None, "city": None}

        return {
            "street": m.group(1).strip().lower(),
            "nr": m.group(2).strip(),
            "suffix": (m.group(3) or "").strip().lower() or None,
            "plz": m.group(4).strip(),
            "city": m.group(5).strip().lower(),
        }

    # ---------------------------------------------------------
    # 1️⃣ Validate Address
    # ---------------------------------------------------------
    def validate_address(self, address: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        params = {
            "searchText": address,
            "type": "locations",
            "origins": "address",
            "lang": self.lang,
            "sr": self.sr,
        }

        r = requests.get(self.BASE_SEARCH_URL, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()

        results = data.get("results", [])
        if not results:
            return False, None

        want = self.parse_user_address(address)

        for hit in results:
            attrs = hit.get("attrs", {})
            if attrs.get("origin") != "address":
                continue

            label = self.strip_html(attrs.get("label", ""))
            got = self.parse_user_address(label)

            if (
                got["street"] == want["street"]
                and got["nr"] == want["nr"]
                and (got["suffix"] or None) == (want["suffix"] or None)
                and got["plz"] == want["plz"]
                and got["city"] == want["city"]
            ):
                return True, hit

        return False, None

    # ---------------------------------------------------------
    # 2️⃣ Geocode Address
    # ---------------------------------------------------------
    def geocode_address(self, address: str) -> Tuple[float, float, Optional[str], float, float]:
        """
        Returns:
        lon, lat (WGS84)
        feature_id (building id if available)
        x, y (LV95 coordinates)
        """

        params = {
            "searchText": address,
            "type": "locations",
            "origins": "address",
            "lang": self.lang,
            "sr": self.sr,
        }

        r = requests.get(self.BASE_SEARCH_URL, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()

        results = data.get("results", [])
        if not results:
            raise ValueError("Address not found")

        attrs = results[0]["attrs"]

        x = attrs.get("x")
        y = attrs.get("y")
        lon = attrs.get("lon")
        lat = attrs.get("lat")
        feature_id = attrs.get("featureId")

        return lon, lat, feature_id, x, y

    # ---------------------------------------------------------
    # 3️⃣ Fetch GWR Register Data
    # ---------------------------------------------------------
    def fetch_gwr_register_data(self, feature_id: str) -> Dict[str, Any]:
        """
        Fetch building register attributes
        """

        url = f"{self.BASE_IDENTIFY_URL}/ch.bfs.gebaeude_wohnungs_register/{feature_id}"
        r = requests.get(url, timeout=20)
        r.raise_for_status()

        data = r.json()

        # Extract attribute block safely
        attrs = {}
        if isinstance(data, dict):
            if "feature" in data:
                attrs = data["feature"].get("attributes", {})
            elif "attributes" in data:
                attrs = data["attributes"]

        return attrs

    # ---------------------------------------------------------
    # 4️⃣ Extract minimal structured building data
    # ---------------------------------------------------------
    @staticmethod
    def extract_gwr_minimal(attrs: dict) -> dict:
    # attrs sind bei dir bereits so keys wie: egid, strname_deinr, ggdename, dplz4, gstat, gkat, gbauj
        egid = attrs.get("egid")
        kreis = attrs.get("lgbkr")
        baujahr = attrs.get("gbauj")
        geb_status_code = attrs.get("gstat")
        geb_kategorie_code = attrs.get("gkat")

        # Adresse aus vorhandenen Feldern bauen
        line1 = attrs.get("strname_deinr")  # z.B. "Steinackerweg 16"
        plz = attrs.get("dplz4")            # z.B. 8488
        ort = attrs.get("ggdename") or attrs.get("dplzname")  # "Turbenthal"
        address = ", ".join([p for p in [line1, f"{plz} {ort}".strip()] if p])

        return {
            "EGID": egid,
            "ADDRESS": address,
            "STADTKREIS": kreis,
            "BAUJAHR": baujahr,
        }

    
    # ---------------------------------------------------------
    # 5️⃣ Fetch and parse extended HTML popup for more details
    # ---------------------------------------------------------

    def fetch_extended_popup_html(self, feature_id: str, lang: str = "de") -> str:
        url = f"{self.BASE}/{feature_id}/extendedHtmlPopup"
        r = requests.get(url, params={"lang": lang}, timeout=30)
        r.raise_for_status()
        return r.text

    @staticmethod
    def parse_popup_value(html: str, label: str) -> Optional[str]:
        # HTML entities decodieren (&uuml; etc.)
        html = html_lib.unescape(html)

        pattern = rf"{re.escape(label)}\s*</td>\s*<td[^>]*>\s*([^<]+?)\s*<"
        m = re.search(pattern, html, flags=re.IGNORECASE)
        return m.group(1).strip() if m else None

    def extract_texts_from_popup(self, html: str) -> dict:
        return {
            "GSW_STATUS": self.parse_popup_value(html, "Gebäudestatus"),
            "HAUPTNUTZUNG": self.parse_popup_value(html, "Gebäudekategorie"),
            "NUTZUNG": self.parse_popup_value(html, "Gebäudeklasse"),
        }

    def fetch_gwr_popup_texts(self, feature_id: str, lang: str = "de") -> dict:
        html = self.fetch_extended_popup_html(feature_id, lang=lang)
        return self.extract_texts_from_popup(html)
    
    # ---------------------------------------------------------
    # 6️⃣ Convenience full pipeline
    # ---------------------------------------------------------
    def collect_building_data(self, address: str) -> Dict[str, Any]:
        """
        Full pipeline:
        validate → geocode → gwr fetch → minimal extract
        """

        is_valid, hit = self.validate_address(address)
        if not is_valid:
            raise ValueError("Address not found in geo.admin")

        attrs_hit = hit["attrs"]

        lon = attrs_hit.get("lon")
        lat = attrs_hit.get("lat")
        x = attrs_hit.get("x")
        y = attrs_hit.get("y")
        feature_id = attrs_hit.get("featureId")

        gwr_attrs = self.fetch_gwr_register_data(feature_id)
        base = self.extract_gwr_minimal(gwr_attrs)

        # Popup Texte ergänzen
        popup_html = self.fetch_extended_popup_html(feature_id)
        base.update(self.extract_texts_from_popup(popup_html))

        base.update({
            "lon": lon,
            "lat": lat,
            "x": x,
            "y": y,
            "feature_id": feature_id,
        })

        return base