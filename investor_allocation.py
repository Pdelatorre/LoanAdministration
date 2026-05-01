from datetime import datetime
from typing import List, Dict
from investors import get_ownership_for_period
from interest_calculations import penny_round


def allocate_period_to_investors(
    loan_id: str,
    period_data: Dict,
    investors_filepath: str = "data/investors.csv"
) -> Dict:
    """
    Allocate all period activity to investors based on ownership.
    
    Handles ownership changes during the period by creating segments.
    
    Args:
        loan_id: The loan identifier
        period_data: Period data from loan schedule
        investors_filepath: Path to investors CSV
    
    Returns:
        {
            'period_number': int,
            'period_start': datetime,
            'period_end': datetime,
            'ownership_segments': [...],  # Ownership breakdown by date range
            'investor_allocations': [...]  # Total allocation per investor
        }
    """
    period_start = period_data['start_date']
    period_end = period_data['end_date']
    
    # Get ownership segments for this period
    ownership_segments = get_ownership_for_period(
        loan_id, 
        period_start, 
        period_end, 
        investors_filepath
    )
    
    total_days = sum(seg['days'] for seg in ownership_segments)

    # Determine PIK vs cash split at the period level (already penny-rounded in loan.py)
    total_interest = period_data['interest_owed']
    total_pik      = round(period_data.get('pik_amount', 0.0), 2)
    total_cash_int = round(total_interest - total_pik, 2)

    # Allocate each type of activity
    investor_totals = {}

    # Allocate interest using Largest Remainder Method for penny-exact distribution
    for segment in ownership_segments:
        segment_interest  = total_interest * (segment['days'] / total_days)
        segment_pik       = total_pik      * (segment['days'] / total_days)
        segment_cash_int  = total_cash_int * (segment['days'] / total_days)

        # Compute each investor's precise (unrounded) share for this segment
        precise_shares      = [segment_interest * (inv['ownership_pct'] / 100) for inv in segment['investors']]
        precise_pik         = [segment_pik      * (inv['ownership_pct'] / 100) for inv in segment['investors']]
        precise_cash_int    = [segment_cash_int * (inv['ownership_pct'] / 100) for inv in segment['investors']]

        # Apply penny rounding so segment shares sum to exactly segment totals
        rounded_shares   = penny_round(segment_interest, precise_shares)
        rounded_pik      = penny_round(segment_pik,      precise_pik)
        rounded_cash_int = penny_round(segment_cash_int, precise_cash_int)

        for investor, total_share, pik_share, cash_share in zip(
                segment['investors'], rounded_shares, rounded_pik, rounded_cash_int):
            inv_id = investor['investor_id']

            if inv_id not in investor_totals:
                investor_totals[inv_id] = {
                    'investor_id': inv_id,
                    'investor_name': investor['investor_name'],
                    'investor_short_name': investor['investor_short_name'],
                    'interest': 0.0,
                    'pik_interest': 0.0,
                    'cash_interest': 0.0,
                    'principal_beginning': 0.0,
                    'principal_ending': 0.0,
                    'principal_prepayment': 0.0,
                    'segments': []   # per-segment breakdown for reporting
                }

            investor_totals[inv_id]['interest']      += total_share
            investor_totals[inv_id]['pik_interest']  += pik_share
            investor_totals[inv_id]['cash_interest'] += cash_share

            # Store per-segment detail for statement rendering
            investor_totals[inv_id]['segments'].append({
                'start_date':    segment['start_date'],
                'end_date':      segment['end_date'],
                'days':          segment['days'],
                'ownership_pct': investor['ownership_pct'],
                'interest':      total_share,
                'pik_interest':  pik_share,
                'cash_interest': cash_share,
            })

    # Re-apply penny rounding across accumulated per-investor totals
    inv_ids_ordered = list(investor_totals.keys())
    final_interest  = penny_round(total_interest, [investor_totals[i]['interest']     for i in inv_ids_ordered])
    final_pik       = penny_round(total_pik,      [investor_totals[i]['pik_interest'] for i in inv_ids_ordered])
    final_cash_int  = penny_round(total_cash_int, [investor_totals[i]['cash_interest']for i in inv_ids_ordered])

    for inv_id, tot, pik, cash in zip(inv_ids_ordered, final_interest, final_pik, final_cash_int):
        investor_totals[inv_id]['interest']      = tot
        investor_totals[inv_id]['pik_interest']  = pik
        investor_totals[inv_id]['cash_interest'] = cash
        # Update the last segment's interest to reflect the final penny-rounded total
        # (segment-level values are already individually rounded; this keeps total consistent)

    # Allocate principal balances (penny-rounded using ending-period ownership)
    principal_beginning = period_data['principal_beginning']
    principal_ending = period_data['principal_ending']

    last_segment = ownership_segments[-1]
    last_investors = last_segment['investors']

    precise_beg = [principal_beginning * (inv['ownership_pct'] / 100) for inv in last_investors]
    precise_end = [principal_ending  * (inv['ownership_pct'] / 100) for inv in last_investors]

    rounded_beg = penny_round(principal_beginning, precise_beg)
    rounded_end = penny_round(principal_ending,    precise_end)

    for investor, beg, end in zip(last_investors, rounded_beg, rounded_end):
        inv_id = investor['investor_id']
        if inv_id in investor_totals:
            investor_totals[inv_id]['principal_beginning'] = beg
            investor_totals[inv_id]['principal_ending']    = end
            # Attach principal to the investor's last active segment for display
            if investor_totals[inv_id]['segments']:
                investor_totals[inv_id]['segments'][-1]['principal_beginning'] = beg
                investor_totals[inv_id]['segments'][-1]['principal_ending']    = end
    
    # Allocate principal prepayments at point-in-time ownership on the payment date.
    # Each prepayment is allocated using the ownership structure in effect on that
    # specific payment date — not time-weighted across the period.  This mirrors fee
    # allocation logic: an investor who exited before the payment date receives nothing,
    # and an investor who increased their stake on the payment date receives their full
    # new percentage.
    if period_data.get('prepayments'):
        from investors import _get_investors_at_date, load_investors
        all_investors = load_investors(loan_id)

        for prepayment in period_data['prepayments']:
            pp_amount = prepayment['amount']
            pp_date   = prepayment['payment_date']

            # Ownership as of the payment date
            owners_at_date = _get_investors_at_date(all_investors, pp_date)

            precise_prep = [
                pp_amount * (inv['ownership_pct'] / 100)
                for inv in owners_at_date
            ]
            rounded_prep = penny_round(pp_amount, precise_prep)

            for inv, prep_share in zip(owners_at_date, rounded_prep):
                inv_id = inv['investor_id']
                if inv_id in investor_totals:
                    investor_totals[inv_id]['principal_prepayment'] += prep_share

        # Final penny-round across accumulated prepayment totals
        total_prepayment = sum(p['amount'] for p in period_data['prepayments'])
        prep_ids = list(investor_totals.keys())
        raw_prep = [investor_totals[i]['principal_prepayment'] for i in prep_ids]
        final_prep = penny_round(total_prepayment, raw_prep)
        for inv_id, amt in zip(prep_ids, final_prep):
            investor_totals[inv_id]['principal_prepayment'] = amt
    
    return {
        'period_number': period_data['period_number'],
        'period_start': period_start,
        'period_end': period_end,
        'payment_due_date': period_data['payment_due_date'],
        'ownership_segments': ownership_segments,
        'investor_allocations': list(investor_totals.values())
    }


def generate_investor_report_data(
    loan_id: str,
    schedule: List[Dict],
    investors_filepath: str = "data/investors.csv"
) -> List[Dict]:
    """
    Generate investor allocation data for entire loan schedule.
    
    Args:
        loan_id: The loan identifier
        schedule: Complete loan schedule
        investors_filepath: Path to investors CSV
    
    Returns:
        List of period allocations (one per period)
    """
    allocations = []
    
    for period in schedule:
        allocation = allocate_period_to_investors(loan_id, period, investors_filepath)
        allocations.append(allocation)
    
    return allocations