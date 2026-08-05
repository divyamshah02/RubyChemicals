"""
QuotationPDFViewSet
===================
GET  /leads/quotations/<pk>/download-pdf/

Generates a PDF quotation based on the quotation's sub-department:
  • sub_department code == "RC"  → RC-style table (SR NO / PARTICULARS / SCOPE / UNIT / QTY / RATE / TOTAL)
                                   with application-area group headers.
  • anything else (e.g. "OEM") → OEM-style table (NO / PRODUCT NAME / UNIT / GST / MRP / OFFER RATE)

Requires reportlab:
    pip install reportlab

NOTE: This file is standalone — drop it into your app folder, register the URL in urls.py,
and import it from leads_viewsets.py (or directly in urls.py).
"""

from io import BytesIO
from itertools import groupby

from django.http import HttpResponse
from rest_framework import viewsets

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)
from reportlab.platypus.flowables import HRFlowable

# ── local imports ─────────────────────────────────────────────────────────────
try:
    from .models import Quotation
    from utils.decorators import handle_exceptions, check_authentication
except ImportError:
    # allow running standalone / during code review
    Quotation = None
    handle_exceptions = lambda f: f
    check_authentication = lambda **kw: (lambda f: f)


# ─────────────────────────────────────────────────────────────────────────────
# Branding constants  (edit here to match your letterhead)
# ─────────────────────────────────────────────────────────────────────────────
COMPANY_NAME    = "Ruby Build Care LLP"
COMPANY_ADDRESS = "A438, Moneyplant Highstreet, Jagatpur Road, SG Highway, Ahmedabad - 382470, Gujarat, India"
COMPANY_PHONE   = "+91 95 58 58 7829"
COMPANY_EMAIL   = "sales@rubychemicals.co"
COMPANY_WEBSITE = "www.rubychemicals.co"

# BDE / Authorised signatory
SIGNATORY_NAME  = "Ms. Nidhi Thakkar"
SIGNATORY_ROLE  = "BDE"
SIGNATORY_PHONE = "+91 70 48 48 7829"

# Colour palette
DARK_BLUE  = colors.HexColor("#003399")   # table header bg, section header bg
MID_BLUE   = colors.HexColor("#003399")   # same as dark blue kept for semantic clarity
LIGHT_GREY = colors.HexColor("#F2F2F2")   # alternating row
WHITE      = colors.white
BLACK      = colors.black

# RC Terms & Conditions
RC_TERMS = [
    "Required Electricity, Lockable Store, Sand, Bricks, Blocks, Cement, Grit, Water, Lift etc. shall be provided by client at free of cost.",
    "Stay for Labour in Labour Colony or space on site shall be provided by client at free of cost.",
    "Quantity shall be considered only as per actual treated area on site.",
    "GST @ 18% shall be extra",
    "Work shall commence only after receiving of Work Order.",
    "Cost of removal of macro cleaning shall be extra",
    "Site shall be executed by our authorised applicator.",
    "Treatment conditions can be considered for revision in case of any situation on site.",
    "If lead is more for material picking up on site, extra charges shall be levied as per site situation and shall be pre-informed.",
]
RC_PAYMENT = "40% Advance Against Material Delivery on Site, 40% As Per Running Work in Progress, and 20% within 7 Days of Completion of Work"

# OEM Terms & Conditions
OEM_TERMS = [
    "Terms of Delivery :",
    "Above rates shall be net and final. Rates are subject to change at company's discretion.",
    "Rates are valid for 30 days from the date of quotation.",
    "Order shall be processed only after purchase order is received.",
    "Delivery of material shall be as per mutual consideration after purchase order is received.",
    "Goods once purchased shall not be taken back.",
    "All transactions shall be subject to Ahmedabad Jurisdiction Only.",
    "Billing and Delivery shall be done through our authorised dealer.",
    "All rates are inclusive of GST.",
]
OEM_PAYMENT = "100% Advance"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _std_response(success, data=None, error=None, http_status=200):
    from rest_framework.response import Response
    return Response({
        "success": success,
        "user_not_logged_in": False,
        "user_unauthorized": False,
        "data": data,
        "error": error,
    }, status=http_status)


