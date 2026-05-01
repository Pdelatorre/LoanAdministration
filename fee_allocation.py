from datetime import datetime
from typing import Dict, List
from fees import load_fees, get_fee_display_name
from investors import _get_investors_at_date
from interest_calculations import penny_round


def allocate_fee_to_investors(
    loan_id: str,
    fee_date: datetime,
    fee_amount: float,
    fee_type: str
) -> Dict:
    """
    Allocate a fee to investors based on ownership ON the fee date.
    
    Point-in-time allocation - no pro-rating for ownership changes.
    Uses ownership percentages as of the fee date.
    
    Args:
        loan_id: Loan identifier
        fee_date: Date fee was incurred
        fee_amount: Total fee amount
        fee_type: Type of fee
    
    Returns:
        Dict with allocation details:
        {
            'fee_date': datetime,
            'fee_type': 'prepayment_fee',
            'fee_amount': 10000.00,
            'investor_allocations': [
                {
                    'investor_id': 'INV-A',
                    'investor_name': 'Investor A LLC',
                    'ownership_pct': 40.0,
                    'fee_share': 4000.00
                },
                ...
            ]
        }
    """
    # Get investors as of fee date
    from investors import load_investors
    all_investors = load_investors(loan_id)
    investors = _get_investors_at_date(all_investors, fee_date)
    
    if not investors:
        raise ValueError(f"No investors found for {loan_id} as of {fee_date.strftime('%Y-%m-%d')}")
    
    # Validate ownership sums to 100%
    total_ownership = sum(inv['ownership_pct'] for inv in investors)
    if abs(total_ownership - 100.0) > 0.01:
        raise ValueError(f"Ownership percentages sum to {total_ownership}%, not 100%")
    
    # Compute precise (unrounded) shares then apply Largest Remainder Method
    # so every investor's share is to the penny and they sum to fee_amount exactly.
    precise_shares = [fee_amount * (inv['ownership_pct'] / 100.0) for inv in investors]
    rounded_shares = penny_round(fee_amount, precise_shares)

    allocations = []
    for inv, fee_share in zip(investors, rounded_shares):
        allocations.append({
            'investor_id': inv['investor_id'],
            'investor_name': inv['investor_name'],
            'ownership_pct': inv['ownership_pct'],
            'fee_share': fee_share
        })

    # Sanity check — should always pass after penny_round; kept as a hard guard
    total_allocated = sum(a['fee_share'] for a in allocations)
    if abs(total_allocated - fee_amount) > 0.01:
        raise ValueError(f"Allocation error: ${total_allocated:.2f} allocated vs ${fee_amount:.2f} fee")
    
    return {
        'fee_date': fee_date,
        'fee_type': fee_type,
        'fee_amount': fee_amount,
        'investor_allocations': allocations
    }


def get_period_fees_with_allocations(loan_id: str, period_number: int) -> List[Dict]:
    """
    Get all fees for a period with investor allocations.
    
    Args:
        loan_id: Loan identifier
        period_number: Period number
    
    Returns:
        List of fees with allocations:
        [
            {
                'fee_id': 'FEE-LOAN001-001',
                'fee_date': datetime,
                'fee_type': 'prepayment_fee',
                'amount': 10000.00,
                'cash_or_pik': 'cash',
                'description': 'Early payoff penalty',
                'allocations': {
                    'investor_allocations': [...]
                }
            },
            ...
        ]
    """
    from fees import get_fees_for_period
    
    fees = get_fees_for_period(loan_id, period_number)
    
    fees_with_allocations = []
    for fee in fees:
        # Allocate fee to investors
        allocation = allocate_fee_to_investors(
            loan_id=loan_id,
            fee_date=fee['fee_date'],
            fee_amount=fee['amount'],
            fee_type=fee['fee_type']
        )
        
        fees_with_allocations.append({
            **fee,
            'allocations': allocation
        })
    
    return fees_with_allocations


def calculate_investor_fee_totals(loan_id: str, period_number: int, investor_id: str) -> Dict:
    """
    Calculate total fees for a specific investor in a period.
    
    Args:
        loan_id: Loan identifier
        period_number: Period number
        investor_id: Investor identifier
    
    Returns:
        Dict with fee totals by type:
        {
            'prepayment_fee': 4000.00,
            'amendment_fee': 2000.00,
            'total_fees': 6000.00,
            'fee_details': [
                {
                    'fee_date': datetime,
                    'fee_type': 'prepayment_fee',
                    'display_name': 'Prepayment Fee',
                    'total_amount': 10000.00,
                    'investor_share': 4000.00,
                    'ownership_pct': 40.0,
                    'description': 'Early payoff penalty'
                },
                ...
            ]
        }
    """
    fees_with_allocations = get_period_fees_with_allocations(loan_id, period_number)
    
    # Aggregate by fee type
    fee_totals = {}
    fee_details = []
    total_fees = 0.0
    
    for fee in fees_with_allocations:
        # Find this investor's allocation
        investor_allocation = next(
            (alloc for alloc in fee['allocations']['investor_allocations'] 
             if alloc['investor_id'] == investor_id),
            None
        )
        
        if investor_allocation:
            fee_type = fee['fee_type']
            investor_share = investor_allocation['fee_share']
            
            # Add to type total
            if fee_type not in fee_totals:
                fee_totals[fee_type] = 0.0
            fee_totals[fee_type] += investor_share
            
            # Add to overall total
            total_fees += investor_share
            
            # Add to details
            fee_details.append({
                'fee_date': fee['fee_date'],
                'fee_type': fee_type,
                'display_name': get_fee_display_name(fee_type),
                'total_amount': fee['amount'],
                'investor_share': investor_share,
                'ownership_pct': investor_allocation['ownership_pct'],
                'description': fee['description'],
                'cash_or_pik': fee['cash_or_pik']
            })
    
    return {
        **fee_totals,
        'total_fees': total_fees,
        'fee_details': fee_details
    }