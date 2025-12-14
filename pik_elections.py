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
    existing_PIK_elections = load_pik_elections(loan_id, filepath)

    if period_number in existing_PIK_elections:
        print(f"Warning: PIK election for loan {loan_id} period {period_number} already exists. Updating...")

    
    date_added = datetime.now().strftime('%Y-%m-%d')
    new_row = {
        'loan_id': loan_id,
        'period_number': period_number,
        'pik_elected': str(pik_elected),
        'date_added': date_added
    }   

    file_is_new = not os.path.exists(filepath) or os.path.getsize(filepath) == 0

    with open(filepath, 'a', newline='') as file:
        fieldnames = ['loan_id', 'period_number', 'pik_elected', 'date_added']
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        # If file is new/empty, write the header
        if file_is_new :
            writer.writeheader()

        # Write the new row
        writer.writerow(new_row)
    print(f"PIK election for loan {loan_id} period {period_number} added/updated.")
