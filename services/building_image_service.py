import os
import requests
import urllib.parse
from typing import Tuple
from PIL import Image, ImageDraw


class ImageService:

    WMS_BASE = "https://wms.geo.admin.ch/"

    # ---------------------------------------------------------
    # 1️⃣ Download Image
    # ---------------------------------------------------------
    @staticmethod
    def download_image(url, name, outdir: str = "output/images"):
        os.makedirs(outdir, exist_ok=True)
        filename = os.path.join(outdir, f"{name}.jpeg")

        if os.path.exists(filename):
            return filename

        r = requests.get(url, timeout=30)
        r.raise_for_status()

        ct = r.headers.get("Content-Type", "")
        if "image" not in ct:
            raise ValueError(
                f"URL did not return an image. Content-Type={ct}. "
                f"First 200 bytes: {r.content[:200]!r}"
            )

        with open(filename, "wb") as f:
            f.write(r.content)

        return filename

    # ---------------------------------------------------------
    # 2️⃣ LV03 → LV95 Conversion
    # ---------------------------------------------------------
    @staticmethod
    def ensure_lv95_xy(x: float, y: float) -> tuple[float, float]:
        """
        Returns (E95, N95) from inputs that may be:
        - LV95 but swapped (x=N, y=E)
        - LV95 normal (x=E, y=N)
        - LV03 (x=N, y=E) -> converted to LV95
        """
        if x is None or y is None:
            raise ValueError(f"Invalid coords: x={x}, y={y}")

        # Case: already LV95 but swapped (your example)
        if 1_000_000 < x < 1_500_000 and 2_000_000 < y < 3_000_000:
            return y, x  # (E,N)

        # Case: already LV95 normal
        if 2_000_000 < x < 3_000_000 and 1_000_000 < y < 1_500_000:
            return x, y  # (E,N)

        # Case: LV03 (x=N, y=E)
        if x < 1_000_000 and y < 1_000_000:
            return y + 2_000_000, x + 1_000_000

        raise ValueError(f"Unknown coordinate format: x={x}, y={y}")

    # ---------------------------------------------------------
    # 3️⃣ Build Swissimage WMS URL
    # ---------------------------------------------------------
    @staticmethod
    def build_swissimage_wms_url(
        E: float,
        N: float,
        meters: float = 80,
        width: int = 1024,
        height: int = 1024,
    ) -> str:
        bbox = f"{E-meters},{N-meters},{E+meters},{N+meters}"

        params = {
            "SERVICE": "WMS",
            "REQUEST": "GetMap",
            "VERSION": "1.3.0",
            "LAYERS": "ch.swisstopo.swissimage",
            "STYLES": "",
            "FORMAT": "image/jpeg",
            "CRS": "EPSG:2056",
            "BBOX": bbox,
            "WIDTH": str(width),
            "HEIGHT": str(height),
        }

        return ImageService.WMS_BASE + "?" + urllib.parse.urlencode(params)

    # ---------------------------------------------------------
    # 4️⃣ Draw Center Marker
    # ---------------------------------------------------------
    @staticmethod
    def draw_marker(image_path: str, out_path: str) -> str:
        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)

        w, h = img.size
        cx, cy = w // 2, h // 2

        r = max(8, min(w, h) // 60)

        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline="red", width=4)
        draw.line((cx - 2*r, cy, cx + 2*r, cy), fill="red", width=3)
        draw.line((cx, cy - 2*r, cx, cy + 2*r), fill="red", width=3)

        img.save(out_path, "JPEG", quality=95)
        return out_path