# test_pdf_simple.py
from datetime import datetime
from loan import Loan
from investors import add_investor
from fees import add_fee
from investor_allocation import allocate_period_to_investors
from investor_reports_pdf import generate_investor_statement_pdf
from sofr_rates import load_sofr_rates
import os

# Clean up
if os.path.exists('data/investors.csv'):
    os.remove('data/investors.csv')
if os.path.exists('data/fees.csv'):
    os.remove('data/fees.csv')

print("Creating test loan...")

loan = Loan(
    loan_id="PDF-TEST",
    borrower="Test Company",
    loan_name="Test",
    principal=1000000,
    margin=0.025,
    origination_date=datetime(2025, 1, 15),
    maturity_date=datetime(2025, 3, 31)
)

add_investor("PDF-TEST", "INV-A", "Investor A", "Inv-A", 100.0, datetime(2025, 1, 1))

add_fee("PDF-TEST", datetime(2025, 2, 15), "prepayment_fee", 5000.00, period_number=2)

sofr_rates = load_sofr_rates()
schedule = loan.calculate_schedule(sofr_rates=sofr_rates)

allocation = allocate_period_to_investors("PDF-TEST", schedule[1])

print("Generating PDF...")

try:
    pdf_path = generate_investor_statement_pdf(
        loan_id="PDF-TEST",
        loan_name="Test",
        period_data=schedule[1],
        allocation_data=allocation,
        investor_id="INV-A",
        output_path="output/investor_reports_pdf/TEST.pdf"
    )
    print(f"✅ PDF created: {pdf_path}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()