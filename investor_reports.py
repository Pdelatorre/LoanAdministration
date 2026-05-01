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

    # Build report
    report = f"""
┌─────────────────────────────────────────────────────────────┐
│                    [{company_name}]                         │
│                 INVESTOR LOAN STATEMENT                     │
└─────────────────────────────────────────────────────────────┘

{investor['investor_name']}

Loan: {loan_name}
Period: {period_start} - {period_end}

─────────────────────────────────────────────────────────────

TOTAL LOAN ACTIVITY

"""
    if period_oid > 0:
        report += (
            "Effective    Beginning         Interest     OID          Ending\n"
            "Date         Principal         Income       Amortized    Principal\n"
            "             Balance                                     Balance\n"
            "─────────────────────────────────────────────────────────────\n"
            f"{effective_date:<12} ${period_data['principal_beginning']:>14,.2f}  "
            f"${period_data['interest_owed']:>10,.2f}  ${period_oid:>10,.2f}  "
            f"${period_data['principal_ending']:>14,.2f}\n"
        )
    else:
        report += (
            "Effective    Beginning         Interest          Ending\n"
            "Date         Principal         Income            Principal\n"
            "             Balance                             Balance\n"
            "─────────────────────────────────────────────────────────────\n"
            f"{effective_date:<12} ${period_data['principal_beginning']:>14,.2f}  "
            f"${period_data['interest_owed']:>10,.2f}                 "
            f"${period_data['principal_ending']:>14,.2f}\n"
        )
    report += "\n"

    # Add prepayment activity if exists
    if period_data.get('prepayments'):
        report += "\n  Activity During Period:\n"
        for pp in period_data['prepayments']:
            pp_date = pp['payment_date'].strftime('%m/%d/%Y')
            report += f"    {pp_date} - Principal Prepayment      (${ pp['amount']:>12,.2f})\n"

    # YOUR ALLOCATION section — per-segment rows
    multi_segment = len(investor_segments) > 1
    report += f"""
─────────────────────────────────────────────────────────────

YOUR ALLOCATION

Segment Dates               Ownership   Interest Income
─────────────────────────────────────────────────────────────
"""
    for seg in investor_segments:
        seg_start = seg['start_date'].strftime('%m/%d/%Y')
        seg_end   = seg['end_date'].strftime('%m/%d/%Y')
        report += f"{seg_start} - {seg_end}   {seg['ownership_pct']:>6.2f}%   ${seg['interest']:>12,.2f}\n"

    if multi_segment:
        report += f"{'':45} {'─' * 16}\n"
        report += f"{'Total Interest Income':45} ${investor['interest']:>12,.2f}\n"

    report += f"\n"
    report += f"{'Beginning Principal Balance:':45} ${investor['principal_beginning']:>12,.2f}\n"

    # Only show prepayment row if investor held ownership at period end (not exited).
    # Check the final segment's ownership — 0% means the investor exited mid-period.
    last_seg_pct = investor['segments'][-1]['ownership_pct'] if investor.get('segments') else 0
    if investor['principal_prepayment'] > 0 and last_seg_pct > 0:
        if period_data.get('prepayments'):
            for pp in period_data['prepayments']:
                pp_date = pp['payment_date'].strftime('%m/%d/%Y')
                investor_pp = investor['principal_prepayment']
                report += f"{'  Principal Prepayment (' + pp_date + '):':45} (${ investor_pp:>11,.2f})\n"

    report += f"{'Ending Principal Balance:':45} ${investor['principal_ending']:>12,.2f}\n"

    # OID Balance section — only shown when loan has OID
    if investor_oid > 0:
        report += "\n─────────────────────────────────────────────────────────────\n\n"
        report += "OID BALANCE\n\n"
        report += f"{'Unamortized OID — Beginning:':45} (${investor_oid_beginning:,.2f})\n"
        report += f"{'OID Amortized This Period:':45}   ${investor_oid:,.2f}\n"
        report += f"{'Unamortized OID — Ending:':45} (${investor_oid_ending:,.2f})\n"

    # Load fees for this period — will be merged into Income Summary below
    from fee_allocation import calculate_investor_fee_totals
    try:
        investor_fees = calculate_investor_fee_totals(
            loan_id,
            period_data['period_number'],
            investor_id
        )
        fee_details   = investor_fees['fee_details'] if investor_fees['total_fees'] > 0 else []
        total_fees    = investor_fees['total_fees']
    except:
        fee_details   = []
        total_fees    = 0.00

    # INCOME SUMMARY — interest breakout + fees + grand total
    pik_interest  = investor.get('pik_interest',  0.0)
    cash_interest = investor.get('cash_interest', investor['interest'])
    is_pik_period = period_data.get('pik_elected', False)

    report += f"""
─────────────────────────────────────────────────────────────

INCOME SUMMARY

"""
    if is_pik_period:
        report += f"Cash Interest:{'':<35} ${cash_interest:>12,.2f}\n"
        report += f"PIK Interest (capitalized to balance):{'':<11} ${pik_interest:>12,.2f}\n"
        report += f"{'':45} {'─' * 16}\n"
        report += f"Total Interest Income:{'':<27} ${investor['interest']:>12,.2f}\n"
    else:
        report += f"Interest Income:{'':<33} ${investor['interest']:>12,.2f}\n"

    # Fees inline — each on its own line with date
    for detail in fee_details:
        fee_label = f"{detail['display_name']} ({detail['fee_date'].strftime('%b %d')}):"
        report += f"{fee_label:45} ${detail['investor_share']:>12,.2f}\n"

    report += f"{'':45} {'─' * 16}\n"
    total_income = investor['interest'] + total_fees
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
        # Skip investors with no active (>0%) segments this period
        active_segments = [
            seg for seg in investor.get('segments', [])
            if seg['ownership_pct'] > 0
        ]
        if not active_segments:
            print(f"⏭️  Skipped {investor['investor_short_name']} — no ownership this period")
            continue

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
        filename = f"{loan.loan_name}_Period{period_num}_{investor['investor_short_name']}.txt"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)

        filepaths.append(filepath)
        print(f"✅ Generated report: {filename}")
    
    return filepaths