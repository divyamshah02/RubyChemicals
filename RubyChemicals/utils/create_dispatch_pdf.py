from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO

def format_date(s):
    return f"{s[8:10]}-{s[5:7]}-{s[0:4]}"


def split_text(text, max_len=100):
    words = text.split()
    result = []
    current = ""

    for word in words:
        # If adding this word exceeds limit
        if len(current) + len(word) + (1 if current else 0) > max_len:
            if current:
                result.append(current)
                current = word
            else:
                # Word itself is longer than max_len → force split
                result.append(word[:max_len])
                remaining = word[max_len:]
                while len(remaining) > max_len:
                    result.append(remaining[:max_len])
                    remaining = remaining[max_len:]
                current = remaining
        else:
            current = f"{current} {word}" if current else word

    if current:
        result.append(current)

    return result

def generate_challan(
    input_pdf_path,
    output_pdf_path,
    company_name,
    challan_no,
    address,
    date,
    dispatch_through,
    vehicle_no,
    gstin,
    contact_name,
    contact_number,
    items,  # list of dicts: [{sr, name, hsn, qty}]
    remarks
):
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    
    # ---- HEADER FIELDS ----
    can.setFont("Helvetica", 10) 
    can.drawString(73, 748, str(challan_no))
    can.drawString(440, 748, format_date(date))
    can.drawString(33, 721, company_name)

    # handle address
    address_lst = split_text(address)
    line = 0
    line_y = 694
    for addr in address_lst:
        if line == 2:
            break
        if line == 0:
            can.drawString(63, line_y, addr)            
        else:
            can.drawString(18, line_y, addr)
        line_y -= 27
        line += 1

    # can.drawString(63, 694, address)
    
    
    can.drawString(100, 640, dispatch_through)
    can.drawString(373, 640, vehicle_no)
    
    can.drawString(50, 613, gstin)       
    can.drawString(265, 613, contact_name)
    can.drawString(465, 613, contact_number)


    # ---- ITEMS TABLE ----
    y = 572
    for item in items:
        # can.drawString(35, y, str(item["sr"]))
        can.drawString(67, y, item["name"])
        can.drawString(344, y, item["hsn"])
        can.drawString(443, y, str(item["qty"]))
        y -= 14  # move down row


    remarks_lst = split_text(remarks)
    remarks_line = 0
    remarks_line_y = 420
    for addr in remarks_lst:
        if remarks_line == 3:
            break
        if remarks_line == 0:
            can.drawString(63, remarks_line_y, addr)            
        else:
            can.drawString(18, remarks_line_y, addr)
        remarks_line_y -= 27
        remarks_line += 1


    # can.drawString(63, 420, remarks)

    can.save()


    packet.seek(0)

    new_pdf = PdfReader(packet)
    existing_pdf = PdfReader(input_pdf_path)

    output = PdfWriter()

    page = existing_pdf.pages[0]
    page.merge_page(new_pdf.pages[0])
    output.add_page(page)
    output.add_page(page)

    # 👉 write to memory instead of file
    output_stream = BytesIO()
    output.write(output_stream)
    output_stream.seek(0)

    return output_stream

    packet.seek(0)
    new_pdf = PdfReader(packet)
    existing_pdf = PdfReader(input_pdf_path)
    output = PdfWriter()

    page = existing_pdf.pages[0]
    page.merge_page(new_pdf.pages[0])
    output.add_page(page)
    output.add_page(page)

    with open(output_pdf_path, "wb") as f:
        output.write(f)


if __name__ == "__main__":
    items = [
        {"sr": 1, "name": "Cement Bag", "hsn": "2523", "qty": 50},
        {"sr": 2, "name": "Sand", "hsn": "2505", "qty": 100},
        {"sr": 3, "name": "Steel Rod", "hsn": "7214", "qty": 30},
        {"sr": 1, "name": "Cement Bag", "hsn": "2523", "qty": 50},
        {"sr": 2, "name": "Sand", "hsn": "2505", "qty": 100},
        {"sr": 3, "name": "Steel Rod", "hsn": "7214", "qty": 30},
        {"sr": 1, "name": "Cement Bag", "hsn": "2523", "qty": 50},
        {"sr": 2, "name": "Sand", "hsn": "2505", "qty": 100},
        {"sr": 3, "name": "Steel Rod", "hsn": "7214", "qty": 30},
    ]

    generate_challan(
        input_pdf_path=r"dispatch_template.pdf",
        output_pdf_path="dispatch_output_challan.pdf",
        company_name="Dynamic Labz Pvt Ltd",
        challan_no="CH-00123",
        address="603, siddhi sadhan, paldi, bhattha, Ahmedabad, Gujarat, 1 603, siddhi sadhan, paldi, bhattha, Ahmedabad, Gujarat 2 603, siddhi sadhan, paldi, bhattha, Ahmedabad, Gujarat 3 603, siddhi sadhan, paldi, bhattha, Ahmedabad, Gujarat 4 603, siddhi sadhan, paldi, bhattha, Ahmedabad, Gujarat",
        date="22-04-2026",
        dispatch_through="Truck",
        vehicle_no="GJ01AB1234",
        gstin="24ABCDE1234F1Z5",
        contact_name="Divyam",
        contact_number="9876543210",
        items=items,
        remarks="Loream ipsum is cool but useless just like you. 1 Loream ipsum is cool but useless just like you. 2 Loream ipsum is cool but useless just like you. 3 Loream ipsum is cool but useless just like you. 4 Loream ipsum is cool but useless just like you. 5 Loream ipsum is cool but useless just like you. 6 Loream ipsum is cool but useless just like you."
    )
    
    print("Challan generated: output_challan.pdf")
