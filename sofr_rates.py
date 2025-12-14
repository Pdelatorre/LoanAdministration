import csv
import os
from datetime import datetime
from typing import Dict, Optional


def load_sofr_rates(filepath: str = "data/sofr_rates.csv") -> Dict[datetime, float]:
    """Load SOFR rates from a CSV file into a dictionary."""
    rates = {}
    
    try:
        with open(filepath, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Parse the reset_date string to datetime
                reset_date = datetime.strptime(row['reset_date'], "%Y-%m-%d")
                
                # Parse the rate as a float
                term_sofr_1m = float(row['term_sofr_1m'])
                
                # Add to dictionary
                rates[reset_date] = term_sofr_1m
                
    except FileNotFoundError:
        # Return empty dict if file doesn't exist yet
        return {}
    
    return rates


def add_sofr_rate(
    reset_date: datetime,
    rate: float,
    filepath: str = "data/sofr_rates.csv",
    source: str = "CME"
) -> None:
    """
    Add a new SOFR rate to the CSV file.
    
    Args:
        reset_date: The SOFR reset date
        rate: The 1-month Term SOFR rate (as decimal)
        filepath: Path to the CSV file
        source: Source of the rate (default "CME")
    """
    # Read existing rates to check for duplicates
    existing_rates = load_sofr_rates(filepath)
    
    if reset_date in existing_rates:
        print(f"Warning: Rate for {reset_date.strftime('%Y-%m-%d')} already exists. Updating...")
    
    # Prepare the new row
    date_added = datetime.now().strftime('%Y-%m-%d')
    new_row = {
        'reset_date': reset_date.strftime('%Y-%m-%d'),
        'term_sofr_1m': f"{rate:.5f}",  # 5 decimal places
        'source': source,
        'date_added': date_added
    }
    
    # Check if file exists and has content
    file_is_new = not os.path.exists(filepath) or os.path.getsize(filepath) == 0

    with open(filepath, 'a', newline='') as file:
        fieldnames = ['reset_date', 'term_sofr_1m', 'source', 'date_added']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        
        # If file is new/empty, write the header
        if file_is_new:
            writer.writeheader()
        
        # Write the new row
        writer.writerow(new_row)
    print(f"Added rate for {reset_date.strftime('%Y-%m-%d')}: {rate:.5f}")
