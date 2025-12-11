# test_loan_with_csv.py
from datetime import datetime
from loan import Loan
from sofr_rates import add_sofr_rate, load_sofr_rates

# First, make sure we have all the rates we need
# Add the 4th rate (we already have 3 from earlier tests)
add_sofr_rate(datetime(2025, 3, 28), 0.04650)

# Create loan
loan = Loan(
    loan_id="LOAN-001",
    borrower="ABC Company",
    principal=1000000,
    margin=0.0250,
    origination_date=datetime(2025, 1, 15),
    maturity_date=datetime(2025, 4, 30),
    sofr_floor=0.0000,
    sofr_ceiling=0.0800
)

print(f"Loan: {loan.loan_id}")
print(f"Principal: ${loan.principal:,.2f}\n")

# Check what dates we need
print("Required SOFR reset dates:")
for date in loan.get_required_sofr_dates():
    print(f"  {date.strftime('%Y-%m-%d')}")

# Show what rates we have
print("\nAvailable SOFR rates:")
rates = load_sofr_rates()
for date, rate in sorted(rates.items()):
    print(f"  {date.strftime('%Y-%m-%d')}: {rate:.5f}")

# Calculate schedule from file
print("\n" + "="*80)
print("Interest Schedule (loaded from CSV):")
print("="*80)

schedule = loan.calculate_interest_schedule_from_file()

total_interest = 0
for entry in schedule:
    print(f"\nPeriod {entry['period_number']}: "
          f"{entry['start_date'].strftime('%Y-%m-%d')} to "
          f"{entry['end_date'].strftime('%Y-%m-%d')} ({entry['days']} days)")
    print(f"  SOFR Reset: {entry['sofr_reset_date'].strftime('%Y-%m-%d')}")
    print(f"  SOFR Rate: {entry['sofr_rate']*100:.2f}%")
    print(f"  Effective Rate: {entry['effective_rate']*100:.2f}%")
    print(f"  Interest Amount: ${entry['interest_amount']:,.2f}")
    total_interest += entry['interest_amount']

print(f"\n{'='*80}")
print(f"Total Interest: ${total_interest:,.2f}")

# Add to your test file
from loan_export import export_schedule_to_csv, export_schedule_to_text

# ... after calculating schedule ...

loan_info = {
    'loan_id': loan.loan_id,
    'borrower': loan.borrower,
    'principal': loan.principal,
    'margin': loan.margin * 100,  # Convert to percentage for display
    'origination_date': loan.origination_date.strftime('%Y-%m-%d'),
    'maturity_date': loan.maturity_date.strftime('%Y-%m-%d')
}

print(f"\nLoan info being passed to export:")
print(f"Principal type: {type(loan_info['principal'])}")
print(f"Principal value: {loan_info['principal']}")

# Export to CSV
export_schedule_to_csv(schedule, 'output/loan_schedule.csv', loan_info)

# Export to text
export_schedule_to_text(schedule, 'output/loan_schedule.txt', loan_info)

print("\nExports complete! Check the output/ directory")