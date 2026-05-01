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
    # Read existing rates
    existing_rates = load_sofr_rates(filepath)
    is_update = reset_date in existing_rates

    if is_update:
        print(f"Warning: Rate for {reset_date.strftime('%Y-%m-%d')} already exists. Updating...")

    # Prepare the new row
    date_added = datetime.now().strftime('%Y-%m-%d')
    new_row = {
        'reset_date': reset_date.strftime('%Y-%m-%d'),
        'term_sofr_1m': f"{rate:.7f}",
        'source': source,
        'date_added': date_added
    }

    fieldnames = ['reset_date', 'term_sofr_1m', 'source', 'date_added']

    if is_update:
        # Rewrite the entire file, replacing the existing row for this date.
        # This keeps the CSV clean — no duplicate entries accumulate.
        rows = []
        try:
            with open(filepath, 'r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row_date = datetime.strptime(row['reset_date'], "%Y-%m-%d")
                    if row_date == reset_date:
                        rows.append(new_row)   # replace old row
                    else:
                        rows.append(dict(row))  # keep all other rows
        except FileNotFoundError:
            rows = [new_row]

        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    else:
        # Append new row — no duplicate exists
        file_is_new = not os.path.exists(filepath) or os.path.getsize(filepath) == 0
        with open(filepath, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if file_is_new:
                writer.writeheader()
            writer.writerow(new_row)

    print(f"Added rate for {reset_date.strftime('%Y-%m-%d')}: {rate * 100:.5f}%")