def _has_leads_access(user):
    return user.is_super_admin or user.has_plugin_access('can_leads') or user.role == 'sales'


def _fmt_inr(value):
    """Format a decimal/float as Indian Rupee string, e.g. ₹ 1,300.00"""
    try:
        v = float(value)
        return f"{v:,.2f}"
        return f"\u20b9 {v:,.2f}"
    except (TypeError, ValueError):
        return str(value)


def _get_style():
    """Return a dict of ParagraphStyles used across both PDF types."""
    styles = getSampleStyleSheet()

    base = dict(
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=BLACK,
    )

    return {
        "title": ParagraphStyle("title", **{**base,
            "fontName": "Helvetica-Bold", "fontSize": 14,
            "alignment": TA_CENTER, "textColor": DARK_BLUE, "leading": 18,
        }),
        "subtitle": ParagraphStyle("subtitle", **{**base,
            "fontName": "Helvetica-Bold", "fontSize": 10,
            "alignment": TA_CENTER, "textColor": BLACK,
        }),
        "label_bold": ParagraphStyle("label_bold", **{**base,
            "fontName": "Helvetica-Bold",
        }),
        "normal": ParagraphStyle("normal", **base),
        "small": ParagraphStyle("small", **{**base, "fontSize": 8, "leading": 10}),
        "header_cell": ParagraphStyle("header_cell", **{**base,
            "fontName": "Helvetica-Bold", "fontSize": 8,
            "alignment": TA_CENTER, "textColor": WHITE,
        }),
        "cell_center": ParagraphStyle("cell_center", **{**base,
            "fontSize": 8, "alignment": TA_CENTER,
        }),
        "cell_left": ParagraphStyle("cell_left", **{**base,
            "fontSize": 8, "alignment": TA_LEFT,
        }),
        "cell_left_bold": ParagraphStyle("cell_left_bold", **{**base,
            "fontName": "Helvetica-Bold", "fontSize": 8, "alignment": TA_LEFT,
        }),
        "cell_right": ParagraphStyle("cell_right", **{**base,
            "fontSize": 8, "alignment": TA_RIGHT,
        }),
        "section_header": ParagraphStyle("section_header", **{**base,
            "fontName": "Helvetica-Bold", "fontSize": 8,
            "alignment": TA_CENTER, "textColor": WHITE,
        }),
        "footer_bold": ParagraphStyle("footer_bold", **{**base,
            "fontName": "Helvetica-Bold", "fontSize": 8,
        }),
        "footer_normal": ParagraphStyle("footer_normal", **{**base, "fontSize": 8}),
        "closing": ParagraphStyle("closing", **{**base, "fontSize": 9}),
        "right_align": ParagraphStyle("right_align", **{**base,
            "fontSize": 9, "alignment": TA_RIGHT,
        }),
    }


