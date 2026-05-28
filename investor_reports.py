from datetime import datetime
from typing import Dict, List, Optional
import os
import config


def _compute_cumulative_for_investor(
    loan_id: str,
    schedule: List[Dict],
    current_period_num: int,
    investor_id: str,
) -> Dict:
    """
    Walk schedule periods 1..current_period_num and accumulate the investor's
    inception-to-date and calendar-YTD totals.

    Returns a dict with two sub-dicts ('inception', 'ytd') containing:
      cash_interest, pik_interest, total_interest, oid, fees,
      total_income, principal_returned
    plus 'ytd_year' (the calendar year the YTD column is keyed to).
    """
    from investor_allocation import allocate_period_to_investors
    from fee_allocation import calculate_investor_fee_totals

    current_period = schedule[current_period_num - 1]
    ytd_year = current_period['end_date'].year

    keys = ('cash_interest', 'pik_interest', 'total_interest',
            'oid', 'fees', 'total_income', 'principal_returned')
    inception = {k: 0.0 for k in keys}
    ytd = {k: 0.0 for k in keys}

    for period in schedule:
        if period['period_number'] > current_period_num:
            break

        try:
            alloc = allocate_period_to_investors(loan_id, period)
        except Exception:
            continue

        inv = next(
            (i for i in alloc['investor_allocations']
             if i['investor_id'] == investor_id),
            None
        )
        if inv is None:
            continue

        # OID share — pro-rate by this investor's interest share
        period_oid      = period.get('period_oid', 0.0)
        period_interest = period.get('interest_owed', 0.0)
        if period_oid > 0 and period_interest > 0:
            ratio = inv['interest'] / period_interest
            investor_oid = round(period_oid * ratio, 2)
        else:
            investor_oid = 0.0

        # Fee share for this period
        try:
            fee_result = calculate_investor_fee_totals(
                loan_id, period['period_number'], investor_id
            )
            investor_fees = fee_result['total_fees']
        except Exception:
            investor_fees = 0.0

        cash_int = inv.get('cash_interest', inv['interest'])
        pik_int  = inv.get('pik_interest', 0.0)
        tot_int  = inv['interest']
        prepay   = inv['principal_prepayment']
        total_income = tot_int + investor_oid + investor_fees

        increments = {
            'cash_interest':      cash_int,
            'pik_interest':       pik_int,
            'total_interest':     tot_int,
            'oid':                investor_oid,
            'fees':               investor_fees,
            'total_income':       total_income,
            'principal_returned': prepay,
        }

        for k, v in increments.items():
            inception[k] += v
            if period['end_date'].year == ytd_year:
                ytd[k] += v

    return {'inception': inception, 'ytd': ytd, 'ytd_year': ytd_year}


def generate_investor_statement(
    loan_id: str,
    loan_name: str,
    period_data: Dict,
    allocation_data: Dict,
    investor_id: str,
    company_name: str = None,
    cumulative_data: Optional[Dict] = None,
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

    # Period terms (rate disclosure)
    sofr_reset_date = period_data.get('sofr_reset_date')
    sofr_rate       = period_data.get('sofr_rate', 0.0) or 0.0
    margin          = period_data.get('margin', 0.0) or 0.0
    effective_rate  = period_data.get('effective_rate', 0.0) or 0.0
    sofr_floor      = period_data.get('sofr_floor', 0.0) or 0.0
    sofr_ceiling    = period_data.get('sofr_ceiling')
    days_in_period  = period_data.get('days', 0)

    reset_str = sofr_reset_date.strftime('%m/%d/%Y') if sofr_reset_date else 'N/A'
    has_floor   = sofr_floor and sofr_floor > 0
    has_ceiling = sofr_ceiling is not None and sofr_ceiling != float('inf')

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

PERIOD TERMS

"""
    report += (
        f"{'SOFR Reset Date:':<18}{reset_str:>12}   "
        f"{'Margin:':<17}{margin * 100:>9.4f}%\n"
    )
    report += (
        f"{'SOFR Rate:':<18}{sofr_rate * 100:>11.4f}%   "
        f"{'Day-Count:':<17}{'Actual/360':>10}\n"
    )
    report += (
        f"{'Effective Rate:':<18}{effective_rate * 100:>11.4f}%   "
        f"{'Days in Period:':<17}{days_in_period:>10}\n"
    )
    if has_floor:
        report += f"{'SOFR Floor:':<18}{sofr_floor * 100:>11.4f}%\n"
    if has_ceiling:
        report += f"{'SOFR Ceiling:':<18}{sofr_ceiling * 100:>11.4f}%\n"

    report += """
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

    # Cumulative totals — only shown when caller provides the data
    if cumulative_data:
        inc = cumulative_data['inception']
        ytd = cumulative_data['ytd']
        ytd_year = cumulative_data['ytd_year']

        def _fmt(v: float) -> str:
            return f"${v:>14,.2f}"

        report += "\nCUMULATIVE TOTALS\n\n"
        report += f"{'':26}{'Inception-to-Date':>16}  {'Calendar YTD ' + str(ytd_year):>16}\n"
        report += f"{'─' * 60}\n"

        rows = [
            ('Cash Interest',        inc['cash_interest'],      ytd['cash_interest'],      False),
            ('PIK Interest',         inc['pik_interest'],       ytd['pik_interest'],       False),
            ('  Total Interest',     inc['total_interest'],     ytd['total_interest'],     True),
            ('OID Amortized',        inc['oid'],                ytd['oid'],                False),
            ('Fee Income',           inc['fees'],               ytd['fees'],               False),
            ('  Total Income',       inc['total_income'],       ytd['total_income'],       True),
            ('Principal Returned',   inc['principal_returned'], ytd['principal_returned'], False),
        ]
        for label, inc_val, ytd_val, _ in rows:
            report += f"{label:<26}{_fmt(inc_val):>16}  {_fmt(ytd_val):>16}\n"

        report += "\n─────────────────────────────────────────────────────────────\n"

    return report


def generate_all_investor_statements_for_loan(
    loan,
    period_data: dict,
    allocation_data: dict,
    output_dir: str = None,
    company_name: str = None,
    schedule: Optional[List[Dict]] = None,
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

        # Pre-compute cumulative for this investor if schedule available
        cumulative_data = None
        if schedule is not None:
            cumulative_data = _compute_cumulative_for_investor(
                loan_id=loan.loan_id,
                schedule=schedule,
                current_period_num=allocation_data['period_number'],
                investor_id=investor['investor_id'],
            )

        report = generate_investor_statement(
            loan_id=loan.loan_id,
            loan_name=loan.loan_name,
            period_data=period_data,
            allocation_data=allocation_data,
            investor_id=investor['investor_id'],
            company_name=company_name,
            cumulative_data=cumulative_data,
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