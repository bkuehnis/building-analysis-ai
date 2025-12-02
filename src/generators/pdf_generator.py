from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import os


class PDFGenerator:
    def __init__(self, output_dir="output/pdfs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_pdf(self, address, street_view_image_path, map_image_paths, urls):
        """Generate a single-page PDF for an address with images and URLs"""
        
        # Create safe filename
        safe_address = address.replace("/", "-").replace(" ", "_")
        pdf_filename = f"{self.output_dir}/{safe_address}.pdf"
        
        c = canvas.Canvas(pdf_filename, pagesize=A4)
        width, height = A4
        
        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, f"Address: {address}")
        
        # Layout: 2 rows of 2 images each (larger images)
        img_width = 250
        img_height = 180
        x_margin = 50
        y_start = height - 100
        x_spacing = 20
        y_spacing = 30
        
        y_position = y_start
        
        # Row 1: Street View images
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x_margin, y_position, "Street View (API)")
        c.drawString(x_margin + img_width + x_spacing, y_position, "Street View (Interactive)")
        y_position -= 15
        
        # Draw Street View API image
        if street_view_image_path and os.path.exists(street_view_image_path):
            img = ImageReader(street_view_image_path)
            c.drawImage(img, x_margin, y_position - img_height, width=img_width, height=img_height, preserveAspectRatio=True)
        
        # Draw Street View Interactive screenshot
        if 'streetview-interactive' in map_image_paths and os.path.exists(map_image_paths['streetview-interactive']):
            img = ImageReader(map_image_paths['streetview-interactive'])
            c.drawImage(img, x_margin + img_width + x_spacing, y_position - img_height, width=img_width, height=img_height, preserveAspectRatio=True)
        
        y_position -= (img_height + y_spacing + 10)
        
        # Row 2: Zürich maps
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x_margin, y_position, "Zürich Map")
        c.drawString(x_margin + img_width + x_spacing, y_position, "Zürich Ortho Map")
        y_position -= 15
        
        # Draw ZH map
        if 'zh-map' in map_image_paths and os.path.exists(map_image_paths['zh-map']):
            img = ImageReader(map_image_paths['zh-map'])
            c.drawImage(img, x_margin, y_position - img_height, width=img_width, height=img_height, preserveAspectRatio=True)
        
        # Draw ZH ortho map
        if 'zh-map-ortho' in map_image_paths and os.path.exists(map_image_paths['zh-map-ortho']):
            img = ImageReader(map_image_paths['zh-map-ortho'])
            c.drawImage(img, x_margin + img_width + x_spacing, y_position - img_height, width=img_width, height=img_height, preserveAspectRatio=True)
        
        y_position -= (img_height + y_spacing + 10)
        
        # Swiss Topo Map (small, on left side with URLs)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x_margin, y_position, "Swiss Topo Map")
        y_position -= 15
        
        if 'swisstlm3d-karte-farbe' in map_image_paths and os.path.exists(map_image_paths['swisstlm3d-karte-farbe']):
            small_img_width = 150
            small_img_height = 120
            img = ImageReader(map_image_paths['swisstlm3d-karte-farbe'])
            c.drawImage(img, x_margin, y_position - small_img_height, width=small_img_width, height=small_img_height, preserveAspectRatio=True)
        
        # URLs Section (next to Swiss Topo Map)
        url_x = x_margin + 170
        url_y = y_position - 10
        
        c.setFont("Helvetica-Bold", 12)
        c.drawString(url_x, url_y, "Links:")
        url_y -= 20
        
        c.setFont("Helvetica", 9)
        
        # Google Maps
        c.setFillColorRGB(0, 0, 1)
        c.drawString(url_x + 20, url_y, "Google Maps")
        c.linkURL(urls['maps_url'], (url_x + 20, url_y - 2, url_x + 90, url_y + 10), relative=0)
        c.setFillColorRGB(0, 0, 0)
        url_y -= 15
        
        # Street View
        c.setFillColorRGB(0, 0, 1)
        c.drawString(url_x + 20, url_y, "Google Street View")
        c.linkURL(urls['streetview_url'], (url_x + 20, url_y - 2, url_x + 110, url_y + 10), relative=0)
        c.setFillColorRGB(0, 0, 0)
        url_y -= 15
        
        # Gebäude Register
        c.setFillColorRGB(0, 0, 1)
        c.drawString(url_x + 20, url_y, "Gebäude Register")
        c.linkURL(urls['geo_admin_register_url'], (url_x + 20, url_y - 2, url_x + 110, url_y + 10), relative=0)
        c.setFillColorRGB(0, 0, 0)
        url_y -= 15
        
        # Zürich Map
        c.setFillColorRGB(0, 0, 1)
        c.drawString(url_x + 20, url_y, "Kanton Zürich Map")
        c.linkURL(urls['zh_map_url'], (url_x + 20, url_y - 2, url_x + 120, url_y + 10), relative=0)
        c.setFillColorRGB(0, 0, 0)
        
        # Save PDF
        c.save()
        print(f"PDF generated: {pdf_filename}")
        return pdf_filename