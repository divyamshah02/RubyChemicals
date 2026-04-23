from PyPDF2 import PdfReader, PdfWriter

def normalize_pdf(input_path, output_path):
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for page in reader.pages:
        rotation = page.get("/Rotate")

        if rotation:
            page.rotate(-rotation)  # remove rotation metadata

        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)


normalize_pdf(
    r"C:\Users\Divyam Shah\Downloads\CHALLAN FOR SOFTWARE.pdf",
    "fixed_template.pdf"
)