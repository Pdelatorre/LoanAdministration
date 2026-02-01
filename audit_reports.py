import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
from typing import Dict, List
import config
import os


def generate_audit_report(
    loan,
    schedule: List[Dict],
    loan_id: str,
    output_dir: str = None
) -> str:
    """
    Generate comprehensive Excel audit report.
    
    Creates multi-tab workbook with:
    - Loan summary
    - Period detail
    - Investor allocations
    - Payment ledger
    - Ownership history
    - Reconciliation
    
    Args:
        loan: Loan object
        schedule: Complete loan schedule
        loan_id: Loan identifier
        output_dir: Where to save report
    
    Returns:
        Path to generated Excel file
    """
    if output_dir is None:
        output_dir = config.AUDIT_REPORTS_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Create workbook
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Remove default sheet
    
    # Tab 1: Loan Summary
    _create_loan_summary_tab(wb, loan, schedule)
    
    # Tab 2: Interest Period Detail
    _create_period_detail_tab(wb, schedule)
    
    # Tab 3: Investor Allocations
    _create_investor_allocations_tab(wb, loan_id, schedule)
    
    # Tab 4: Payment Ledger
    _create_payment_ledger_tab(wb, loan_id)
    
    # Tab 5: Ownership History
    _create_ownership_history_tab(wb, loan_id)
    
    # Tab 6: Reconciliation
    _create_reconciliation_tab(wb, loan_id, schedule)
    
    # Save workbook
    timestamp = datetime.now().strftime('%Y%m%d')
    filename = f"{loan_id}_Audit_Report_{timestamp}.xlsx"
    filepath = os.path.join(output_dir, filename)
    
    wb.save(filepath)
    
    print(f"✅ Generated audit report: {filename}")
    return filepath


def _create_loan_summary_tab(wb, loan, schedule):
    """Create Loan Summary tab."""
    ws = wb.create_sheet("Loan Summary")
    
    # Header styling
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, size=12)
    
    # Title
    ws['A1'] = "LOAN SUMMARY"
    ws['A1'].font = Font(bold=True, size=14)
    ws.merge_cells('A1:B1')
    
    # Loan details
    row = 3
    details = [
        ("Loan ID:", loan.loan_id),
        ("Borrower:", loan.borrower),
        ("Loan Name:", loan.loan_name),
        ("Principal Amount:", f"${loan.principal:,.2f}"),
        ("Margin:", f"{loan.margin * 100:.2f}%"),
        ("SOFR Floor:", f"{loan.sofr_floor * 100:.2f}%"),
        ("Origination Date:", loan.origination_date.strftime('%Y-%m-%d')),
        ("Maturity Date:", loan.maturity_date.strftime('%Y-%m-%d')),
        ("", ""),
        ("Total Periods:", len(schedule)),
        ("Total Interest:", f"${sum(p['interest_owed'] for p in schedule):,.2f}"),
        ("Current Principal:", f"${schedule[-1]['principal_ending']:,.2f}"),
    ]
    
    for label, value in details:
        ws[f'A{row}'] = label
        ws[f'A{row}'].font = Font(bold=True)
        ws[f'B{row}'] = value
        row += 1
    
    # Column widths
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 30


def _create_period_detail_tab(wb, schedule):
    """Create Interest Period Detail tab."""
    ws = wb.create_sheet("Period Detail")
    
    # Headers
    headers = [
        "Period", "Start Date", "End Date", "Days", 
        "Principal Beginning", "SOFR Rate", "Margin", "Effective Rate",
        "Interest Owed", "Interest Paid", "Principal Ending", "Status"
    ]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        cell.alignment = Alignment(horizontal="center")
    
    # Data rows
    for row, period in enumerate(schedule, 2):
        ws.cell(row=row, column=1, value=period['period_number'])
        ws.cell(row=row, column=2, value=period['start_date'].strftime('%Y-%m-%d'))
        ws.cell(row=row, column=3, value=period['end_date'].strftime('%Y-%m-%d'))
        ws.cell(row=row, column=4, value=period['days'])
        ws.cell(row=row, column=5, value=period['principal_beginning'])
        ws.cell(row=row, column=6, value=period.get('sofr_rate', 0))
        ws.cell(row=row, column=7, value=period.get('margin', 0))
        ws.cell(row=row, column=8, value=period.get('effective_rate', 0))
        ws.cell(row=row, column=9, value=period['interest_owed'])
        ws.cell(row=row, column=10, value=period.get('interest_paid', 0))
        ws.cell(row=row, column=11, value=period['principal_ending'])
        # Determine status based on payment
        payment_status = period.get('payment_status')

        if payment_status == 'Paid':
            status = 'Final'
        elif payment_status == 'Partially Paid':
            status = 'Partially Paid'
        elif payment_status == 'Unpaid':
            status = 'Unpaid'
        else:
            status = 'Projected'

        ws.cell(row=row, column=12, value=status)
        
        # Format currency columns
        for col in [5, 9, 10, 11]:
            ws.cell(row=row, column=col).number_format = '$#,##0.00'
        
        # Format percentage columns
        for col in [6, 7, 8]:
            ws.cell(row=row, column=col).number_format = '0.00%'
    
    # Auto-width columns
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 15


