from datetime import datetime
from typing import List, Dict
from investors import get_ownership_for_period


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
    
    # Allocate each type of activity
    investor_totals = {}
    
    # Allocate interest
    total_interest = period_data['interest_owed']
    for segment in ownership_segments:
        segment_interest = total_interest * (segment['days'] / total_days)
        
        for investor in segment['investors']:
            inv_id = investor['investor_id']
            investor_share = segment_interest * (investor['ownership_pct'] / 100)
            
            if inv_id not in investor_totals:
                investor_totals[inv_id] = {
                    'investor_id': inv_id,
                    'investor_name': investor['investor_name'],
                    'investor_short_name': investor['investor_short_name'],
                    'interest': 0.0,
                    'principal_beginning': 0.0,
                    'principal_ending': 0.0,
                    'principal_prepayment': 0.0
                }
            
            investor_totals[inv_id]['interest'] += investor_share
    
    # Allocate principal balances
    principal_beginning = period_data['principal_beginning']
    principal_ending = period_data['principal_ending']
    
    for segment in ownership_segments:
        for investor in segment['investors']:
            inv_id = investor['investor_id']
            ownership_pct = investor['ownership_pct'] / 100
            
            # Use ending ownership for principal balances
            # (simplification - could weight by days if needed)
            if segment == ownership_segments[-1]:  # Last segment
                investor_totals[inv_id]['principal_beginning'] = principal_beginning * ownership_pct
                investor_totals[inv_id]['principal_ending'] = principal_ending * ownership_pct
    
    # Allocate principal prepayments
    if period_data.get('prepayments'):
        total_prepayment = sum(p['amount'] for p in period_data['prepayments'])
        
        for segment in ownership_segments:
            segment_prepayment = total_prepayment * (segment['days'] / total_days)
            
            for investor in segment['investors']:
                inv_id = investor['investor_id']
                investor_share = segment_prepayment * (investor['ownership_pct'] / 100)
                investor_totals[inv_id]['principal_prepayment'] += investor_share
    
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