"""
utils/create_salary_slip_pdf.py
───────────────────────────────
Builds the monthly salary slip PDF from a saved Payroll. Uses the same letterhead and
footer as the COA so company documents look consistent.
"""

from calendar import month_name
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .create_coa_pdf import CONTENT_WIDTH, MARGIN_X, NAVY, PAGE_HEIGHT, _draw_page_chrome, format_date

LIGHT = colors.HexColor("#EEF2F8")
GRID = colors.HexColor("#9AA5B8")

ONES = [
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven",
    "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen",
]
TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

COMPONENT_LABELS = [
    ("basic_pay", "Basic Pay"),
    ("da", "Dearness Allowance (DA)"),
    ("hra", "House Rent Allowance (HRA)"),
    ("lta", "Leave Travel Allowance (LTA)"),
    ("epf", "EPF"),
    ("gratuity", "Gratuity"),
    ("esic", "ESIC"),
]


def _below_thousand(number):
    words = []
    if number >= 100:
        words.append(f"{ONES[number // 100]} Hundred")
        number %= 100
    if number >= 20:
        words.append(TENS[number // 10] + (f" {ONES[number % 10]}" if number % 10 else ""))
    elif number:
        words.append(ONES[number])
    return " ".join(words)


def amount_in_words(amount):
    """Indian numbering: 1,23,456.50 -> 'One Lakh Twenty Three Thousand ... and Fifty Paise'."""
    amount = Decimal(amount).quantize(Decimal("0.01"))
    rupees, paise = int(amount), int((amount - int(amount)) * 100)
    if rupees == 0 and paise == 0:
        return "Zero Rupees Only"

    parts = []
    for divisor, label in ((10_000_000, "Crore"), (100_000, "Lakh"), (1_000, "Thousand")):
        if rupees >= divisor:
            parts.append(f"{_below_thousand(rupees // divisor)} {label}")
            rupees %= divisor
    if rupees:
        parts.append(_below_thousand(rupees))

    text = " ".join(parts) + " Rupees" if parts else ""
    if paise:
        text += f"{' and ' if text else ''}{_below_thousand(paise)} Paise"
    return f"{text} Only"


def inr(value):
    """12,34,567.00 style grouping with the 'Rs.' prefix (Helvetica has no rupee glyph)."""
    value = Decimal(value or 0).quantize(Decimal("0.01"))
    whole, _, fraction = f"{abs(value):.2f}".partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    sign = "-" if value < 0 else ""
    return f"{sign}Rs. {whole}.{fraction}"


def _mask_account(number):
    number = (number or "").strip()
    return f"XXXXXX{number[-4:]}" if len(number) > 4 else number


def _styles():
    base = ParagraphStyle("base", fontName="Helvetica", fontSize=9.5, leading=12)
    return {
        "base": base,
        "bold": ParagraphStyle("bold", parent=base, fontName="Helvetica-Bold"),
        "right": ParagraphStyle("right", parent=base, alignment=TA_RIGHT),
        "right_bold": ParagraphStyle("right_bold", parent=base, alignment=TA_RIGHT, fontName="Helvetica-Bold"),
        "title": ParagraphStyle(
            "title", parent=base, fontName="Helvetica-Bold", fontSize=13, leading=16,
            alignment=TA_CENTER, textColor=NAVY,
        ),
        "section": ParagraphStyle(
            "section", parent=base, fontName="Helvetica-Bold", fontSize=10, textColor=NAVY,
        ),
        "small": ParagraphStyle("small", parent=base, fontSize=8, leading=10, textColor=colors.HexColor("#555555")),
        "center_small": ParagraphStyle(
            "center_small", parent=base, fontSize=8, leading=10, alignment=TA_CENTER,
            textColor=colors.HexColor("#555555"),
        ),
    }


def _table(rows, widths, extra=None, header=False):
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.6, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), LIGHT)]
    table.setStyle(TableStyle(style + (extra or [])))
    return table


