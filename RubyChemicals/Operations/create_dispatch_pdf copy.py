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
    items  # list of dicts: [{sr, name, hsn, qty}]
):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    
    # ---- HEADER FIELDS ----
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

    # ---- ITEMS TABLE ----
    y = 388
    for item in items:
        can.drawString(35, y, str(item["sr"]))
        can.drawString(57, y, item["name"])
        can.drawString(220, y, item["hsn"])
        can.drawString(292, y, str(item["qty"]))
        y -= 12  # move down row


    # ---- HEADER FIELDS ----
    can.setFont("Helvetica", 10) 
    can.drawString(42+406, 506, company_name)
    # can.drawString(308+246, 506, str(challan_no))
    can.saveState()
    # can.rotate(180)  
    # can.drawRightString(250, 106, str(challan_no))
    can.drawRightString(650, 506, str(challan_no))
    # can.drawString(550, 710, "shngbri eoasbghrueab grueab hguroeba hguroeba shngbri eoasbghrueab grueab hguroeba hguroeba shngbri eoasbghrueab grueab hguroeba hguroeba shngbri eoasbghrueab grueab hguroeba hguroeba shngbri eoasbghrueab grueab hguroeba hguroeba shngbri eoasbghrueab grueab hguroeba hguroeba shngbri eoasbghrueab grueab hguroeba hguroeba shngbri eoasbghrueab grueab hguroeba hguroeba shngbri eoasbghrueab grueab hguroeba hguroeba shngbri eoasbghrueab grueab hguroeba hguroeba shngbri eoasbghrueab grueab hguroeba hguroeba shngbri eoasbghrueab grueab hguroeba hguroeba shngbri eoasbghrueab grueab hguroeba hguroeba ")
    # can.line(0, 506, 612, 506)   # horizontal guide
    # can.line(580, 0, 580, 792)   # right boundary marker
    # can.restoreState()
    can.drawString(70+406, 478, address)
    can.drawString(278+406, 478, date)
    can.drawString(308+206, 450, vehicle_no)

    can.setFont("Helvetica", 8) 
    can.drawString(55+406, 423, gstin)
    can.setFont("Helvetica", 10)     
    can.drawString(172+406, 423, contact_name)
    can.drawString(294+406, 423, contact_number)

    # ---- ITEMS TABLE ----
    y = 388
    for item in items:
        can.drawString(35+406, y, str(item["sr"]))
        can.drawString(57+406, y, item["name"])
        can.drawString(220+406, y, item["hsn"])
        can.drawString(292+406, y, str(item["qty"]))
        y -= 12  # move down row

    can.save()

    packet.seek(0)
    new_pdf = PdfReader(packet)
    existing_pdf = PdfReader(input_pdf_path)
    output = PdfWriter()

    page = existing_pdf.pages[0]
    # page.rotate(90)   # try 90, -90, or 180 depending on your case
    page.merge_page(new_pdf.pages[0])
    output.add_page(page)

    with open(output_pdf_path, "wb") as f:
        output.write(f)


if __name__ == "__main__":
    items = [
        {"sr": 1, "name": "Cement Bag", "hsn": "2523", "qty": 50},
        {"sr": 2, "name": "Sand", "hsn": "2505", "qty": 100},
        {"sr": 3, "name": "Steel Rod", "hsn": "7214", "qty": 30},
    ]

    generate_challan(
        input_pdf_path=r"C:\Users\Divyam Shah\OneDrive\Desktop\Dynamic Labz\Clients\Clients\Ruby Chemicals\RubyChemicals\fixed_template.pdf",
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

    print("Challan generated: output_challan.pdf")