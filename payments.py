import csv
import os
from datetime import datetime
from typing import List, Dict

def load_payments(loan_id: str, filepath: str = "data/payments.csv") -> List[Dict]:
    """
    Load all payments for a specific loan.
    
    Args:
        loan_id: The loan to load payments for
        filepath: Path to payments CSV
    
    Returns:
        List of payment dicts
        Example: [
            {
                'payment_id': 'PAY-001',
                'loan_id': 'LOAN-001',
                'payment_date': datetime(2025, 1, 15),
                'amount': 20000.00,
                'payment_type': 'interest',
                'period_number': 1,
                'notes': 'Includes prepayment'
            },
            ...
        ]
    """
    payments = []

    try:
        with open(filepath, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['loan_id'] == loan_id:
                    if row['period_number']:
                        period_number = int(row['period_number'])
                    else:
                        period_number = None
                    payment_date = datetime.strptime(row['payment_date'], '%Y-%m-%d')
                    amount = float(row['amount'])
                    payment_type = row['payment_type']
                    notes = row['notes']
                    payments.append({
                        'payment_id': row['payment_id'],
                        'loan_id': loan_id,
                        'payment_date': payment_date,
                        'amount': amount,
                        'payment_type': payment_type,
                        'period_number': period_number,
                        'notes': notes
                    })
    except FileNotFoundError:
        return [] # Return empty dict if file doesn't exist yet
    
    return payments


def add_payment(
    loan_id: str,
    payment_date: datetime,
    amount: float,
    payment_type: str,  # 'interest' or 'principal_prepayment'
    period_number: int = None,
    notes: str = "",
    filepath: str = "data/payments.csv"
) -> None:
    """
    Record a new payment.
    
    Args:
        loan_id: The loan ID
        payment_date: Date payment was received
        amount: Payment amount
        payment_type: 'interest' or 'principal_prepayment'
        period_number: Period number (for interest payments)
        notes: Optional notes
        filepath: Path to CSV file
    """
    # Load existing payments to check for duplicates and generate ID
    existing_payments = load_payments(loan_id, filepath)
    
    if existing_payments:
        payment_numbers = [int(p['payment_id'].split('-')[-1]) for p in existing_payments]
        next_num = max(payment_numbers) + 1
    else:
        next_num = 1

    payment_id = f"PAY-{loan_id}-{next_num:03d}"
    
    # Prepare the row
    new_row = {
        'payment_id': payment_id,  
        'loan_id': loan_id,
        'payment_date': payment_date.strftime('%Y-%m-%d'),
        'amount': f"{amount:.2f}",
        'payment_type': payment_type,
        'period_number': period_number if period_number else '',
        'notes': notes
    }
    
    file_is_new = not os.path.exists(filepath) or os.path.getsize(filepath) == 0

    with open(filepath, 'a', newline='') as file:
        fieldnames = ['payment_id', 'loan_id', 'payment_date', 'amount', 'payment_type', 'period_number', 'notes']
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        # If file is new/empty, write the header
        if file_is_new :
            writer.writeheader()

        # Write the new row
        writer.writerow(new_row)
    print(f"✅ Payment recorded: {loan_id} - ${amount:,.2f} on {payment_date.strftime('%Y-%m-%d')}")


