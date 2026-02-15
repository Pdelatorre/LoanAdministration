from datetime import datetime
from typing import Dict, List
import os
import config

def generate_investor_statement(
    loan_id: str,
    loan_name: str,
    period_data: Dict,
    allocation_data: Dict,
    investor_id: str,
    company_name: str = None
) -> str:
    """
    Generate formatted investor distribution statement.
    
    Args:
        loan_id: Loan identifier
        loan_name: Borrower/loan name for display
        period_data: Period data from loan schedule
        allocation_data: Allocation data from allocate_period_to_investors()
        investor_id: Which investor to generate report for
        company_name: Your company name for header
    
    Returns:
        Formatted text report
    """

    # Use config default if not provided
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
    
    # Get ownership percentage (from last segment for simplicity)
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
    
    # Build report
    report = f"""
┌─────────────────────────────────────────────────────────────┐
│                    [{company_name}]                         │
│                 INVESTOR LOAN STATEMENT                     │
└─────────────────────────────────────────────────────────────┘

{investor['investor_name']}

Loan: {loan_name}
Period: {period_start} - {period_end}
Your Ownership: {investor_ownership:.2f}%

─────────────────────────────────────────────────────────────

TOTAL LOAN ACTIVITY

Effective    Beginning         Interest    Principal      Ending
Date         Principal         Income      Activity       Principal
             Balance                                      Balance
─────────────────────────────────────────────────────────────────
{effective_date:<12} ${period_data['principal_beginning']:>14,.2f}  ${period_data['interest_owed']:>10,.2f}                 ${period_data['principal_ending']:>14,.2f}
"""
    
    # Add prepayment activity if exists
    if period_data.get('prepayments'):
        report += "\n  Activity During Period:\n"
        for pp in period_data['prepayments']:
            pp_date = pp['payment_date'].strftime('%m/%d/%Y')
            report += f"    {pp_date} - Principal Prepayment      (${ pp['amount']:>12,.2f})\n"
    
    report += f"""
─────────────────────────────────────────────────────────────

YOUR ALLOCATION ({investor_ownership:.2f}%)

Effective    Beginning         Interest    Principal      Ending
Date         Principal         Income      Activity       Principal
             Balance                                      Balance
─────────────────────────────────────────────────────────────────
{effective_date:<12} ${investor['principal_beginning']:>14,.2f}  ${investor['interest']:>10,.2f}                 ${investor['principal_ending']:>14,.2f}
"""
    
    # Add investor's share of prepayments
    if investor['principal_prepayment'] > 0:
        report += "\n  Your Share of Activity:\n"
        if period_data.get('prepayments'):
            for pp in period_data['prepayments']:
                pp_date = pp['payment_date'].strftime('%m/%d/%Y')
                investor_pp = investor['principal_prepayment']
                report += f"    {pp_date} - Principal Prepayment      (${ investor_pp:>12,.2f})\n"
    
    # ADDITIONAL INCOME section (only show if fees exist)
    from fee_allocation import calculate_investor_fee_totals
    
    try:
        investor_fees = calculate_investor_fee_totals(
            loan_id, 
            period_data['period_number'], 
            investor_id
        )
        
        if investor_fees['total_fees'] > 0:
            report += f"""
─────────────────────────────────────────────────────────────

ADDITIONAL INCOME
"""
            for detail in investor_fees['fee_details']:
                fee_label = f"{detail['display_name']} ({detail['fee_date'].strftime('%b %d')}):"
                report += f"\n{fee_label:45} ${detail['investor_share']:>12,.2f}"
            
            report += f"\n{'':<45} {'─' * 16}"
            report += f"\nTotal Additional Income:{'':<21} ${investor_fees['total_fees']:>12,.2f}\n"
            
            total_additional = investor_fees['total_fees']
        else:
            total_additional = 0.00
    except:
        total_additional = 0.00
    
    # INCOME SUMMARY
    report += f"""
─────────────────────────────────────────────────────────────

INCOME SUMMARY

Interest Income:{'':<33} ${investor['interest']:>12,.2f}
"""
    
    if total_additional > 0:
        report += f"Additional Income:{'':<29} ${total_additional:>12,.2f}\n"
        report += f"{'':<45} {'─' * 16}\n"
    
    total_income = investor['interest'] + total_additional
    report += f"Total Income Earned:{'':<25} ${total_income:>12,.2f}\n"
    report += "\n─────────────────────────────────────────────────────────────\n"
    
    return report


def generate_all_investor_statements_for_loan(
    loan,
    period_data: dict,
    allocation_data: dict,
    output_dir: str = None,
    company_name: str = None
) -> list[str]:
    """
    Generate statements for all investors in a period.
    
    Args:
        loan: Loan object with loan_id and loan_name
        period_data: Period from schedule
        allocation_data: Allocation data
        output_dir: Where to save reports
        company_name: Company name for header
    
    Returns:
        List of filepaths to generated reports
    """

    # Use config defaults if not provided
    if output_dir is None:
        output_dir = config.INVESTOR_REPORTS_DIR
    if company_name is None:
        company_name = config.COMPANY_NAME
    
    os.makedirs(output_dir, exist_ok=True)
    
    filepaths = []
    
    for investor in allocation_data['investor_allocations']:
        report = generate_investor_statement(
            loan_id=loan.loan_id,
            loan_name=loan.loan_name,
            period_data=period_data,
            allocation_data=allocation_data,
            investor_id=investor['investor_id'],
            company_name=company_name
        )
        
        # Save to file
        period_num = allocation_data['period_number']
        filename = f"{loan.loan_id}_Period{period_num}_{investor['investor_id']}.txt"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(report)
        
        filepaths.append(filepath)
        print(f"✅ Generated report: {filename}")
    
    return filepaths