def generate_salary_slip(payroll):
    """Returns a BytesIO positioned at 0 containing the salary slip PDF."""
    s = _styles()
    user = payroll.user
    detail = user.employee_detail
    period = f"{month_name[payroll.month]} {payroll.year}"
    P = Paragraph

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=(CONTENT_WIDTH + 2 * MARGIN_X, PAGE_HEIGHT),
        leftMargin=MARGIN_X, rightMargin=MARGIN_X, topMargin=88, bottomMargin=78,
        title=f"Salary Slip {period} - {detail.full_name or user.name}",
    )

    half = CONTENT_WIDTH / 2
    story = [P(f"SALARY SLIP FOR {period.upper()}", s["title"]), Spacer(1, 8)]

    info = [
        [P("Employee name", s["bold"]), P(detail.full_name or user.name, s["base"]),
         P("Employee ID", s["bold"]), P(str(user.user_id), s["base"])],
        [P("Department", s["bold"]), P(detail.department or "-", s["base"]),
         P("Designation", s["bold"]), P(detail.position or "-", s["base"])],
        [P("Date of joining", s["bold"]), P(format_date(detail.joining_date) or "-", s["base"]),
         P("PAN", s["bold"]), P(detail.pan_number or "-", s["base"])],
        [P("Bank", s["bold"]), P(detail.bank_name or "-", s["base"]),
         P("Account no.", s["bold"]), P(_mask_account(detail.bank_account_no) or "-", s["base"])],
    ]
    quarter = CONTENT_WIDTH / 4
    story += [_table(info, [quarter * 0.9, quarter * 1.1, quarter * 0.9, quarter * 1.1]), Spacer(1, 10)]

    earnings = [[P("EARNINGS", s["bold"]), P("AMOUNT", s["right_bold"])]]
    for field, label in COMPONENT_LABELS:
        earnings.append([P(label, s["base"]), P(inr(getattr(payroll, field)), s["right"])])
    earnings.append([P("TOTAL SALARY", s["bold"]), P(inr(payroll.total_salary), s["right_bold"])])
    last = len(earnings) - 1
    story += [
        _table(earnings, [CONTENT_WIDTH - 130, 130], header=True,
               extra=[("BACKGROUND", (0, last), (-1, last), LIGHT)]),
        Spacer(1, 10),
    ]

    days = f"{payroll.leave_days_deducted:g}"
    deductions = [
        [P("DEDUCTIONS", s["bold"]), P("AMOUNT", s["right_bold"])],
        [P(f"Leave ({days} day(s) x {inr(payroll.per_day_rate)} per day, total salary / 30)", s["base"]),
         P(f"- {inr(payroll.leave_deduction)}", s["right"])],
        [P("TDS" + ("" if payroll.tds_applicable else " (not applicable)"), s["base"]),
         P(f"- {inr(payroll.tds_deducted)}", s["right"])],
        [P("SALARY FOR THE MONTH", s["bold"]), P(inr(payroll.salary_for_month), s["right_bold"])],
    ]
    story += [
        _table(deductions, [CONTENT_WIDTH - 130, 130], header=True,
               extra=[("BACKGROUND", (0, 3), (-1, 3), LIGHT)]),
        Spacer(1, 10),
    ]

    reimbursements = list(payroll.reimbursements.all().order_by("expense_date"))
    if reimbursements:
        rows = [[P("REIMBURSEMENTS", s["bold"]), P("DATE", s["bold"]), P("AMOUNT", s["right_bold"])]]
        for item in reimbursements:
            rows.append([P(item.description, s["base"]), P(format_date(item.expense_date), s["base"]),
                         P(inr(item.amount), s["right"])])
        rows.append([P("TOTAL REIMBURSEMENT", s["bold"]), "", P(inr(payroll.reimbursement_total), s["right_bold"])])
        story += [
            _table(rows, [CONTENT_WIDTH - 230, 100, 130], header=True,
                   extra=[("BACKGROUND", (0, len(rows) - 1), (-1, len(rows) - 1), LIGHT),
                          ("SPAN", (0, len(rows) - 1), (1, len(rows) - 1))]),
            Spacer(1, 10),
        ]

    if payroll.adjustment_amount:
        sign = "+" if payroll.adjustment_amount > 0 else "-"
        story += [
            _table([[P(f"Adjustment: {payroll.adjustment_note}", s["base"]),
                     P(f"{sign} {inr(abs(payroll.adjustment_amount))}", s["right"])]],
                   [CONTENT_WIDTH - 130, 130]),
            Spacer(1, 10),
        ]

    net = _table(
        [[P("NET SALARY PAYABLE", s["bold"]), P(inr(payroll.net_payable), s["right_bold"])],
         [P(f"Rupees: {amount_in_words(payroll.net_payable)}", s["base"]), ""]],
        [CONTENT_WIDTH - 130, 130],
        extra=[("BACKGROUND", (0, 0), (-1, 0), LIGHT), ("SPAN", (0, 1), (1, 1))],
    )
    story += [KeepTogether([net]), Spacer(1, 10)]

    lines = list(payroll.leave_lines.all().order_by("date"))
    if lines:
        rows = [[P("LEAVE DETAILS", s["bold"]), P("TYPE", s["bold"]), P("DAYS", s["bold"]),
                 P("SALARY CUT", s["right_bold"])]]
        for line in lines:
            rows.append([
                P(format_date(line.date), s["base"]),
                P(line.leave_type.title(), s["base"]),
                P(f"{line.days:g}", s["base"]),
                P(inr(line.amount) if line.deduct else "Not deducted", s["right"]),
            ])
        story += [
            _table(rows, [CONTENT_WIDTH - 280, 90, 60, 130], header=True),
            Spacer(1, 10),
        ]

    story.append(P("This is a computer generated salary slip.", s["center_small"]))
    doc.build(story, onFirstPage=_draw_page_chrome, onLaterPages=_draw_page_chrome)
    buffer.seek(0)
    return buffer