def _header_block(q, st, scope_of_work=""):
    """Return a list of Flowables for the common REF NO / DATE / TO / K.A. / SITE header."""
    items = []

    # REF NO + DATE  (two-column row)
    ref_date_data = [[
        Paragraph(f"<b>REF. NO</b>  {q.quotation_no}", st["normal"]),
        Paragraph(f"<b>DATE</b>  {q.quotation_date.strftime('%d-%m-%Y') if q.quotation_date else ''}", st["right_align"]),
    ]]
    ref_table = Table(ref_date_data, colWidths=[90*mm, 90*mm])
    ref_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ]))
    items.append(ref_table)

    # TO / K.A. / SITE + CONTACT (two-column)
    party    = q.lead.party_name if q.lead else ""
    ka       = q.lead.contact_person if q.lead else ""
    site     = q.shipping_address or ""
    contact  = q.lead.mobile_number if q.lead else ""

    info_data = [[
        Paragraph(f"<b>TO:</b> {party}", st["normal"]),
        Paragraph("", st["normal"]),
    ], [
        Paragraph(f"<b>K.A.</b>  {ka}", st["normal"]),
        Paragraph(f"<b>CONTACT:</b>  {contact}", st["right_align"]),
    ], [
        Paragraph(f"<b>SITE:</b>  {site}", st["normal"]),
        Paragraph("", st["normal"]),
    ]]
    info_table = Table(info_data, colWidths=[90*mm, 90*mm])
    info_table.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
    ]))
    items.append(info_table)

    items.append(Spacer(1, 2*mm))

    # SCOPE OF WORK
    scope = scope_of_work or q.notes or "Supply of Material On Site"
    items.append(Paragraph(f"<b>SCOPE OF WORK:</b> {scope}", st["normal"]))
    items.append(Spacer(1, 4*mm))

    return items


