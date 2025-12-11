from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
import os


class PDFGenerator:
    def __init__(self, output_dir="output/pdfs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_pdf(self, address, egid, street_view_image_path, map_image_paths, urls, building_info=None, building_data_api=None):
        """Generate a PDF for an address with images, URLs, and building data"""
        
        # Create safe filename
        safe_address = address.replace("/", "-").replace(" ", "_")
        pdf_filename = f"{self.output_dir}/{safe_address}.pdf"
        
        c = canvas.Canvas(pdf_filename, pagesize=A4)
        width, height = A4
        
        # PAGE 1: Images and basic info
        self._draw_page1(c, width, height, address, egid, street_view_image_path, map_image_paths, urls, building_info)
        
        # PAGE 2: Detailed building data from API
        if building_data_api:
            c.showPage()
            self._draw_page2(c, width, height, address, egid, building_data_api)
        
        # Save PDF
        c.save()
        print(f"PDF generated: {pdf_filename}")
        return pdf_filename
    
    def _draw_page1(self, c, width, height, address, egid, street_view_image_path, map_image_paths, urls, building_info):
        """Draw first page with images"""
        # Title with EGID
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, f"Address: {address} (EGID: {egid})")
        
        # Layout: 2 rows of 2 images each
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
        
        # URLs Section
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
    
    def _draw_page2(self, c, width, height, address, egid, building_data_api):
        margin_top = 50
        margin_bottom = 50
        margin_left = 50
        margin_right = 50

        gutter = 20
        col_width = (width - margin_left - margin_right - gutter) / 2
        left_x = margin_left
        right_x = margin_left + col_width + gutter

        sections_order = [
            ('Gebäudeinformationen', 'left'),
            ('Eingangsinformationen', 'right'),
            ('Wohnungsinformationen', 'right'),
        ]

        left_y = height - margin_top
        right_y = height - margin_top

        header_h = 12          # space reserved for section title line
        after_header_gap = 4   # gap between title and table
        section_gap = 10       # gap after each section

        for section_name, position in sections_order:
            section_data = building_data_api.get(section_name)
            if not isinstance(section_data, dict) or not section_data:
                continue

            table_data = []
            for key, value in section_data.items():
                if value in (None, ''):  # Keep entries with '-' for processing
                    continue
                table_data.append([key, value])

            if not table_data:
                continue

            # Adjust the column width for the left column
            table = Table(table_data, colWidths=[col_width * 0.5, col_width * 0.56])  # Increased left column width
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                ('TOPPADDING', (0, 0), (-1, -1), 1),
                ('LEFTPADDING', (0, 0), (-1, -1), 1),
                ('RIGHTPADDING', (0, 0), (-1, -1), 1),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                [colors.white, colors.HexColor('#f0f0f0')]),
            ]))

            # Choose column
            if position == 'left':
                current_x, current_y = left_x, left_y
            else:
                current_x, current_y = right_x, right_y

            # Compute REAL table height
            available_h = current_y - margin_bottom - header_h - after_header_gap
            _, table_h = table.wrap(col_width, max(0, available_h))

            needed_h = header_h + after_header_gap + table_h

            # New page if it doesn't fit in that column
            if current_y - needed_h < margin_bottom:
                c.showPage()
                left_y = height - margin_top
                right_y = height - margin_top
                current_y = height - margin_top
                current_x = left_x if position == 'left' else right_x

                available_h = current_y - margin_bottom - header_h - after_header_gap
                _, table_h = table.wrap(col_width, max(0, available_h))
                needed_h = header_h + after_header_gap + table_h

            # Draw header
            c.setFont("Helvetica-Bold", 8)
            c.drawString(current_x, current_y, section_name)

            # Draw table under header, using real height
            table_top_y = current_y - header_h - after_header_gap
            table.drawOn(c, current_x, table_top_y - table_h)

            # Update column cursor
            new_y = current_y - needed_h - section_gap
            if position == 'left':
                left_y = new_y
            else:
                right_y = new_y
