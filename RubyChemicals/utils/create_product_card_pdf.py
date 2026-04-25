from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO


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

def generate_production_card(
    input_pdf_path,
    output_pdf_path,
    code,
    product_name,
    date,
    total_output,
    uom,
    total_loss,
    remarks,
    batches,
    raw_materials,
    production_incharge,
    approved_by,
    accounted_by,
):
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    
    # ---- HEADER FIELDS ----
    can.setFont("Helvetica", 10) 
    can.drawString(40, 762, str(code))
    can.drawString(240, 762, product_name)
    can.drawString(477, 762, date)

    can.drawString(57, 735, total_output)
    can.drawString(189, 735, uom)
    can.drawString(473, 735, total_loss)

    # ---- ITEMS TABLE ----
    y = 675
    for item in raw_materials:
        # can.drawString(35, y, str(item["sr"]))
        can.drawString(67, y, item["stock_item_name"])
        can.drawString(384, y, f"{str(item['quantity_used'])} {str(item['stock_item_unit'])}")
        y -= 15  # move down row


    # ---- ITEMS TABLE ----
    y = 326
    for btc_item in batches:
        # can.drawString(35, y, str(btc_item["sr"]))
        can.drawString(67, y, btc_item["product_name"])
        can.drawString(303, y, str(btc_item["batch_code"]))
        can.drawString(443, y, f"{str(btc_item['output_quantity'])} {str(btc_item['product_unit'])}")
        y -= 15  # move down row


    remarks_lst = split_text(remarks)
    remarks_line = 0
    remarks_line_y = 239
    for addr in remarks_lst:
        if remarks_line == 3:
            break
        if remarks_line == 0:
            can.drawString(65, remarks_line_y, addr)            
        else:
            can.drawString(18, remarks_line_y, addr)
        remarks_line_y -= 27
        remarks_line += 1

    if production_incharge is not None:
            can.drawString(133, 158, production_incharge)
    can.drawString(384, 158, date)

    if approved_by is not None:
            can.drawString(85, 131, approved_by)
    
    if accounted_by is not None:
            can.drawString(92, 104, accounted_by)

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
    
     # 👉 write to memory instead of file
    output_stream = BytesIO()
    output.write(output_stream)
    output_stream.seek(0)
    
    return output_stream
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
    data = {
        "product_name": "Test Prod",
        "code": "PRD-1",
        "date": "2026-04-22",
        "batch_count": 3,
        "total_output": "1200",
        "uom": "kg",
        "total_loss": "112",
        "remarks": "Loream ipsum is cool but useless just like you. 1 Loream ipsum is cool but useless just like you. 2 Loream ipsum is cool but useless just like you. 3 Loream ipsum is cool but useless just like you. 4 Loream ipsum is cool but useless just like you. 5 Loream ipsum is cool but useless just like you. 6 Loream ipsum is cool but useless just like you.",
        "batches": [
            {"batch_code": "BTC-1", "product": "Binder Powder", "output": "1200 kg", "loss": "0 kg"},
            {"batch_code": "BTC-2", "product": "Rainproof", "output": "560 kg", "loss": "0 kg"},
            {"batch_code": "BTC-3", "product": "Chemical A", "output": "5 kg", "loss": "0 kg"},
        ],
        "raw_materials": [
            {"stock_item_name": "Test stock item", "quantity": "120 kg"},
            {"stock_item_name": "Waterproof Chemical A", "quantity": "180 kg"},
            {"stock_item_name": "Test stock item", "quantity": "120 kg"},
            {"stock_item_name": "Waterproof Chemical A", "quantity": "180 kg"},
            {"stock_item_name": "Test stock item", "quantity": "120 kg"},
            {"stock_item_name": "Waterproof Chemical A", "quantity": "180 kg"},
        ],
        "production_incharge": "Divyam Shah",
        "approved_by": "Divyam Shah",
        "accounted_by": "Divyam Shah"
    }

    generate_production_card(
        input_pdf_path=r"production_card_template.pdf",
        output_pdf_path="production_card_output_challan.pdf",
        product_name=data['product_name'],
        code=data['code'],
        date=data['date'],
        total_output=data['total_output'],
        uom=data['uom'],
        total_loss=data['total_loss'],
        remarks=data['remarks'],
        batches=data['batches'],
        raw_materials=data['raw_materials'],    
        production_incharge=data['production_incharge'],
        approved_by=data['approved_by'],
        accounted_by=data['accounted_by']
    )
    
    print("Prod Card generated: output_challan.pdf")
