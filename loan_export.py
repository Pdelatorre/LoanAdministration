import csv
from datetime import datetime
from typing import List, Dict


def export_schedule_to_csv(schedule: List[Dict], filepath: str, loan_info: Dict = None) -> None:
    """
    Export interest schedule to CSV file.
    
    Args:
        schedule: List of period dicts with interest calculations
        filepath: Where to save the CSV
        loan_info: Optional dict with loan details (loan_id, borrower, principal, etc.)
    """
    with open(filepath, 'w', newline='') as file:
        # Define columns for export
        fieldnames = [
            'period_number',
            'start_date',
            'end_date', 
            'payment_due_date',
            'days',
            'sofr_reset_date',
            'sofr_rate',
            'effective_rate',
            'interest_amount'
        ]
        
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        
        # Write header row with loan info if provided
        if loan_info:
            # Write loan info as comments
            file.write(f"# Loan ID: {loan_info.get('loan_id', 'N/A')}\n")
            file.write(f"# Borrower: {loan_info.get('borrower', 'N/A')}\n")
            file.write(f"# Principal: ${loan_info.get('principal', 0):,.2f}\n")
            file.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            file.write("#\n")
        
        # Write column headers
        writer.writeheader()
        
        # Write data rows
        for entry in schedule:
            # Format the row for export
            row = {
                'period_number': entry['period_number'],
                'start_date': entry['start_date'].strftime('%Y-%m-%d'),
                'end_date': entry['end_date'].strftime('%Y-%m-%d'),
                'payment_due_date': entry['payment_due_date'].strftime('%Y-%m-%d'),
                'days': entry['days'],
                'sofr_reset_date': entry['sofr_reset_date'].strftime('%Y-%m-%d'),
                'sofr_rate': f"{entry['sofr_rate']:.5f}",
                'effective_rate': f"{entry['effective_rate']:.5f}",
                'interest_amount': f"{entry['interest_amount']:.2f}"
            }
            writer.writerow(row)
    
    print(f"Schedule exported to {filepath}")


def export_schedule_to_text(schedule: List[Dict], filepath: str, loan_info: Dict = None) -> None:
    """
    Export interest schedule to formatted text file.
    
    Args:
        schedule: List of period dicts with interest calculations
        filepath: Where to save the file
        loan_info: Optional dict with loan details
    """
    with open(filepath, 'w') as file:
        # Write loan info header if provided
        if loan_info:
            file.write(f"Loan ID: {loan_info.get('loan_id', 'N/A')}\n")
            file.write(f"Borrower: {loan_info.get('borrower', 'N/A')}\n")
            file.write(f"Principal: ${loan_info.get('principal', 0):,.2f}\n")
            file.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            file.write("\n")
        
        # Write schedule header
        header = (
            f"{'Period':<6} {'Start Date':<12} {'End Date':<12} {'Payment Date':<14} "
            f"{'Days':<5} {'SOFR Effective Date':<12} {'SOFR Rate':<10} {'Effective Rate':<15} {'Interest Amount':<15}\n"
        )
        file.write(header)
        file.write("=" * len(header) + "\n")
        
        # Write each period's data
        for entry in schedule:
            line = (
                f"{entry['period_number']:<6} "
                f"{entry['start_date'].strftime('%Y-%m-%d'):<12} "
                f"{entry['end_date'].strftime('%Y-%m-%d'):<12} "
                f"{entry['payment_due_date'].strftime('%Y-%m-%d'):<14} "
                f"{entry['days']:<5} "
                f"{entry['sofr_reset_date'].strftime('%Y-%m-%d'):<12} "
                f"{entry['sofr_rate']*100:<10.5f} "
                f"{entry['effective_rate']*100:<15.5f} "
                f"${entry['interest_amount']:<15,.2f}\n"
            )
            file.write(line)
    
    print(f"Schedule exported to {filepath}")