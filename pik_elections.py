import csv
import os
from typing import Dict
from datetime import datetime

def load_pik_elections(loan_id: str, filepath: str = "data/pik_elections.csv") -> Dict[int, bool]:
    """
    Load PIK elections for a specific loan.
    
    Args:
        loan_id: The loan to load elections for
        filepath: Path to PIK elections CSV
    
    Returns:
        Dictionary mapping period_number to pik_elected boolean
        Example: {1: True, 2: False, 3: True}
    """
    pik_elections = {}

    try:
        with open(filepath, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['loan_id'] == loan_id:
                    period_number = int(row['period_number'])
                    pik_elected = row['pik_elected'].lower() == 'true'
                    pik_elections[period_number] = pik_elected
    except FileNotFoundError:
        return {} # Return empty dict if file doesn't exist yet
    
    return pik_elections


def add_pik_election(loan_id: str, period_number: int, pik_elected: bool, 
                     filepath: str = "data/pik_elections.csv") -> None:
    """
    Add or update a PIK election for a loan period.
    
    Args:
        loan_id: The loan ID
        period_number: Which period
        pik_elected: True for PIK, False for cash
        filepath: Path to CSV file
    """
    fieldnames = ['loan_id', 'period_number', 'pik_elected', 'date_added']
    date_added = datetime.now().strftime('%Y-%m-%d')
    new_row = {
        'loan_id': loan_id,
        'period_number': period_number,
        'pik_elected': str(pik_elected),
        'date_added': date_added
    }

    # Load all existing rows across all loans
    all_rows = []
    updated = False
    try:
        with open(filepath, 'r', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['loan_id'] == loan_id and int(row['period_number']) == period_number:
                    # Replace in place — update date_added too
                    all_rows.append(new_row)
                    updated = True
                else:
                    all_rows.append(row)
    except FileNotFoundError:
        pass

    if not updated:
        all_rows.append(new_row)

    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
    with open(filepath, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    status = "PIK" if pik_elected else "Cash"
    action = "Updated" if updated else "Added"
    print(f"{action}: Loan {loan_id} Period {period_number} → {status}")
