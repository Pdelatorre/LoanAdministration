from datetime import datetime
from loan import Loan
from investors import add_investor
from fees import add_fee
from investor_allocation import allocate_period_to_investors
from investor_reports import generate_investor_statement
from investor_reports_pdf import generate_all_investor_pdfs
from sofr_rates import load_sofr_rates
import os

# Clean up
for filepath in ['data/investors.csv', 'data/fees.csv', 'data/payments.csv']:
    if os.path.exists(filepath):
        os.remove(filepath)

print("=" * 80)
print("TESTING FEES ON INVESTOR REPORTS")
print("=" * 80)

# Create loan
loan = Loan(
    loan_id="FEE-TEST",
    borrower="Test Company LLC",
    loan_name="Test Co",
    principal=5000000,
    margin=0.025,
    origination_date=datetime(2025, 1, 15),
    maturity_date=datetime(2025, 4, 30)
)

# Add investors
print("\n1. Adding investors...")
add_investor("FEE-TEST", "INV-A", "Investor A LLC", 40.0, datetime(2025, 1, 1))
add_investor("FEE-TEST", "INV-B", "Investor B Fund", 60.0, datetime(2025, 1, 1))

# Add fees to Period 2
print("\n2. Adding fees...")
add_fee(
    loan_id="FEE-TEST",
    fee_date=datetime(2025, 2, 15),
    fee_type="prepayment_fee",
    amount=25000.00,
    period_number=2,
    description="Early payoff penalty - 0.5% of prepayment"
)

add_fee(
    loan_id="FEE-TEST",
    fee_date=datetime(2025, 2, 20),
    fee_type="amendment_fee",
    amount=10000.00,
    period_number=2,
    description="Rate modification amendment"
)

# Generate schedule
print("\n3. Generating loan schedule...")
sofr_rates = load_sofr_rates()
schedule = loan.calculate_schedule(sofr_rates=sofr_rates)

# Get Period 2
period_2 = schedule[1]

# Allocate to investors
print("\n4. Allocating period to investors...")
allocation = allocate_period_to_investors("FEE-TEST", period_2)

# Generate text report for Investor A
print("\n5. Generating text report...")
text_report = generate_investor_statement(
    loan_id="FEE-TEST",
    loan_name="Test Co",
    period_data=period_2,
    allocation_data=allocation,
    investor_id="INV-A"
)

print("\n" + "=" * 80)
print("TEXT REPORT PREVIEW (Investor A - 40% ownership):")
print("=" * 80)
print(text_report)

# Generate PDFs
print("\n6. Generating PDF reports...")
pdf_files = generate_all_investor_pdfs(
    loan=loan,
    period_data=period_2,
    allocation_data=allocation
)

print(f"\n✅ Generated {len(pdf_files)} PDF reports")
for pdf in pdf_files:
    print(f"   - {pdf}")

print("\n" + "=" * 80)
print("✅ FEES ON REPORTS TEST COMPLETE")
print("=" * 80)
print("\nExpected Investor A fees:")
print("  Prepayment Fee: $10,000 (40% of $25,000)")
print("  Amendment Fee:  $ 4,000 (40% of $10,000)")
print("  Total Fees:     $14,000")