from datetime import datetime
from typing import Dict
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import config


def generate_investor_statement_pdf(
    loan_id: str,
    loan_name: str,
    period_data: Dict,
    allocation_data: Dict,
    investor_id: str,
    output_path: str,
    company_name: str = None
) -> str:
    """
    Generate PDF investor distribution statement using reportlab.
    
    Args:
        loan_id: Loan identifier
        loan_name: Display name for loan
        period_data: Period data from schedule
        allocation_data: Allocation data
        investor_id: Which investor
        output_path: Where to save PDF
        company_name: Company name for header
    
    Returns:
        Path to generated PDF
    """
    if company_name is None:
        company_name = config.COMPANY_NAME
    
    # Find investor allocation
    investor = next(
        (inv for inv in allocation_data['investor_allocations'] 
         if inv['investor_id'] == investor_id),
        None
    )
    
    if not investor:
        raise ValueError(f"Investor {investor_id} not found in allocation data")
    
    # Get investor's active segments (ownership > 0%) for this period
    investor_segments = [
        seg for seg in investor.get('segments', [])
        if seg['ownership_pct'] > 0
    ]

    # Format dates
    period_start = allocation_data['period_start'].strftime('%B %d, %Y')
    period_end = allocation_data['period_end'].strftime('%B %d, %Y')
    effective_date = allocation_data['period_end'].strftime('%m/%d/%Y')

    # OID values — prorated to this investor by their interest share
    period_oid = period_data.get('period_oid', 0.0)
    total_period_interest = period_data.get('interest_owed', 0.0)
    oid_unamortized_start = period_data.get('oid_unamortized_start', 0.0)
    if period_oid > 0 and total_period_interest > 0:
        ownership_ratio = investor['interest'] / total_period_interest
        investor_oid = round(period_oid * ownership_ratio, 2)
        investor_oid_beginning = round(oid_unamortized_start * ownership_ratio, 2)
        investor_oid_ending = round(investor_oid_beginning - investor_oid, 2)
    else:
        investor_oid = 0.0
        investor_oid_beginning = 0.0
        investor_oid_ending = 0.0

    # Create PDF
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                          topMargin=0.75*inch, bottomMargin=0.75*inch,
                          leftMargin=0.75*inch, rightMargin=0.75*inch)
    
    # Container for elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.black,
        spaceAfter=6,
        alignment=TA_CENTER
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.black,
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading3'],
        fontSize=11,
        textColor=colors.black,
        spaceAfter=6,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black
    )
    
    # Header - Simple, no box
    elements.append(Paragraph(f"{company_name}", title_style))
    elements.append(Paragraph("INVESTOR LOAN STATEMENT", subtitle_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Investor Name
    elements.append(Paragraph(f"<b>{investor['investor_name']}</b>", heading_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Loan Info
    loan_info = f"""
    <b>Loan:</b> {loan_name}<br/>
    <b>Period:</b> {period_start} - {period_end}
    """
    elements.append(Paragraph(loan_info, normal_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Total Loan Activity Section
    elements.append(Paragraph("TOTAL LOAN ACTIVITY", heading_style))
    
    if period_oid > 0:
        loan_table_data = [
            ['Effective\nDate', 'Beginning\nPrincipal', 'Interest\nIncome', 'OID\nAmortized', 'Ending\nPrincipal'],
            [
                effective_date,
                f"${period_data['principal_beginning']:,.2f}",
                f"${period_data['interest_owed']:,.2f}",
                f"${period_oid:,.2f}",
                f"${period_data['principal_ending']:,.2f}"
            ]
        ]
    else:
        loan_table_data = [
            ['Effective\nDate', 'Beginning\nPrincipal', 'Interest\nIncome', 'Ending\nPrincipal'],
            [
                effective_date,
                f"${period_data['principal_beginning']:,.2f}",
                f"${period_data['interest_owed']:,.2f}",
                f"${period_data['principal_ending']:,.2f}"
            ]
        ]

    # Add prepayment rows if exist
    if period_data.get('prepayments'):
        for pp in period_data['prepayments']:
            pp_date = pp['payment_date'].strftime('%m/%d/%Y')
            if period_oid > 0:
                loan_table_data.append([f"{pp_date} - Principal Prepayment", '', '', '', f"(${pp['amount']:,.2f})"])
            else:
                loan_table_data.append([f"{pp_date} - Principal Prepayment", '', '', f"(${pp['amount']:,.2f})"])

    if period_oid > 0:
        loan_table = Table(loan_table_data, colWidths=[1.0*inch, 1.5*inch, 1.3*inch, 1.2*inch, 1.5*inch])
    else:
        loan_table = Table(loan_table_data, colWidths=[1.2*inch, 1.8*inch, 1.5*inch, 1.9*inch])
    loan_table.setStyle(TableStyle([
        # Header row - bold with underline
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        
        # Data rows - clean, no lines
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))
    
    elements.append(loan_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Your Allocation Section — per-segment rows
    elements.append(Paragraph("YOUR ALLOCATION", heading_style))

    multi_segment = len(investor_segments) > 1

    # Header row
    alloc_table_data = [['Segment Dates', 'Ownership', 'Interest\nIncome']]

    for seg in investor_segments:
        seg_label = (f"{seg['start_date'].strftime('%m/%d/%Y')} - "
                     f"{seg['end_date'].strftime('%m/%d/%Y')}")
        alloc_table_data.append([
            seg_label,
            f"{seg['ownership_pct']:.2f}%",
            f"${seg['interest']:,.2f}",
        ])

    # Total row if multiple segments
    if multi_segment:
        alloc_table_data.append([
            'Total Interest Income',
            '',
            f"${investor['interest']:,.2f}",
        ])

    alloc_table = Table(alloc_table_data, colWidths=[3.0*inch, 1.2*inch, 1.5*inch])
    alloc_style_cmds = [
        # Header
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        # Data rows
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
    ]
    if multi_segment:
        # Bold total row and put a line above it
        total_row_idx = len(alloc_table_data) - 1
        alloc_style_cmds += [
            ('FONTNAME', (0, total_row_idx), (-1, total_row_idx), 'Helvetica-Bold'),
            ('LINEABOVE', (0, total_row_idx), (-1, total_row_idx), 0.5, colors.black),
        ]
    alloc_table.setStyle(TableStyle(alloc_style_cmds))

    elements.append(alloc_table)
    elements.append(Spacer(1, 0.1*inch))

    # Principal summary below segment table
    # Only show prepayment row if investor still held ownership at period end (not exited)
    last_seg_pct = investor['segments'][-1]['ownership_pct'] if investor.get('segments') else 0
    principal_data = [
        ['Beginning Principal Balance:', f"${investor['principal_beginning']:,.2f}"],
    ]
    if investor['principal_prepayment'] > 0 and last_seg_pct > 0:
        if period_data.get('prepayments'):
            for pp in period_data['prepayments']:
                pp_date = pp['payment_date'].strftime('%m/%d/%Y')
                principal_data.append([
                    f"Principal Prepayment ({pp_date}):",
                    f"(${investor['principal_prepayment']:,.2f})"
                ])
    principal_data.append(['Ending Principal Balance:', f"${investor['principal_ending']:,.2f}"])

    principal_table = Table(principal_data, colWidths=[3.5*inch, 2.0*inch])
    principal_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(principal_table)

    # OID Balance section — only shown when loan has OID
    if investor_oid > 0:
        elements.append(Spacer(1, 0.15*inch))
        elements.append(Paragraph("OID BALANCE", heading_style))
        oid_data = [
            ['Unamortized OID — Beginning:', f"(${investor_oid_beginning:,.2f})"],
            ['OID Amortized This Period:', f"${investor_oid:,.2f}"],
            ['Unamortized OID — Ending:', f"(${investor_oid_ending:,.2f})"],
        ]
        oid_table = Table(oid_data, colWidths=[3.5*inch, 2.0*inch])
        oid_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(oid_table)

    elements.append(Spacer(1, 0.2*inch))

    # Load fees — merged into Income Summary below (no separate Additional Income section)
    from fee_allocation import calculate_investor_fee_totals
    try:
        investor_fees = calculate_investor_fee_totals(
            loan_id,
            period_data['period_number'],
            investor_id
        )
        fee_details = investor_fees['fee_details'] if investor_fees['total_fees'] > 0 else []
        total_fees  = investor_fees['total_fees']
    except:
        fee_details = []
        total_fees  = 0.00

    # INCOME SUMMARY — interest breakout + fees inline + grand total
    elements.append(Paragraph("INCOME SUMMARY", heading_style))

    pik_interest  = investor.get('pik_interest',  0.0)
    cash_interest = investor.get('cash_interest', investor['interest'])
    is_pik_period = period_data.get('pik_elected', False)

    summary_data = []

    if is_pik_period:
        summary_data.append(['Cash Interest:', f"${cash_interest:,.2f}"])
        summary_data.append(['PIK Interest (capitalized to balance):', f"${pik_interest:,.2f}"])
        summary_data.append(['Total Interest Income:', f"${investor['interest']:,.2f}"])
    else:
        summary_data.append(['Interest Income:', f"${investor['interest']:,.2f}"])

    # Each fee on its own line with date — no separate section header
    for detail in fee_details:
        fee_label = f"{detail['display_name']} ({detail['fee_date'].strftime('%b %d')}):"
        summary_data.append([fee_label, f"${detail['investor_share']:,.2f}"])

    # Grand total
    total_income = investor['interest'] + total_fees
    summary_data.append(['Total Income Earned:', f"${total_income:,.2f}"])

    # Style: bold + line above grand total row; if PIK, also bold+underline interest subtotal
    summary_table = Table(summary_data, colWidths=[4.5*inch, 2*inch])
    table_style_cmds = [
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]
    if is_pik_period:
        # Bold + thin line above the interest subtotal row (index 2)
        table_style_cmds += [
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
            ('LINEABOVE', (0, 2), (-1, 2), 0.5, colors.black),
        ]
    summary_table.setStyle(TableStyle(table_style_cmds))

    elements.append(summary_table)

    # Build PDF
    doc.build(elements)

    return output_path


def generate_all_investor_pdfs(
    loan,
    period_data: Dict,
    allocation_data: Dict,
    output_dir: str = None,
    company_name: str = None
) -> list:
    """
    Generate PDF statements for all investors.
    
    Returns list of PDF filepaths.
    """
    if output_dir is None:
        output_dir = config.INVESTOR_REPORTS_PDF_DIR
    if company_name is None:
        company_name = config.COMPANY_NAME
    
    os.makedirs(output_dir, exist_ok=True)
    
    filepaths = []
    
    for investor in allocation_data['investor_allocations']:
        # Skip investors with no active (>0%) segments this period
        active_segments = [
            seg for seg in investor.get('segments', [])
            if seg['ownership_pct'] > 0
        ]
        if not active_segments:
            investor_short = investor.get('investor_short_name', investor['investor_id'])
            print(f"⏭️  Skipped PDF for {investor_short} — no ownership this period")
            continue

        period_num = allocation_data['period_number']
        investor_short = investor.get('investor_short_name', investor['investor_id'])
        filename = f"{loan.loan_name}_Period{period_num}_{investor_short}.pdf"
        filepath = os.path.join(output_dir, filename)

        generate_investor_statement_pdf(
            loan_id=loan.loan_id,
            loan_name=loan.loan_name,
            period_data=period_data,
            allocation_data=allocation_data,
            investor_id=investor['investor_id'],
            output_path=filepath,
            company_name=company_name
        )

        filepaths.append(filepath)
        print(f"✅ Generated PDF: {filename}")
    
    return filepaths