"""
utils/create_daily_log_pdf.py
──────────────────────────────
Generates the "Lead Activity Report" PDF used by the Leads module.

Two entry points:
  • generate_daily_log_pdf(...)            -> single user / admin "all" report (2 pages)
  • generate_all_users_daily_log_pdf(...)  -> admin-only bulk export, one section per user
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    PageBreak,
)

styles = getSampleStyleSheet()

TITLE_STYLE = ParagraphStyle(
    "TitleStyle", parent=styles["Heading1"], fontSize=16, spaceAfter=4, textColor=colors.HexColor("#1f2937")
)
SUBTITLE_STYLE = ParagraphStyle(
    "SubtitleStyle", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#4b5563"), spaceAfter=10
)
SECTION_STYLE = ParagraphStyle(
    "SectionStyle", parent=styles["Heading2"], fontSize=13, spaceBefore=6, spaceAfter=8, textColor=colors.HexColor("#111827")
)
EMPTY_STYLE = ParagraphStyle(
    "EmptyStyle", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#6b7280")
)
CELL_STYLE = ParagraphStyle("CellStyle", parent=styles["Normal"], fontSize=8, leading=10)
HEADER_CELL_STYLE = ParagraphStyle(
    "HeaderCellStyle", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.white
)


def _p(text):
    return Paragraph("" if text is None else str(text), CELL_STYLE)


def _header_cell(text):
    return Paragraph(str(text), HEADER_CELL_STYLE)


def _activity_table(logs, is_admin):
    headers = ["Time"]
    if is_admin:
        headers.append("User")
    headers.extend(["Action", "Lead ID", "Party Name", "Contact", "Party Type", "Status", "Remarks"])

    data = [[_header_cell(h) for h in headers]]

    for log in logs:
        row = [_p(log["time"].strftime("%H:%M:%S"))]
        if is_admin:
            row.append(_p(log["user"]))
        row.extend([
            _p(log["action"]),
            _p(log["lead_id"]),
            _p(log["party"]),
            _p(log["contact"]),
            _p(log["party_type"]),
            _p(log["status"]),
            _p(log["remarks"]),
        ])
        data.append(row)

    col_count = len(headers)
    if is_admin:
        widths = [1.6, 2.2, 2.6, 1.8, 3.2, 2.6, 2.2, 2.0, 5.0]
    else:
        widths = [1.6, 2.6, 1.8, 3.2, 2.6, 2.2, 2.0, 5.6]
    widths = widths[:col_count]
    total = sum(widths)
    col_widths = [(w / total) * (26.5 * cm) for w in widths]

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(_table_style())
    return table


def _followup_table(pending_leads, is_admin):
    headers = ["Lead ID", "Party Name", "Contact", "Mobile", "Party Type", "Status", "Followup Date", "Followup Time", "Remarks", "Forwarded To"]
    if is_admin:
        headers.insert(0, "User")

    data = [[_header_cell(h) for h in headers]]

    for lead in pending_leads:
        row = []
        if is_admin:
            row.append(_p(lead["user"]))
        row.extend([
            _p(lead["lead_id"]),
            _p(lead["party"]),
            _p(lead["contact"]),
            _p(lead["mobile"]),
            _p(lead["party_type"]),
            _p(lead["status"]),
            _p(lead["followup_date"]),
            _p(lead["followup_time"]),
            _p(lead["remarks"]),
            _p(lead["forwarded_to"]),
        ])
        data.append(row)

    col_count = len(headers)
    widths = [2.2, 2.6, 2.0, 1.8, 2.2, 2.0, 1.8, 1.6, 4.0, 1.8]
    if is_admin:
        widths = [1.8] + widths
    widths = widths[:col_count]
    total = sum(widths)
    col_widths = [(w / total) * (26.5 * cm) for w in widths]

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(_table_style())
    return table


def _table_style():
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ])


def _user_section_flowables(report_date, logs, pending_leads, is_admin, name=None, email=None):
    """Builds the 2-page (Activity Log + Missed Followups) section for one user/report."""
    flow = []

    if name or email:
        flow.append(Paragraph(name or "", TITLE_STYLE))
        if email:
            flow.append(Paragraph(email, SUBTITLE_STYLE))

    flow.append(Paragraph(f"Lead Activity Report &mdash; {report_date}", SECTION_STYLE))
    if logs:
        flow.append(_activity_table(logs, is_admin))
    else:
        flow.append(Paragraph("No leads or follow-ups recorded for this date.", EMPTY_STYLE))

    flow.append(PageBreak())

    flow.append(Paragraph(f"Missed Follow-ups &mdash; {report_date}", SECTION_STYLE))
    if pending_leads:
        flow.append(_followup_table(pending_leads, is_admin))
    else:
        flow.append(Paragraph("No missed follow-ups for this date.", EMPTY_STYLE))

    return flow


def generate_daily_log_pdf(report_date, logs, pending_leads, is_admin):
    """Single report (own leads, or all leads if requester is admin) with 2 pages."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        leftMargin=1 * cm,
        rightMargin=1 * cm,
    )

    story = _user_section_flowables(report_date, logs, pending_leads, is_admin)
    doc.build(story)

    buffer.seek(0)
    return buffer


def generate_all_users_daily_log_pdf(report_date, users_data):
    """
    Admin bulk export — one section per user (2 pages each), separated by a page break.
    users_data: list of dicts -> {"name": str, "email": str, "logs": [...], "pending_leads": [...]}
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        leftMargin=1 * cm,
        rightMargin=1 * cm,
    )

    story = []
    for index, user_data in enumerate(users_data):
        story.extend(
            _user_section_flowables(
                report_date,
                user_data["logs"],
                user_data["pending_leads"],
                is_admin=False,
                name=user_data["name"],
                email=user_data["email"],
            )
        )
        if index < len(users_data) - 1:
            story.append(PageBreak())

    if not users_data:
        story.append(Paragraph("No users with the leads role were found.", EMPTY_STYLE))

    doc.build(story)

    buffer.seek(0)
    return buffer
