from docx import Document
from copy import deepcopy
import docx2pdf


def replace_placeholders(doc, data):
    # Replace in paragraphs
    for para in doc.paragraphs:
        for key, value in data.items():
            if f"{{{{{key}}}}}" in para.text:
                para.text = para.text.replace(f"{{{{{key}}}}}", str(value))

    # Replace inside tables (important)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for key, value in data.items():
                    if f"{{{{{key}}}}}" in cell.text:
                        cell.text = cell.text.replace(f"{{{{{key}}}}}", str(value))


def fill_items_table(doc, items):
    """
    Assumes FIRST table is your items table.
    """
    table = doc.tables[0]

    # Remove existing empty rows except header
    while len(table.rows) > 1:
        table._element.remove(table.rows[1]._element)

    # Add items
    for item in items:
        row_cells = table.add_row().cells
        row_cells[0].text = str(item["sr"])
        row_cells[1].text = item["name"]
        row_cells[2].text = item["hsn"]
        row_cells[3].text = str(item["qty"])


def duplicate_challan_section(doc, data, items):
    """
    Your DOC has TWO challans in one page.
    This fills BOTH.
    """
    replace_placeholders(doc, data)
    fill_items_table(doc, items)


def generate_challan(
    template_path,
    output_docx,
    output_pdf,
    data,
    items
):
    doc = Document(template_path)

    # Fill both sections (since placeholders are duplicated)
    duplicate_challan_section(doc, data, items)

    # Save DOCX
    doc.save(output_docx)

    # Convert to PDF
    docx2pdf.convert(output_docx, output_pdf)


# =========================
# 🚀 TEST CALL
# =========================

if __name__ == "__main__":

    data = {
        "company name": "Dynamic Labz Pvt Ltd",
        "challan_no": "CH-00123",
        "address": "Ahmedabad, Gujarat",
        "date": "22-04-2026",
        "vehicle_no": "GJ01AB1234",
        "gstin": "24ABCDE1234F1Z5",
        "contact_name": "Divyam",
        "contact_number": "9876543210"
    }

    items = [
        {"sr": 1, "name": "Cement Bag", "hsn": "2523", "qty": 50},
        {"sr": 2, "name": "Sand", "hsn": "2505", "qty": 100},
        {"sr": 3, "name": "Steel Rod", "hsn": "7214", "qty": 30},
    ]

    generate_challan(
        template_path=r"C:\Users\Divyam Shah\Downloads\FOR SOFTWARE - CHALLAN.docx",
        output_docx="output.docx",
        output_pdf="output.pdf",
        data=data,
        items=items
    )

    print("✅ DOCX + PDF generated")