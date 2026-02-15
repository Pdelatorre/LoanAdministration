from datetime import datetime
from typing import Dict
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
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
    
    # Get ownership percentage
    last_segment = allocation_data['ownership_segments'][-1]
    investor_ownership = next(
        (inv['ownership_pct'] for inv in last_segment['investors'] 
         if inv['investor_id'] == investor_id),
        0.0
    )
    
    # Format dates
    period_start = allocation_data['period_start'].strftime('%B %d, %Y')
    period_end = allocation_data['period_end'].strftime('%B %d, %Y')
    effective_date = allocation_data['period_end'].strftime('%m/%d/%Y')
    
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
        textColor=colors.HexColor('#333333'),
        spaceAfter=6,
        alignment=TA_CENTER
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#333333'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading3'],
        fontSize=11,
        textColor=colors.HexColor('#333333'),
        spaceAfter=6,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#333333')
    )
    
    # Header Box
    header_data = [
        [Paragraph(f"[{company_name}]", title_style)],
        [Paragraph("INVESTOR LOAN STATEMENT", subtitle_style)]
    ]
    
    header_table = Table(header_data, colWidths=[6.5*inch])
    header_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#333333')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    
    elements.append(header_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Investor Name
    elements.append(Paragraph(f"<b>{investor['investor_name']}</b>", heading_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Loan Info
    loan_info = f"""
    <b>Loan:</b> {loan_name}<br/>
    <b>Period:</b> {period_start} - {period_end}<br/>
    <b>Your Ownership:</b> {investor_ownership:.2f}%
    """
    elements.append(Paragraph(loan_info, normal_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Total Loan Activity Section
    elements.append(Paragraph("TOTAL LOAN ACTIVITY", heading_style))
    
    loan_table_data = [
        ['Effective\nDate', 'Beginning\nPrincipal', 'Interest\nIncome', 'Principal\nActivity', 'Ending\nPrincipal'],
        [
            effective_date,
            f"${period_data['principal_beginning']:,.2f}",
            f"${period_data['interest_owed']:,.2f}",
            "-",
            f"${period_data['principal_ending']:,.2f}"
        ]
    ]
    
    # Add prepayment rows if exist
    if period_data.get('prepayments'):
        loan_table_data.append(['Activity During Period:', '', '', '', ''])
        for pp in period_data['prepayments']:
            pp_date = pp['payment_date'].strftime('%m/%d/%Y')
            loan_table_data.append([
                f"  {pp_date} - Principal Prepayment",
                '',
                '',
                f"(${ pp['amount']:,.2f})",
                ''
            ])
    
    loan_table = Table(loan_table_data, colWidths=[1.3*inch, 1.3*inch, 1.3*inch, 1.3*inch, 1.3*inch])
    loan_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#333333')),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))
    
    elements.append(loan_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Your Allocation Section
    elements.append(Paragraph(f"YOUR ALLOCATION ({investor_ownership:.2f}%)", heading_style))
    
    investor_table_data = [
        ['Effective\nDate', 'Beginning\nPrincipal', 'Interest\nIncome', 'Principal\nActivity', 'Ending\nPrincipal'],
        [
            effective_date,
            f"${investor['principal_beginning']:,.2f}",
            f"${investor['interest']:,.2f}",
            "-",
            f"${investor['principal_ending']:,.2f}"
        ]
    ]
    
    # Add investor prepayment rows if exist
    if investor['principal_prepayment'] > 0:
        investor_table_data.append(['Your Share of Activity:', '', '', '', ''])
        if period_data.get('prepayments'):
            for pp in period_data['prepayments']:
                pp_date = pp['payment_date'].strftime('%m/%d/%Y')
                investor_pp = investor['principal_prepayment']
                investor_table_data.append([
                    f"  {pp_date} - Principal Prepayment",
                    '',
                    '',
                    f"(${ investor_pp:,.2f})",
                    ''
                ])
    
    investor_table = Table(investor_table_data, colWidths=[1.3*inch, 1.3*inch, 1.3*inch, 1.3*inch, 1.3*inch])
    investor_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#333333')),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))
    
    elements.append(investor_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # ADDITIONAL INCOME - Dynamic fee loading
    from fee_allocation import calculate_investor_fee_totals

    try:
        investor_fees = calculate_investor_fee_totals(
            loan_id, 
            period_data['period_number'], 
            investor_id
        )
        
        if investor_fees['total_fees'] > 0:
            elements.append(Paragraph("ADDITIONAL INCOME", heading_style))
            
            fee_data = []
            
            # Add each fee type with date
            for detail in investor_fees['fee_details']:
                fee_label = f"{detail['display_name']} ({detail['fee_date'].strftime('%b %d')}):"
                fee_data.append([fee_label, f"${detail['investor_share']:,.2f}"])
            
            # Total additional income
            fee_data.append(['Total Additional Income:', f"${investor_fees['total_fees']:,.2f}"])
            
            fee_table = Table(fee_data, colWidths=[4.5*inch, 2*inch])
            fee_table.setStyle(TableStyle([
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#333333')),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            
            elements.append(fee_table)
            elements.append(Spacer(1, 0.2*inch))
            
            # Store for distribution summary
            total_additional = investor_fees['total_fees']
        else:
            total_additional = 0.00
    except:
        # No fees for this period or fee system not available
        total_additional = 0.00
    
    # INCOME SUMMARY
    elements.append(Paragraph("INCOME SUMMARY", heading_style))

    summary_data = [
        ['Interest Income:', f"${investor['interest']:,.2f}"]
    ]

    # Add additional income if exists
    if total_additional > 0:
        summary_data.append(['Additional Income:', f"${total_additional:,.2f}"])

    # Total income earned
    total_income = investor['interest'] + total_additional
    summary_data.append(['Total Income Earned:', f"${total_income:,.2f}"])

    summary_table = Table(summary_data, colWidths=[4.5*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#333333')),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

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
        period_num = allocation_data['period_number']
        filename = f"{loan.loan_id}_Period{period_num}_{investor['investor_id']}.pdf"
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