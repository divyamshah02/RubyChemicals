# pip install docxtpl
from docxtpl import DocxTemplate

def generate_doc():
    doc = DocxTemplate(r"C:\Users\Divyam Shah\Downloads\PRODUCTION CARD (1).docx")

    data = {
        "product_name": "Test Prod",
        "code": "PRD-1",
        "date": "2026-04-22",
        "batch_count": 3,
        "total_output": "1200 kg",
        "total_loss": "119.999 kg",
        "remarks": "This is a test remark",

        "batches": [
            {"batch_code": "BTC-1", "product": "Binder Powder", "output": "1200 kg", "loss": "0 kg"},
            {"batch_code": "BTC-2", "product": "Rainproof", "output": "560 kg", "loss": "0 kg"},
            {"batch_code": "BTC-3", "product": "Chemical A", "output": "5 kg", "loss": "0 kg"},
        ],

        "raw_materials": [
            {"material": "Test stock item", "quantity": "120 kg"},
            {"material": "Waterproof Chemical A", "quantity": "180 kg"},
        ]
    }

    doc.render(data)
    doc.save("output.docx")

generate_doc()