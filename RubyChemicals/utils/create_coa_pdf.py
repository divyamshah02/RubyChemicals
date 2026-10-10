import os
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coa_assets")
LOGO_PATH = os.path.join(ASSET_DIR, "logo.png")
STAMP_PATH = os.path.join(ASSET_DIR, "stamp.png")
SIGNATURE_PATH = os.path.join(ASSET_DIR, "signature.png")

NAVY = colors.HexColor("#002060")
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_X = 28
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN_X

CERTIFY_TEXT = (
    "We hereby certify that the material has been manufactured as per the "
    "described test results of the product."
)
REMARKS_TEXT = (
    "The above test results are based on internal testing methods developed and "
    "standardized through experience over a period of years. The product has been "
    "manufactured in accordance with these tested parameters. However, variations "
    "may occur when tested under different conditions, equipment, or external "
    "laboratory methods. The results should therefore be considered indicative and "
    "not absolute."
)

FOOTER_LINES = [
    "A-438, Moneyplant Highstreet, Jagatpur Road, S G Highway, Ahmedabad \u2013 382470, Gujarat, India",
    "2-3, Ajanta Sheds, Santej \u2013 Vadsar Road, Santej, Gandhinagar \u2013 382721, Gujarat, India",
    "+91 95 58 58 7829 | factory@rubychemicals.co | www.rubychemicals.co",
]

UNIT_LABELS = {
    "kg": "KGS.",
    "g": "GRAMS",
    "pcs": "PCS.",
}


def format_date(value):
    """Accepts a date/datetime or an ISO string and returns DD.MM.YYYY."""
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d.%m.%Y")
    text = str(value)
    return f"{text[8:10]}.{text[5:7]}.{text[0:4]}"


def format_quantity(quantity, unit):
    unit_label = UNIT_LABELS.get(str(unit), str(unit).upper())
    return f"{float(quantity):.3f} {unit_label}"


def _fit_image(path, max_width, max_height):
    from reportlab.lib.utils import ImageReader

    width, height = ImageReader(path).getSize()
    scale = min(max_width / width, max_height / height)
    return width * scale, height * scale


class SignatureBlock(Flowable):
    """'For, Ruby Build Care LLP' with the stamp, signature and authorised signatory line."""

    HEIGHT = 112

    def __init__(self):
        super().__init__()
        self.width = CONTENT_WIDTH
        self.height = self.HEIGHT

    def wrap(self, avail_width, avail_height):
        return avail_width, self.HEIGHT

    def draw(self):
        c = self.canv
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(0, self.HEIGHT - 12, "For, Ruby Build Care LLP")

        stamp_w, stamp_h = _fit_image(STAMP_PATH, 70, 70)
        c.drawImage(STAMP_PATH, 78, 22, width=stamp_w, height=stamp_h, mask="auto")

        sig_w, sig_h = _fit_image(SIGNATURE_PATH, 90, 40)
        c.drawImage(SIGNATURE_PATH, 8, 30, width=sig_w, height=sig_h, mask="auto")

        c.setStrokeColor(colors.black)
        c.setLineWidth(0.8)
        c.line(0, 22, 150, 22)
        c.setFont("Helvetica", 10)
        c.drawString(0, 9, "(Authorised Signatory)")


def _draw_page_chrome(canvas, doc):
    canvas.saveState()

    logo_w, logo_h = _fit_image(LOGO_PATH, 170, 30)
    top = PAGE_HEIGHT - 24
    canvas.drawImage(LOGO_PATH, MARGIN_X, top - logo_h, width=logo_w, height=logo_h, mask="auto")

    canvas.setFillColor(NAVY)
    canvas.setFont("Helvetica-Bold", 17)
    canvas.drawRightString(PAGE_WIDTH - MARGIN_X, top - 22, "RUBY BUILD CARE LLP")

    canvas.setStrokeColor(NAVY)
    canvas.setLineWidth(1.5)
    canvas.line(MARGIN_X, top - logo_h - 10, PAGE_WIDTH - MARGIN_X, top - logo_h - 10)

    canvas.setLineWidth(1)
    canvas.line(MARGIN_X, 62, PAGE_WIDTH - MARGIN_X, 62)
    canvas.setFillColor(colors.black)
    canvas.setFont("Helvetica", 7.5)
    y = 50
    for line in FOOTER_LINES:
        canvas.drawCentredString(PAGE_WIDTH / 2, y, line)
        y -= 10

    canvas.restoreState()


