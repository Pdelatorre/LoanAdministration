import config
from investor_reports import generate_all_investor_statements_for_loan
from investor_reports_pdf import generate_all_investor_pdfs
from datetime import datetime
from loan import Loan
from investors import add_investor
from investor_allocation import allocate_period_to_investors
from payments import add_payment
from sofr_rates import load_sofr_rates
import os

# Clean up
for filepath in ['data/investors.csv', 'data/payments.csv']:
    if os.path.exists(filepath):
        os.remove(filepath)

print("=" * 80)
print("TESTING CONFIG INTEGRATION")
print("=" * 80)

print(f"\n📋 Company Name: {config.COMPANY_NAME}")
print(f"📁 Text Reports Dir: {config.INVESTOR_REPORTS_DIR}")
print(f"📁 PDF Reports Dir: {config.INVESTOR_REPORTS_PDF_DIR}")

# Create loan
loan = Loan(
    loan_id="TEST-CONFIG",
    borrower="Test Company LLC",
    loan_name="Test",
    principal=1000000,
    margin=0.025,
    origination_date=datetime(2025, 1, 15),
    maturity_date=datetime(2025, 3, 31)
)

# Add investors
add_investor("TEST-CONFIG", "INV-A", "Investor A", "Inv-A", 50.0, datetime(2025, 1, 1))
add_investor("TEST-CONFIG", "INV-B", "Investor B", "Inv-B", 50.0, datetime(2025, 1, 1))

# Generate schedule
sofr_rates = load_sofr_rates()
schedule = loan.calculate_schedule(sofr_rates=sofr_rates, include_payment_status=False)

# Allocate
allocation = allocate_period_to_investors("TEST-CONFIG", schedule[1])

print("\n" + "=" * 80)
print("GENERATING TEXT REPORTS (using config defaults)")
print("=" * 80)

# Generate text reports - NO company_name parameter, should use config
text_files = generate_all_investor_statements_for_loan(
    loan=loan,
    period_data=schedule[1],
    allocation_data=allocation
    # Not passing company_name or output_dir - should use config defaults
)

print(f"\n✅ Generated {len(text_files)} text reports")
for f in text_files:
    print(f"   {f}")

print("\n" + "=" * 80)
print("GENERATING PDF REPORTS (using config defaults)")
print("=" * 80)

# Generate PDFs - NO company_name parameter, should use config
pdf_files = generate_all_investor_pdfs(
    loan=loan,
    period_data=schedule[1],
    allocation_data=allocation
    # Not passing company_name or output_dir - should use config defaults
)

print(f"\n✅ Generated {len(pdf_files)} PDF reports")
for f in pdf_files:
    print(f"   {f}")

print("\n" + "=" * 80)
print("VERIFYING COMPANY NAME IN REPORTS")
print("=" * 80)

# Check text report
with open(text_files[0], 'r') as f:
    content = f.read()
    if config.COMPANY_NAME in content:
        print(f"✅ Text report contains config company name: {config.COMPANY_NAME}")
    else:
        print(f"❌ Text report missing config company name")

print("\n📁 Check these locations:")
print(f"   Text: {config.INVESTOR_REPORTS_DIR}")
print(f"   PDF:  {config.INVESTOR_REPORTS_PDF_DIR}")