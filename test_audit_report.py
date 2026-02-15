from datetime import datetime
from loan import Loan
from investors import add_investor
from payments import add_payment
from audit_reports import generate_audit_report
from sofr_rates import load_sofr_rates
from fees import add_fee
import os

# Clean up
for filepath in ['data/investors.csv', 'data/payments.csv']:
    if os.path.exists(filepath):
        os.remove(filepath)

print("=" * 80)
print("TESTING AUDIT REPORT GENERATION")
print("=" * 80)

# Create loan
loan = Loan(
    loan_id="AUDIT-TEST",
    borrower="Test Company LLC",
    loan_name="Test Co",
    principal=5000000,
    margin=0.025,
    origination_date=datetime(2025, 1, 15),
    maturity_date=datetime(2025, 4, 30)
)

# Add investors
add_investor("AUDIT-TEST", "INV-A", "Investor A LLC", 40.0, datetime(2025, 1, 1))
add_investor("AUDIT-TEST", "INV-B", "Investor B Fund", 35.0, datetime(2025, 1, 1))
add_investor("AUDIT-TEST", "INV-C", "Investor C Capital", 25.0, datetime(2025, 1, 1))

# Ownership change
add_investor("AUDIT-TEST", "INV-A", "Investor A LLC", 30.0, datetime(2025, 2, 15))
add_investor("AUDIT-TEST", "INV-D", "Investor D Partners", 10.0, datetime(2025, 2, 15))

print("\n📝 Adding fees...")
add_fee(
    loan_id="AUDIT-TEST",
    fee_date=datetime(2025, 2, 15),
    fee_type="prepayment_fee",
    amount=10000.00,
    period_number=2,
    description="Prepayment penalty - 2% of prepayment"
)

add_fee(
    loan_id="AUDIT-TEST",
    fee_date=datetime(2025, 2, 20),
    fee_type="amendment_fee",
    amount=5000.00,
    period_number=2,
    description="Rate modification amendment"
)

# Add payments
add_payment("AUDIT-TEST", datetime(2025, 1, 31), 16250.00, "interest", period_number=1, notes="Period 1")
add_payment("AUDIT-TEST", datetime(2025, 2, 15), 500000.00, "principal_prepayment", notes="Prepayment")
add_payment("AUDIT-TEST", datetime(2025, 2, 28), 26633.33, "interest", period_number=2, notes="Period 2")

# Generate schedule
sofr_rates = load_sofr_rates()
schedule = loan.calculate_schedule(sofr_rates=sofr_rates)

# Generate schedule
sofr_rates = load_sofr_rates()
schedule = loan.calculate_schedule(sofr_rates=sofr_rates)

# Generate audit report
print("\n📊 Generating comprehensive audit report...")
filepath = generate_audit_report(
    loan=loan,
    schedule=schedule,
    loan_id="AUDIT-TEST"
)

print("📁 Open the Excel file to review all tabs:")
print("   - Loan Summary")
print("   - Period Detail")
print("   - Investor Allocations")
print("   - Payment Ledger")
print("   - Fee Income")
print("   - Ownership History")
print("   - Reconciliation")