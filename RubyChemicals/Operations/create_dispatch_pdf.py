from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PyPDF2 import PdfReader, PdfWriter
import io


def generate_challan(
    input_pdf_path,
    output_pdf_path,
    company_name,
    challan_no,
    address,
    date,
    vehicle_no,
    gstin,
    contact_name,
    contact_number,
    items
):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)

    # ---------------- NORMAL (NO ROTATION HERE) ----------------

    # LEFT
    can.setFont("Helvetica", 10)
    can.drawString(42, 506, company_name)
    can.drawString(308, 506, str(challan_no))
    can.drawString(70, 478, address)
    can.drawString(278, 478, date)
    can.drawString(308, 450, vehicle_no)

    can.setFont("Helvetica", 8)
    can.drawString(55, 423, gstin)

    can.setFont("Helvetica", 10)
    can.drawString(172, 423, contact_name)
    can.drawString(294, 423, contact_number)

    y = 388
    for item in items:
        can.drawString(35, y, str(item["sr"]))
        can.drawString(57, y, item["name"])
        can.drawString(220, y, item["hsn"])
        can.drawString(292, y, str(item["qty"]))
        y -= 12

    # RIGHT
    OFFSET = 406
    RIGHT_EDGE = 580

    can.setFont("Helvetica", 10)
    can.drawString(42 + OFFSET, 506, company_name)
    can.drawRightString(RIGHT_EDGE, 506, str(challan_no))

    can.drawString(70 + OFFSET, 478, address)
    can.drawString(278 + OFFSET, 478, date)
    can.drawString(308 + OFFSET, 450, vehicle_no)

    can.setFont("Helvetica", 8)
    can.drawString(55 + OFFSET, 423, gstin)

    can.setFont("Helvetica", 10)
    can.drawString(172 + OFFSET, 423, contact_name)
    can.drawString(294 + OFFSET, 423, contact_number)

    y = 388
    for item in items:
        can.drawString(35 + OFFSET, y, str(item["sr"]))
        can.drawString(57 + OFFSET, y, item["name"])
        can.drawString(220 + OFFSET, y, item["hsn"])
        can.drawString(292 + OFFSET, y, str(item["qty"]))
        y -= 12

    can.save()

    # ---------------- MERGE ----------------
    packet.seek(0)
    new_pdf = PdfReader(packet)
    existing_pdf = PdfReader(input_pdf_path)

    output = PdfWriter()
    page = existing_pdf.pages[0]

    # ✅ ROTATE PDF HERE ONLY (NOT canvas)
    page.rotate(90)

    page.merge_page(new_pdf.pages[0])
    output.add_page(page)

    with open(output_pdf_path, "wb") as f:
        output.write(f)
# ---------------- TEST ----------------
if __name__ == "__main__":
    items = [
        {"sr": 1, "name": "Cement Bag", "hsn": "2523", "qty": 50},
        {"sr": 2, "name": "Sand", "hsn": "2505", "qty": 100},
        {"sr": 3, "name": "Steel Rod", "hsn": "7214", "qty": 30},
    ]

    generate_challan(
        input_pdf_path=r"C:\Users\Divyam Shah\Downloads\CHALLAN FOR SOFTWARE.pdf",
        output_pdf_path="output_challan.pdf",
        company_name="Dynamic Labz Pvt Ltd",
        challan_no="CH-00123",
        address="Ahmedabad, Gujarat",
        date="22-04-2026",
        vehicle_no="GJ01AB1234",
        gstin="24ABCDE1234F1Z5",
        contact_name="Divyam",
        contact_number="9876543210",
        items=items
    )

    print("✅ Challan generated successfully")