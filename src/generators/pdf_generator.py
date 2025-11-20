class PDFGenerator:
    def __init__(self):
        pass

    def generate_pdf(self, address, street_view_image, map_image, birdseye_image):
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        pdf_filename = f"{address.replace(' ', '_')}.pdf"
        c = canvas.Canvas(pdf_filename, pagesize=letter)
        width, height = letter

        # Add Street View Image
        if street_view_image:
            c.drawImage(street_view_image, 50, height - 300, width=500, height=250)

        # Add Map Image
        if map_image:
            c.drawImage(map_image, 50, height - 600, width=500, height=250)

        # Add Bird's Eye View Image
        if birdseye_image:
            c.drawImage(birdseye_image, 50, height - 900, width=500, height=250)

        c.drawString(50, height - 50, f"Address: {address}")
        c.save()