def generate_coa(
    ref_no,
    date,
    batch_no,
    mfg_date,
    product_name,
    quantity,
    unit,
    parameters,
):
    """
    Builds the Certificate of Analysis and returns it as a BytesIO stream.

    parameters: list of dicts with keys 'particulars', 'parameter', 'result'.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=108,
        bottomMargin=78,
        title=f"Certificate of Analysis - {batch_no}",
        author="Ruby Build Care LLP",
    )

    title_style = ParagraphStyle(
        "coa_title", fontName="Helvetica-Bold", fontSize=14, alignment=TA_CENTER, leading=18
    )
    cell_style = ParagraphStyle("coa_cell", fontName="Helvetica", fontSize=10, leading=13)
    cell_bold = ParagraphStyle("coa_cell_bold", parent=cell_style, fontName="Helvetica-Bold")
    cell_center = ParagraphStyle("coa_cell_center", parent=cell_style, alignment=TA_CENTER)
    head_style = ParagraphStyle(
        "coa_head", parent=cell_style, fontName="Helvetica-Bold", alignment=TA_CENTER
    )
    body_style = ParagraphStyle(
        "coa_body", fontName="Helvetica", fontSize=10.5, leading=15, alignment=TA_LEFT
    )
    remarks_style = ParagraphStyle(
        "coa_remarks", fontName="Helvetica", fontSize=9, leading=12.5, alignment=TA_JUSTIFY
    )

    def esc(value):
        return (
            str(value if value is not None else "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    grid = ("GRID", (0, 0), (-1, -1), 0.8, colors.black)

    story = [Paragraph("<u>CERTIFICATE OF ANALYSIS</u>", title_style), Spacer(1, 14)]

    ref_rows = [
        [Paragraph("REF. NO.:", cell_bold), Paragraph(esc(ref_no), cell_style),
         Paragraph("DATE:", cell_bold), Paragraph(esc(date), cell_style)],
        [Paragraph("BATCH NO.:", cell_bold), Paragraph(esc(batch_no), cell_style),
         Paragraph("MFG. DATE:", cell_bold), Paragraph(esc(mfg_date), cell_style)],
        [Paragraph("PRODUCT NAME:", cell_bold), Paragraph(esc(product_name), cell_style),
         Paragraph("QUANTITY:", cell_bold), Paragraph(esc(format_quantity(quantity, unit)), cell_style)],
    ]
    ref_table = Table(
        ref_rows,
        colWidths=[CONTENT_WIDTH * 0.20, CONTENT_WIDTH * 0.32, CONTENT_WIDTH * 0.17, CONTENT_WIDTH * 0.31],
    )
    ref_table.setStyle(TableStyle([
        grid,
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [ref_table, Spacer(1, 16)]

    param_rows = [[
        Paragraph("SR. NO.", head_style),
        Paragraph("PARTICULARS", head_style),
        Paragraph("PARAMETERS", head_style),
        Paragraph("RESULT", head_style),
    ]]
    for index, item in enumerate(parameters, start=1):
        param_rows.append([
            Paragraph(str(index), cell_center),
            Paragraph(esc(item.get("particulars")), cell_style),
            Paragraph(esc(item.get("parameter")), cell_style),
            Paragraph(esc(item.get("result")), cell_center),
        ])
    param_table = Table(
        param_rows,
        colWidths=[CONTENT_WIDTH * 0.11, CONTENT_WIDTH * 0.29, CONTENT_WIDTH * 0.31, CONTENT_WIDTH * 0.29],
        repeatRows=1,
    )
    param_table.setStyle(TableStyle([
        grid,
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [param_table, Spacer(1, 22)]

    remarks_table = Table(
        [
            [Paragraph("REMARKS:", cell_bold)],
            [Paragraph(esc(REMARKS_TEXT), remarks_style)],
        ],
        colWidths=[CONTENT_WIDTH],
    )
    remarks_table.setStyle(TableStyle([
        grid,
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    story.append(KeepTogether([
        Paragraph(esc(CERTIFY_TEXT), body_style),
        Spacer(1, 12),
        SignatureBlock(),
        Spacer(1, 10),
        remarks_table,
    ]))

    doc.build(story, onFirstPage=_draw_page_chrome, onLaterPages=_draw_page_chrome)
    buffer.seek(0)
    return buffer
