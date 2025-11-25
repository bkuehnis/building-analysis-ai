from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os


class PDFGenerator:
    def __init__(self, output_dir="output/pdfs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_pdf(self, address, street_view_image_path, map_image_paths, urls):
        """Generate a single-page PDF for an address with images in 2x2 table and URLs
        
        Args:
            address: Street address
            street_view_image_path: Path to street view image
            map_image_paths: Dictionary with map type as key and image path as value
            urls: Dictionary with URL links
        """
        
        # Create safe filename
        safe_address = address.replace("/", "-").replace(" ", "_")
        pdf_filename = f"{self.output_dir}/{safe_address}.pdf"
        
        c = canvas.Canvas(pdf_filename, pagesize=A4)
        width, height = A4
        
        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, f"Address: {address}")
        
        # 2x2 Grid layout for images
        img_width = 250
        img_height = 200
        x_margin = 50
        y_start = height - 100
        x_spacing = 20
        y_spacing = 30
        
        # Collect all images
        images = []
        
        # Add street view
        if street_view_image_path and os.path.exists(street_view_image_path):
            images.append(("Street View", street_view_image_path))
        
        # Add maps
        for map_type, map_image_path in map_image_paths.items():
            if map_image_path and os.path.exists(map_image_path):
                images.append((f"Map ({map_type})", map_image_path))
        
        # Draw images in 2x2 grid
        positions = [
            (x_margin, y_start - img_height),  # Top left
            (x_margin + img_width + x_spacing, y_start - img_height),  # Top right
            (x_margin, y_start - 2 * img_height - y_spacing),  # Bottom left
            (x_margin + img_width + x_spacing, y_start - 2 * img_height - y_spacing)  # Bottom right
        ]
        
        for i, (label, img_path) in enumerate(images[:4]):  # Max 4 images
            if i < len(positions):
                x, y = positions[i]
                
                # Draw label
                c.setFont("Helvetica-Bold", 10)
                c.drawString(x, y + img_height + 15, label)
                
                # Draw image
                img = ImageReader(img_path)
                c.drawImage(img, x, y, width=img_width, height=img_height, preserveAspectRatio=True)
        
        # URLs Section below the grid
        y_position = y_start - 2 * img_height - 2 * y_spacing - 40
        
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_position, "Links:")
        y_position -= 20
        
        c.setFont("Helvetica", 9)
        
        # Google Maps
        c.setFillColorRGB(0, 0, 1)  # Blue color for links
        c.drawString(70, y_position, "Google Maps")
        c.linkURL(urls['maps_url'], (70, y_position - 2, 140, y_position + 10), relative=0)
        c.setFillColorRGB(0, 0, 0)  # Reset to black
        y_position -= 15
        
        # Street View
        c.setFillColorRGB(0, 0, 1)
        c.drawString(70, y_position, "Google Street View")
        c.linkURL(urls['streetview_url'], (70, y_position - 2, 160, y_position + 10), relative=0)
        c.setFillColorRGB(0, 0, 0)
        y_position -= 15
        
        # Gebäude Register
        c.setFillColorRGB(0, 0, 1)
        c.drawString(70, y_position, "Gebäude Register (geo.admin.ch)")
        c.linkURL(urls['geo_admin_register_url'], (70, y_position - 2, 240, y_position + 10), relative=0)
        c.setFillColorRGB(0, 0, 0)
        
        # Save PDF
        c.save()
        print(f"PDF generated: {pdf_filename}")
        return pdf_filename