def _footer_block(terms, payment_terms, bde_name, bde_role, bde_phone, st):
    """Return a list of Flowables for Terms + Payment + Signatory footer."""
    items = []

    # ── Terms & Conditions table ──────────────────────────────────────────
    tc_data = [[Paragraph("<b>Terms &amp; Conditions</b>", st["footer_bold"])]]
    for i, t in enumerate(terms, 1):
        tc_data.append([Paragraph(f"{i}. {t}", st["footer_normal"])])

    tc_table = Table(tc_data, colWidths=[180*mm])
    tc_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0),   DARK_BLUE),
        ("TEXTCOLOR",   (0, 0), (-1, 0),   WHITE),
        ("BOX",         (0, 0), (-1, -1),  0.5, BLACK),
        ("INNERGRID",   (0, 0), (-1, -1),  0.25, colors.lightgrey),
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
    ]))
    items.append(tc_table)
    items.append(Spacer(1, 3*mm))

    # ── Payment Terms ─────────────────────────────────────────────────────
    pt_data = [
        [Paragraph("<b>Payment Terms</b>", st["footer_bold"])],
        [Paragraph(f"- {payment_terms}", st["footer_normal"])],
    ]
    pt_table = Table(pt_data, colWidths=[180*mm])
    pt_table.setStyle(TableStyle([
        ("BOX",         (0, 0), (-1, -1), 0.5, BLACK),
        ("INNERGRID",   (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
    ]))
    items.append(pt_table)
    items.append(Spacer(1, 3*mm))

    # ── Contact Details ───────────────────────────────────────────────────
    cd_data = [
        [Paragraph("<b>Contact Details</b>", st["footer_bold"])],
        [Paragraph(f"1  {bde_name}", st["footer_normal"])],
        [Paragraph(f"2  {bde_role}  {bde_phone}", st["footer_normal"])],
    ]
    cd_table = Table(cd_data, colWidths=[180*mm])
    cd_table.setStyle(TableStyle([
        ("BOX",         (0, 0), (-1, -1), 0.5, BLACK),
        ("INNERGRID",   (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
    ]))
    items.append(cd_table)
    items.append(Spacer(1, 4*mm))

    # ── Closing sentence + Signatory ──────────────────────────────────────
    items.append(Paragraph(
        "We are sure you will find our offer in line with your requirement and "
        "we look forward to for a positive business association.",
        st["closing"]
    ))
    items.append(Spacer(1, 5*mm))

    sig_data = [[
        Paragraph("Thanking You,<br/><b>For, Ruby Build Care LLP</b><br/>(Authorised Signatory)", st["normal"]),
    ]]
    sig_table = Table(sig_data, colWidths=[180*mm])
    sig_table.setStyle(TableStyle([
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    items.append(sig_table)
    items.append(Spacer(1, 6*mm))

    # ── Company footer address ────────────────────────────────────────────
    items.append(HRFlowable(width="100%", thickness=0.5, color=DARK_BLUE))
    items.append(Spacer(1, 2*mm))
    items.append(Paragraph(
        f"{COMPANY_ADDRESS}<br/>"
        f"{COMPANY_PHONE} | {COMPANY_EMAIL} | {COMPANY_WEBSITE}",
        ParagraphStyle("footer_addr", fontName="Helvetica", fontSize=7,
                       alignment=TA_CENTER, textColor=BLACK, leading=10),
    ))

    return items


# ─────────────────────────────────────────────────────────────────────────────
# RC  PDF builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_rc_pdf(q):
    """
    RC quotation:
    Columns: SR. NO. | PARTICULARS | SCOPE | UNIT | QTY. | RATE | TOTAL
    Items are grouped by application_area.  Each group gets a full-width
    dark-blue header row with the application area name.  Within a group,
    rows are labelled A, B, C … for active items, and "-" for fixed/ancillary
    items (rate == 0 or description indicates "INCLUDED").
    """
    buf  = BytesIO()
    doc  = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm,
    )
    st   = _get_style()
    story = []

    # ── Title ────────────────────────────────────────────────────────────
    story.append(Paragraph("ESTIMATE / QUOTATION", st["title"]))
    story.append(Spacer(1, 4*mm))

    # ── Header block ─────────────────────────────────────────────────────
    scope = q.notes or "WATERPROOFING WORK ON SITE"
    story.extend(_header_block(q, st, scope_of_work=scope))

    # ── Table ─────────────────────────────────────────────────────────────
    # Column widths (total ~180 mm)
    COL_W = [12*mm, 54*mm, 22*mm, 16*mm, 16*mm, 22*mm, 22*mm]
    HEADERS = ["SR. NO.", "PARTICULARS", "SCOPE", "UNIT", "QTY.", "RATE", "TOTAL"]

    tdata = []  # list of rows

    # Header row
    tdata.append([Paragraph(h, st["header_cell"]) for h in HEADERS])

    # Gather only active items
    active_items = [i for i in q.items.all() if i.is_active]

    # Group by application_area (preserve insertion order)
    seen_areas = []
    area_map   = {}
    for item in active_items:
        area = (item.application_area or "").strip() or "GENERAL"
        if area not in area_map:
            area_map[area] = []
            seen_areas.append(area)
        area_map[area].append(item)

    row_styles = []  # (style_name, row_index, ...)
    row_idx    = 1   # 0 is header

    for area_name in seen_areas:
        area_items = area_map[area_name]

        # ── Section header row ────────────────────────────────────────────
        tdata.append([
            Paragraph(area_name, st["section_header"]),
            "", "", "", "", "", "",
        ])
        row_styles.append(("SPAN", (0, row_idx), (6, row_idx)))
        row_styles.append(("BACKGROUND", (0, row_idx), (6, row_idx), DARK_BLUE))
        row_styles.append(("TEXTCOLOR",  (0, row_idx), (6, row_idx), WHITE))
        row_styles.append(("ALIGN",      (0, row_idx), (6, row_idx), "CENTER"))
        row_idx += 1

        # ── Item rows ─────────────────────────────────────────────────────
        alpha_counter = 0
        ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        for item in area_items:
            p_name  = item.stock_item.product_name if item.stock_item else item.product_name
            warranty = item.warranty or (item.stock_item.warranty if item.stock_item else "") or ""
            if warranty:
                particulars_text = f"<b>{p_name}</b><br/><b>WARRANTY : {warranty}</b>"
            else:
                particulars_text = f"<b>{p_name}</b>"

            scope_text = item.scope or ""

            # Determine row label
            is_ancillary = (
                float(item.rate or 0) == 0 or
                "INCLUDED" in p_name.upper() or
                "PIPE CORE" in p_name.upper() or
                "ANGLE FILLET" in p_name.upper() or
                "SLOPE" in p_name.upper() or
                "CONSTRUCTION JOINT" in p_name.upper()
            )
            if is_ancillary:
                sr_label = "-"
            else:
                sr_label = ALPHA[alpha_counter % 26]
                alpha_counter += 1

            # Rate / total cells — "INCLUDED. NOT EXTRA." for 0-rate items
            rate_val  = float(item.rate or 0)
            qty_val   = float(item.quantity or 0)
            total_val = rate_val * qty_val

            # Special display for ancillary items
            rate_cell  = _fmt_inr(rate_val) if rate_val else ""
            total_cell = _fmt_inr(total_val) if total_val else ""

            # Some 0-rate items have "INCLUDED. NOT EXTRA." spanning rate+total
            # We detect this when rate == 0 AND item is labelled "-"
            # We'll handle it via a simple text approach (no spanning for now to keep it simple)
            if is_ancillary and rate_val == 0:
                rate_display  = "INCLUDED. NOT EXTRA."
                total_display = ""
            elif "AS ACTUAL" in (item.description or "").upper():
                rate_display  = _fmt_inr(rate_val) if rate_val else "AS ACTUAL"
                total_display = ""
            else:
                rate_display  = _fmt_inr(rate_val) if rate_val else ""
                total_display = _fmt_inr(total_val) if total_val else ""

            qty_display = str(int(qty_val)) if qty_val == int(qty_val) and qty_val != 0 else (
                f"{qty_val:.2f}".rstrip("0").rstrip(".") if qty_val else ""
            )

            row = [
                Paragraph(sr_label, st["cell_center"]),
                Paragraph(particulars_text, st["cell_left"]),
                Paragraph(scope_text, st["cell_center"]),
                Paragraph(item.uom or "", st["cell_center"]),
                Paragraph(qty_display, st["cell_center"]),
                Paragraph(rate_display, st["cell_right"]),
                Paragraph(total_display, st["cell_right"]),
            ]
            tdata.append(row)
            row_idx += 1

    table = Table(tdata, colWidths=COL_W, repeatRows=1)

    # Base table style
    ts = TableStyle([
        # Header
        ("BACKGROUND",   (0, 0), (-1, 0),  DARK_BLUE),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0),  8),
        ("ALIGN",        (0, 0), (-1, 0),  "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        # Borders
        ("BOX",          (0, 0), (-1, -1), 0.75, BLACK),
        ("INNERGRID",    (0, 0), (-1, -1), 0.25, BLACK),
        # Padding
        ("LEFTPADDING",  (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        # Alternate rows (light grey for odd data rows, skip section headers)
    ])
    # Apply dynamic styles (section headers etc.)
    for s in row_styles:
        ts.add(*s)

    table.setStyle(ts)
    story.append(table)
    story.append(Spacer(1, 5*mm))

    # ── Footer ────────────────────────────────────────────────────────────
    story.extend(_footer_block(RC_TERMS, RC_PAYMENT, SIGNATORY_NAME, SIGNATORY_ROLE, SIGNATORY_PHONE, st))

    doc.build(story)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# OEM PDF builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_oem_pdf(q):
    """
    OEM quotation:
    Columns: NO. | PRODUCT NAME | UNIT | GST | MRP | OFFER RATE
    Flat list of active items, no application-area grouping.
    """
    buf  = BytesIO()
    doc  = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm,
    )
    st    = _get_style()
    story = []

    # ── Title ────────────────────────────────────────────────────────────
    story.append(Paragraph("ESTIMATE / QUOTATION", st["title"]))
    story.append(Spacer(1, 4*mm))

    # ── Header block ─────────────────────────────────────────────────────
    story.extend(_header_block(q, st, scope_of_work="Supply of Material On Site"))

    # ── Table ─────────────────────────────────────────────────────────────
    # Column widths (total ~180 mm)
    COL_W = [12*mm, 70*mm, 18*mm, 14*mm, 33*mm, 33*mm]
    HEADERS = ["NO.", "PRODUCT NAME", "UNIT", "GST", "MRP", "OFFER RATE"]

    tdata = [[Paragraph(h, st["header_cell"]) for h in HEADERS]]

    active_items = [i for i in q.items.all() if i.is_active]

    for idx, item in enumerate(active_items, 1):
        p_name = item.stock_item.product_name if item.stock_item else item.product_name

        # GST: prefer item's hsn_code lookup, fall back to stock_item gst if
        # the linked item is a SubDeptStockItem (no gst field) — show from description
        gst_text = "18%"  # default for waterproofing / construction chemicals
        if item.description and "%" in item.description:
            gst_text = item.description.strip()

        mrp_val   = float(item.rate or 0)
        offer_val = float(item.quantity or 0) * mrp_val
        # In OEM context: rate = MRP, and total = offer rate (sometimes quantity used as offer price)
        # Based on the PDF: MRP and OFFER RATE are both price columns (not qty × rate)
        # The serializer stores: rate, quantity.  For OEM, rate = MRP, quantity ≠ 1 is unusual.
        # We'll treat rate as MRP and total (rate*qty) as the offer rate.
        # If qty == 1, offer_rate = rate.
        # If you store offer_rate separately, adjust this logic.
        offer_rate = float(item.total) if hasattr(item, 'total') else offer_val

        mrp_display   = _fmt_inr(mrp_val)
        offer_display = _fmt_inr(offer_rate)

        row = [
            Paragraph(str(idx), st["cell_center"]),
            Paragraph(p_name, st["cell_left"]),
            Paragraph(item.uom or "Per Pack", st["cell_center"]),
            Paragraph(gst_text, st["cell_center"]),
            Paragraph(mrp_display, st["cell_right"]),
            Paragraph(offer_display, st["cell_right"]),
        ]
        tdata.append(row)

    table = Table(tdata, colWidths=COL_W, repeatRows=1)
    table.setStyle(TableStyle([
        # Header
        ("BACKGROUND",   (0, 0), (-1, 0),  DARK_BLUE),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0),  8),
        ("ALIGN",        (0, 0), (-1, 0),  "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        # Borders
        ("BOX",          (0, 0), (-1, -1), 0.75, BLACK),
        ("INNERGRID",    (0, 0), (-1, -1), 0.25, BLACK),
        # Padding
        ("LEFTPADDING",  (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        # Alternate row shading
        *[("BACKGROUND", (0, i), (-1, i), LIGHT_GREY)
          for i in range(2, len(tdata), 2)],
    ]))
    story.append(table)
    story.append(Spacer(1, 5*mm))

    # ── Footer ────────────────────────────────────────────────────────────
    story.extend(_footer_block(OEM_TERMS, OEM_PAYMENT, SIGNATORY_NAME, SIGNATORY_ROLE, SIGNATORY_PHONE, st))

    doc.build(story)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# ViewSet
# ─────────────────────────────────────────────────────────────────────────────

class QuotationPDFViewSet(viewsets.ViewSet):
    """
    GET  /leads/quotations/<pk>/download-pdf/

    Returns a PDF file download response.
    Branch logic:
      • sub_department.code == "RC"  →  RC-style PDF
      • anything else               →  OEM-style PDF
    """

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        pk = request.query_params.get("quotation_id")
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)

        try:
            q = (
                Quotation.objects
                .prefetch_related("items__stock_item")
                .select_related("lead", "lead__sub_department", "created_by")
                .get(pk=pk)
            )
        except Quotation.DoesNotExist:
            return _std_response(False, error="Quotation not found", http_status=404)

        # Determine sub-department
        sub_dept_code = ""
        try:
            sub_dept_code = q.lead.sub_department.code.upper()
        except AttributeError:
            pass

        if sub_dept_code == "RC":
            pdf_buf = _build_rc_pdf(q)
        else:
            pdf_buf = _build_oem_pdf(q)

        filename = f"Quotation-{q.quotation_no}.pdf"
        response = HttpResponse(pdf_buf.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