def _create_investor_allocations_tab(wb, loan_id, schedule):
    """Create Investor Allocations tab."""
    from investors import load_investors
    from investor_allocation import allocate_period_to_investors
    
    ws = wb.create_sheet("Investor Allocations")
    
    # Headers
    headers = [
        "Period", "Investor ID", "Investor Name", "Ownership %",
        "Principal Begin", "Interest Income", "Prepayment", "Principal End"
    ]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        cell.alignment = Alignment(horizontal="center")
    
    # Data rows
    row = 2
    for period in schedule:
        try:
            allocation = allocate_period_to_investors(loan_id, period)
            
            for investor in allocation['investor_allocations']:
                ws.cell(row=row, column=1, value=period['period_number'])
                ws.cell(row=row, column=2, value=investor['investor_id'])
                ws.cell(row=row, column=3, value=investor['investor_name'])
                
                # Get ownership % from last segment
                last_segment = allocation['ownership_segments'][-1]
                ownership = next(
                    (inv['ownership_pct'] for inv in last_segment['investors'] 
                     if inv['investor_id'] == investor['investor_id']),
                    0.0
                )
                ws.cell(row=row, column=4, value=ownership / 100)
                
                ws.cell(row=row, column=5, value=investor['principal_beginning'])
                ws.cell(row=row, column=6, value=investor['interest'])
                ws.cell(row=row, column=7, value=investor['principal_prepayment'])
                ws.cell(row=row, column=8, value=investor['principal_ending'])
                
                # Format currency columns
                for col in [5, 6, 7, 8]:
                    ws.cell(row=row, column=col).number_format = '$#,##0.00'
                
                # Format percentage
                ws.cell(row=row, column=4).number_format = '0.00%'
                
                row += 1
        except:
            # No investors for this loan
            pass
    
    # Auto-width columns
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 18


def _create_payment_ledger_tab(wb, loan_id):
    """Create Payment Ledger tab."""
    from payments import load_payments
    
    ws = wb.create_sheet("Payment Ledger")
    
    # Headers
    headers = ["Date", "Type", "Amount", "Period", "Notes"]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        cell.alignment = Alignment(horizontal="center")
    
    # Load payments
    payments = load_payments(loan_id)
    
    # Data rows
    for row, payment in enumerate(payments, 2):
        ws.cell(row=row, column=1, value=payment['payment_date'].strftime('%Y-%m-%d'))
        ws.cell(row=row, column=2, value=payment['payment_type'])
        ws.cell(row=row, column=3, value=payment['amount'])
        ws.cell(row=row, column=4, value=payment.get('period', ''))
        ws.cell(row=row, column=5, value=payment.get('notes', ''))
        
        # Format currency
        ws.cell(row=row, column=3).number_format = '$#,##0.00'
    
    # Auto-width columns
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 20


def _create_ownership_history_tab(wb, loan_id):
    """Create Ownership History tab."""
    from investors import load_investors
    
    ws = wb.create_sheet("Ownership History")
    
    # Headers
    headers = ["Effective Date", "Investor ID", "Investor Name", "Ownership %"]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        cell.alignment = Alignment(horizontal="center")
    
    # Load investors
    investors = load_investors(loan_id)
    
    # Data rows
    for row, investor in enumerate(investors, 2):
        ws.cell(row=row, column=1, value=investor['effective_date'].strftime('%Y-%m-%d'))
        ws.cell(row=row, column=2, value=investor['investor_id'])
        ws.cell(row=row, column=3, value=investor['investor_name'])
        ws.cell(row=row, column=4, value=investor['ownership_pct'] / 100)
        
        # Format percentage
        ws.cell(row=row, column=4).number_format = '0.00%'
    
    # Auto-width columns
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 20


def _create_reconciliation_tab(wb, loan_id, schedule):
    """Create Reconciliation tab."""
    from investors import load_investors
    from investor_allocation import allocate_period_to_investors
    
    ws = wb.create_sheet("Reconciliation")
    
    # Title
    ws['A1'] = "RECONCILIATION CHECKS"
    ws['A1'].font = Font(bold=True, size=14)
    
    row = 3
    
    # Check 1: Interest allocations sum to period totals
    ws[f'A{row}'] = "Check 1: Interest Allocations = Period Totals"
    ws[f'A{row}'].font = Font(bold=True)
    row += 1
    
    for period in schedule:
        try:
            allocation = allocate_period_to_investors(loan_id, period)
            total_allocated = sum(inv['interest'] for inv in allocation['investor_allocations'])
            period_interest = period['interest_owed']
            match = abs(total_allocated - period_interest) < 0.01
            
            ws[f'A{row}'] = f"Period {period['period_number']}"
            ws[f'B{row}'] = period_interest
            ws[f'C{row}'] = total_allocated
            ws[f'D{row}'] = "✓" if match else "✗"
            ws[f'D{row}'].font = Font(color="00FF00" if match else "FF0000", bold=True)
            
            row += 1
        except:
            pass
    
    # Column widths
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 20
    ws.column_dimensions['D'].width = 10