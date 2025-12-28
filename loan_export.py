import csv
from datetime import datetime
from typing import List, Dict


def export_schedule_to_csv(schedule: List[Dict], filepath: str, loan_info: Dict = None) -> None:
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
            'principal_beginning',
            'interest_owed',
            'prepaid_balance_start',
            'prepaid_applied',
            'prepaid_balance_end',
            'pik_elected',
            'pik_amount',
            'cash_due',
            'principal_ending',
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
                'pik_elected': entry['pik_elected'],
                'principal_beginning': f"{entry['principal_beginning']:.2f}",
                'interest_owed': f"{entry['interest_owed']:.2f}",
                'prepaid_balance_start': f"{entry['prepaid_balance_start']:.2f}",
                'prepaid_applied': f"{entry['prepaid_applied']:.2f}",
                'prepaid_balance_end': f"{entry['prepaid_balance_end']:.2f}",
                'pik_amount': f"{entry['pik_amount']:.2f}",
                'cash_due': f"{entry['cash_due']:.2f}",
                'principal_ending': f"{entry['principal_ending']:.2f}"
            }
            writer.writerow(row)
    
    print(f"Schedule exported to {filepath}")

def export_segment_details_to_csv(schedule: List[Dict], filepath: str, loan_info: Dict = None) -> None:
    """
    Export segment-level details for periods with principal prepayments.
    
    Only creates file if there are segments to export.
    
    Args:
        schedule: Complete loan schedule
        filepath: Path for segment details CSV
        loan_info: Optional loan information for header
    """
    import csv
    from datetime import datetime
    
    # Collect all segments from all periods
    all_segments = []
    
    for entry in schedule:
        if entry['segments']:  # Only periods with prepayments
            period_num = entry['period_number']
            
            for segment in entry['segments']:
                all_segments.append({
                    'period_number': period_num,
                    'segment_number': segment['segment_num'],
                    'start_date': segment['start_date'].strftime('%Y-%m-%d'),
                    'end_date': segment['end_date'].strftime('%Y-%m-%d'),
                    'days': segment['days'],
                    'principal': f"{segment['principal']:.2f}",
                    'interest': f"{segment['interest']:.2f}"
                })
    
    # Only create file if there are segments
    if not all_segments:
        return
    
    # Write to CSV with header comments
    with open(filepath, 'w', newline='') as file:
        # Write header comments (Option 5)
        if loan_info:
            file.write(f"# Loan ID: {loan_info.get('loan_id', 'N/A')}\n")
            file.write(f"# Borrower: {loan_info.get('borrower', 'N/A')}\n")
            # Extract loan ID to create related schedule filename
            loan_id = loan_info.get('loan_id', 'UNKNOWN')
            file.write(f"# Related Schedule: {loan_id}_schedule.csv\n")
            file.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            file.write("#\n")
            file.write("# This file contains detailed segment breakdowns for periods with principal prepayments.\n")
            file.write("# Each segment shows interest calculated on different principal balances within a period.\n")
            file.write("#\n")
        
        # Write data
        fieldnames = ['period_number', 'segment_number', 'start_date', 'end_date', 
                     'days', 'principal', 'interest']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_segments)
    
    print(f"Segment details exported to {filepath}")


def export_schedule_to_text(schedule: List[Dict], filepath: str, loan_info: Dict = None) -> None:
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
            f"{'Days':<5} {'SOFR Effective Date':<20} {'SOFR Rate':<10} {'Effective Rate':<15} {'PIK Elected' :<15} {'Principal Beginning' :<20} {'Interest Amount':<15} {'Prepaid Balance Start':<20} {'Prepaid Applied':<20} {'Prepaid Balance End':<20} {'PIK Amount' :<15} {'Cash Due' :<15} {'Principal Ending' :<20}\n"
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
                f"{entry['sofr_reset_date'].strftime('%Y-%m-%d'):<20} "
                f"{entry['sofr_rate']*100:<10.5f} "
                f"{entry['effective_rate']*100:<15.5f} "
                f"{'Yes' if entry['pik_elected'] else 'No':<15} "
                f"${entry['principal_beginning']:<20,.2f} "
                f"${entry['interest_owed']:<15,.2f} "
                f"${entry['prepaid_balance_start']:<20,.2f} "
                f"${entry['prepaid_applied']:<20,.2f} "
                f"${entry['prepaid_balance_end']:<20,.2f} "
                f"${entry['pik_amount']:<15,.2f} "
                f"${entry['cash_due']:<15,.2f} "
                f"${entry['principal_ending']:<20,.2f}\n"
            )
            file.write(line)

            # Add segment details if present
            if entry['segments'] and len(entry['segments']) > 1:
                file.write("\n")
                file.write(" ** PRINCIPAL PREPAYMENTS IN THIS PERIOD **\n")
                for prepayment in entry['prepayments']:
                    file.write(f"    - {prepayment['payment_date'].strftime('%Y-%m-%d')}: -${prepayment['amount']:,.2f}\n")
                file.write("\n")
                file.write(" ** INTEREST CALCULATION DETAIL **\n")
                for segment in entry['segments']:
                    seg_desc = (
                        f"    Segment {segment['segment_num']}: "
                        f"{segment['start_date'].strftime('%Y-%m-%d')} to {segment['end_date'].strftime('%Y-%m-%d')} "
                        f"{segment['days']} days @ ${segment['principal']:,.2f}: "
                        f"{segment['interest']:,.2f}\n"
                    )
                    file.write(seg_desc)

                file.write(f"    {'':<60} {'-' * 12}\n")
                file.write(f"    Total Interest:{'':<47} ${entry['interest_owed']:,.2f}\n")
                file.write("\n")

    print(f"Schedule exported to {filepath}")
