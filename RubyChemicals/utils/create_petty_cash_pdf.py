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

def format_date(s):
    return f"{s[8:10]}-{s[5:7]}-{s[0:4]}"


def generate_petty_cash_card(
    input_pdf_path,
    output_pdf_path,
    challan_no,
    date,
    to,
    expense_head,
    paid_via,
    payment_type,
    particulars,
    amount,
    total_amount,
    remarks,
    paid_by,
):
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    
    # ---- HEADER FIELDS ----
    can.setFont("Helvetica", 12) 
    can.drawString(80, 743, str(challan_no))
    can.drawString(445, 743, format_date(date))        
    can.drawString(35, 700, to)
    can.drawString(90, 670, expense_head)
    can.drawString(62, 641, paid_via)
    can.drawString(418, 641, payment_type)
    can.drawString(20, 585, particulars)
    can.drawString(380, 585, amount)
    can.drawString(380, 499, total_amount)
    can.drawString(58, 388, paid_by)
    can.drawString(382, 388, format_date(date))

    remarks_lst = split_text(remarks)
    remarks_line = 0
    remarks_line_y = 468
    for addr in remarks_lst:
        if remarks_line == 3:
            break
        if remarks_line == 0:
            can.drawString(63, remarks_line_y, addr)            
        else:
            can.drawString(18, remarks_line_y, addr)
        remarks_line_y -= 27
        remarks_line += 1



    can.save()

    packet.seek(0)

    new_pdf = PdfReader(packet)
    existing_pdf = PdfReader(input_pdf_path)

    output = PdfWriter()

    page = existing_pdf.pages[0]
    page.merge_page(new_pdf.pages[0])
    # output.add_page(page)
    output.add_page(page)
    output.add_page(page)

    # 👉 write to memory instead of file
    output_stream = BytesIO()
    output.write(output_stream)
    output_stream.seek(0)

    return output_stream

    can.save()

    # packet.seek(0)

    # new_pdf = PdfReader(packet)
    # existing_pdf = PdfReader(input_pdf_path)

    output = PdfWriter()

    # page = existing_pdf.pages[0]
    # page.merge_page(new_pdf.pages[0])
    # # output.add_page(page)
    # output.add_page(page)

    # # 👉 write to memory instead of file
    # output_stream = BytesIO()
    # output.write(output_stream)
    # output_stream.seek(0)

    # return output_stream


    packet.seek(0)
    
     # 👉 write to memory instead of file
    output_stream = BytesIO()
    output.write(output_stream)
    output_stream.seek(0)
    
    # return output_stream
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
        "challan_no": "001",
        "date": "2026-04-22",
        "to": "Dynamic Labz",
        "expense_head": "Raw Materials",
        "paid_via": "Online",
        "payment_type": "part", # advance - part - final
        "particulars": "Web portal developemtn",
        "amount": "120000",
        "total_amount": "120000",
        "remarks": "Loream ipsum is cool but useless just like you. 1 Loream ipsum is cool but useless just like you. 2 Loream ipsum is cool but useless just like you. 3 Loream ipsum is cool but useless just like you. 4 Loream ipsum is cool but useless just like you. 5 Loream ipsum is cool but useless just like you. 6 Loream ipsum is cool but useless just like you.",
        "paid_by": "Divyam Shah"
    }

    generate_petty_cash_card(
        input_pdf_path=r"petty_cash_template.pdf",
        output_pdf_path="petty_cash_template_output_challan.pdf",
        challan_no=data["challan_no"],
        date=data["date"],
        to=data["to"],
        expense_head=data["expense_head"],
        paid_via=data["paid_via"],
        payment_type=data["payment_type"],
        particulars=data["particulars"],
        amount=data["amount"],
        total_amount=data["total_amount"],
        remarks=data["remarks"],
        paid_by=data["paid_by"],
    )
    
    print("Prod Card generated: output_challan.pdf")
