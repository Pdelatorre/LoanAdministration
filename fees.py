import csv
import os
from datetime import datetime
from typing import List, Dict


def load_fees(loan_id: str, filepath: str = "data/fees.csv") -> List[Dict]:
    """
    Load all fees for a specific loan.
    
    Returns:
        List of fee dicts with structure:
        {
            'fee_id': 'FEE-LOAN001-001',
            'loan_id': 'LOAN-001',
            'fee_date': datetime(2025, 2, 15),
            'fee_type': 'prepayment_fee',
            'amount': 10000.00,
            'cash_or_pik': 'cash',
            'period_number': 2,
            'description': 'Early payoff penalty'
        }
    """
    fees = []
    
    if not os.path.exists(filepath):
        return []
    
    try:
        with open(filepath, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['loan_id'] == loan_id:
                    fees.append({
                        'fee_id': row['fee_id'],
                        'loan_id': row['loan_id'],
                        'fee_date': datetime.strptime(row['fee_date'], '%Y-%m-%d'),
                        'fee_type': row['fee_type'],
                        'amount': float(row['amount']),
                        'cash_or_pik': row['cash_or_pik'],
                        'period_number': int(row['period_number']) if row['period_number'] else None,
                        'description': row['description']
                    })
    except FileNotFoundError:
        return []
    
    return fees


def add_fee(
    loan_id: str,
    fee_date: datetime,
    fee_type: str,
    amount: float,
    cash_or_pik: str = 'cash',
    period_number: int = None,
    description: str = "",
    filepath: str = "data/fees.csv"
) -> None:
    """
    Add a fee to the system.
    
    Args:
        loan_id: Loan identifier
        fee_date: Date fee was incurred
        fee_type: Type of fee (prepayment_fee, amendment_fee, exit_fee, etc.)
        amount: Fee amount
        cash_or_pik: 'cash' or 'pik' (whether fee capitalizes)
        period_number: Which period to include it in
        description: Description of the fee
    
    Fee Types:
        - prepayment_fee: Prepayment penalty
        - prepayment_interest: Interest on prepayment amount
        - amendment_fee: Amendment fee
        - exit_fee: Exit fee
        - waiver_fee: Covenant waiver fee
        - default_interest: Default interest (after negotiation)
        - other: Other fees
    """
    # Validate fee type
    valid_types = [
        'prepayment_fee',
        'prepayment_interest', 
        'amendment_fee',
        'exit_fee',
        'waiver_fee',
        'default_interest',
        'other'
    ]
    
    if fee_type not in valid_types:
        raise ValueError(f"Invalid fee_type. Must be one of: {', '.join(valid_types)}")
    
    # Validate cash_or_pik
    if cash_or_pik not in ['cash', 'pik']:
        raise ValueError("cash_or_pik must be 'cash' or 'pik'")
    
    # Generate fee ID
    existing_fees = load_fees(loan_id, filepath)
    if existing_fees:
        fee_numbers = [int(f['fee_id'].split('-')[-1]) for f in existing_fees]
        next_num = max(fee_numbers) + 1
    else:
        next_num = 1
    
    fee_id = f"FEE-{loan_id}-{next_num:03d}"
    
    # Prepare row
    new_row = {
        'fee_id': fee_id,
        'loan_id': loan_id,
        'fee_date': fee_date.strftime('%Y-%m-%d'),
        'fee_type': fee_type,
        'amount': f"{amount:.2f}",
        'cash_or_pik': cash_or_pik,
        'period_number': period_number if period_number else '',
        'description': description
    }
    
    # Write to CSV
    file_is_new = not os.path.exists(filepath) or os.path.getsize(filepath) == 0
    
    with open(filepath, 'a', newline='') as file:
        fieldnames = ['fee_id', 'loan_id', 'fee_date', 'fee_type', 'amount', 
                     'cash_or_pik', 'period_number', 'description']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        
        if file_is_new:
            writer.writeheader()
        
        writer.writerow(new_row)
    
    print(f"✅ Fee recorded: {fee_id} - {fee_type} - ${amount:,.2f} ({cash_or_pik})")


def get_fees_for_period(loan_id: str, period_number: int, filepath: str = "data/fees.csv") -> List[Dict]:
    """Get all fees for a specific period."""
    all_fees = load_fees(loan_id, filepath)
    return [f for f in all_fees if f['period_number'] == period_number]


def get_fee_display_name(fee_type: str) -> str:
    """Convert fee type to display name."""
    display_names = {
        'prepayment_fee': 'Prepayment Fee',
        'prepayment_interest': 'Prepayment Interest',
        'amendment_fee': 'Amendment Fee',
        'exit_fee': 'Exit Fee',
        'waiver_fee': 'Waiver Fee',
        'default_interest': 'Default Interest',
        'other': 'Other Fee'
    }
    return display_names.get(fee_type, fee_type)