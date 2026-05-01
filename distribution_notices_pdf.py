from datetime import datetime
from typing import Dict, List, Optional
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import config


def generate_investor_notice_pdf(
    loan_name: str,
    period_number: int,
    period_start: datetime,
    period_end: datetime,
    notice_type: str,
    investor: Dict,
    effective_date: datetime,
    description: str,
    output_path: str,
    wire_ref: Optional[str] = None,
    original_statement_date: Optional[datetime] = None,
    company_name: str = None
) -> str:
    """
    Generate a PDF distribution notice for one investor.

    Args:
        notice_type:             'interim' or 'supplemental'
        investor:                Entry from allocate_notice_to_investors()
        original_statement_date: Context for supplemental notices
    """
    if company_name is None:
        company_name = config.COMPANY_NAME

    notice_date = datetime.now()
    type_display = (
        'INTERIM DISTRIBUTION NOTICE'
        if notice_type == 'interim'
        else 'SUPPLEMENTAL DISTRIBUTION NOTICE'
    )

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        topMargin=0.75*inch, bottomMargin=0.75*inch,
        leftMargin=0.75*inch, rightMargin=0.75*inch
    )

    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'NoticeTitle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.black,
        spaceAfter=4,
        alignment=TA_CENTER
    )
    subtitle_style = ParagraphStyle(
        'NoticeSubtitle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.black,
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    heading_style = ParagraphStyle(
        'NoticeHeading',
        parent=styles['Heading3'],
        fontSize=11,
        textColor=colors.black,
        spaceAfter=6,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    normal_style = ParagraphStyle(
        'NoticeNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black
    )
    note_style = ParagraphStyle(
        'NoticeNote',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.black,
        fontName='Helvetica-Oblique'
    )

    # Header
    elements.append(Paragraph(company_name, title_style))
    elements.append(Paragraph(type_display, subtitle_style))
    elements.append(Spacer(1, 0.15*inch))

    # Investor name
    elements.append(Paragraph(f"<b>{investor['investor_name']}</b>", heading_style))
    elements.append(Spacer(1, 0.1*inch))

    # Loan / period meta
    if original_statement_date and notice_type == 'supplemental':
        stmt_str = original_statement_date.strftime('%B %d, %Y')
        meta_extra = f"<br/><b>Supplements Statement Dated:</b> {stmt_str}"
    else:
        meta_extra = ""

    meta = (
        f"<b>Loan:</b> {loan_name}<br/>"
        f"<b>Period:</b> {period_start.strftime('%B %d, %Y')} - {period_end.strftime('%B %d, %Y')}<br/>"
        f"<b>Notice Date:</b> {notice_date.strftime('%B %d, %Y')}<br/>"
        f"<b>Effective Date:</b> {effective_date.strftime('%B %d, %Y')}"
        f"{meta_extra}"
    )
    elements.append(Paragraph(meta, normal_style))
    elements.append(Spacer(1, 0.2*inch))

    # Context note
    if notice_type == 'interim':
        note_text = (
            f"This notice confirms a distribution made outside of the regular period-end "
            f"statement. This amount will be reflected in the Period {period_number} "
            f"statement issued at period close."
        )
    else:
        if original_statement_date:
            stmt_str = original_statement_date.strftime('%B %d, %Y').upper()
        else:
            stmt_str = period_end.strftime('%B %d, %Y').upper()
        note_text = (
            f"<b>SUPPLEMENT TO PERIOD {period_number} STATEMENT DATED {stmt_str}</b><br/>"
            "This notice documents additional activity not reflected in the original "
            "period statement referenced above."
        )
    elements.append(Paragraph(note_text, note_style))
    elements.append(Spacer(1, 0.2*inch))

    # Distribution detail section
    elements.append(Paragraph("DISTRIBUTION DETAIL", heading_style))

    detail_rows = [['Description:', description]]
    if wire_ref:
        detail_rows.append(['Wire Reference:', wire_ref])

    detail_table = Table(detail_rows, colWidths=[1.8*inch, 4.7*inch])
    detail_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN',   (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(detail_table)
    elements.append(Spacer(1, 0.2*inch))

    # Your allocation section
    elements.append(Paragraph("YOUR ALLOCATION", heading_style))

    eff_label = f"Ownership ({effective_date.strftime('%m/%d/%Y')}):"
    alloc_rows = [
        [eff_label, f"{investor['ownership_pct']:.2f}%"],
        ['Distribution Amount:', f"${investor['amount']:,.2f}"],
    ]
    alloc_table = Table(alloc_rows, colWidths=[3.5*inch, 2.0*inch])
    alloc_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
        ('ALIGN',  (1, 0), (1, -1), 'RIGHT'),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(alloc_table)

    doc.build(elements)
    return output_path


def generate_all_investor_notice_pdfs(
    loan_id: str,
    loan_name: str,
    period_number: int,
    period_start: datetime,
    period_end: datetime,
    notice_type: str,
    effective_date: datetime,
    description: str,
    total_amount: float,
    wire_ref: Optional[str] = None,
    original_statement_date: Optional[datetime] = None,
    output_dir: str = None,
    company_name: str = None
) -> List[str]:
    """
    Generate PDF distribution notices for all investors.

    Returns list of file paths written.
    """
    if output_dir is None:
        output_dir = config.DISTRIBUTION_NOTICES_PDF_DIR
    if company_name is None:
        company_name = config.COMPANY_NAME

    os.makedirs(output_dir, exist_ok=True)

    from distribution_notices import allocate_notice_to_investors
    allocations = allocate_notice_to_investors(loan_id, effective_date, total_amount)

    type_label = 'Interim' if notice_type == 'interim' else 'Supplemental'
    date_str = effective_date.strftime('%Y-%m-%d')

    filepaths = []
    for investor in allocations:
        filename = (
            f"{loan_name}_Period{period_number}_"
            f"{type_label}_{date_str}_{investor['investor_short_name']}.pdf"
        )
        filepath = os.path.join(output_dir, filename)

        generate_investor_notice_pdf(
            loan_name=loan_name,
            period_number=period_number,
            period_start=period_start,
            period_end=period_end,
            notice_type=notice_type,
            investor=investor,
            effective_date=effective_date,
            description=description,
            output_path=filepath,
            wire_ref=wire_ref,
            original_statement_date=original_statement_date,
            company_name=company_name,
        )

        filepaths.append(filepath)
        print(f"✅ Generated PDF notice: {filename}")

    return filepaths
