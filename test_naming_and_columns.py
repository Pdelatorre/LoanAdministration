from datetime import datetime
from loan import Loan
from investors import add_investor
from fees import add_fee
from payments import add_payment
from investor_allocation import allocate_period_to_investors
from investor_reports import generate_all_investor_statements_for_loan
from investor_reports_pdf import generate_all_investor_pdfs
from audit_reports import generate_audit_report
from sofr_rates import load_sofr_rates
import os

# Clean up
for filepath in ['data/investors.csv', 'data/fees.csv', 'data/payments.csv']:
    if os.path.exists(filepath):
        os.remove(filepath)

print("=" * 80)
print("TESTING: New Naming Convention & Removed Principal Activity Column")
print("=" * 80)

# Create loan with a realistic name
loan = Loan(
    loan_id="LOAN-001",
    borrower="ABC Company LLC",
    loan_name="ABC Loan",  # This will be used in filenames
    principal=5000000,
    margin=0.025,
    origination_date=datetime(2025, 1, 15),
    maturity_date=datetime(2025, 4, 30)
)

# Add investors with short names
print("\n1. Adding investors with short names...")
add_investor(
    loan_id="LOAN-001",
    investor_id="INV-A",
    investor_name="Investor A LLC",
    investor_short_name="InvestorA",  # NEW
    ownership_pct=40.0,
    effective_date=datetime(2025, 1, 1)
)

add_investor(
    loan_id="LOAN-001",
    investor_id="INV-B",
    investor_name="Sovereign Wealth Fund",
    investor_short_name="SovereignFund",  # NEW
    ownership_pct=60.0,
    effective_date=datetime(2025, 1, 1)
)

# Add a mid-period prepayment
print("\n2. Adding principal prepayment...")
add_payment(
    loan_id="LOAN-001",
    payment_date=datetime(2025, 2, 15),
    amount=500000.00,
    payment_type="principal_prepayment",
    notes="Mid-period prepayment"
)

# Add fees
print("\n3. Adding fees...")
add_fee(
    loan_id="LOAN-001",
    fee_date=datetime(2025, 2, 20),
    fee_type="prepayment_fee",
    amount=10000.00,
    period_number=2,
    description="Prepayment penalty - 2%"
)

add_fee(
    loan_id="LOAN-001",
    fee_date=datetime(2025, 2, 25),
    fee_type="amendment_fee",
    amount=5000.00,
    period_number=2,
    description="Rate modification"
)

# Generate schedule
print("\n4. Generating loan schedule...")
sofr_rates = load_sofr_rates()
schedule = loan.calculate_schedule(sofr_rates=sofr_rates)

# Get Period 2
period_2 = schedule[1]

# Allocate to investors
print("\n5. Allocating period to investors...")
allocation = allocate_period_to_investors("LOAN-001", period_2)

# Check investor data includes short_name
print("\n6. Verifying investor_short_name in allocation...")
for inv in allocation['investor_allocations']:
    print(f"   {inv['investor_name']:30} | Short: {inv.get('investor_short_name', 'MISSING')}")

# Generate text reports
print("\n7. Generating text reports...")
text_files = generate_all_investor_statements_for_loan(
    loan=loan,
    period_data=period_2,
    allocation_data=allocation
)

print("\n📄 Text report filenames:")
for f in text_files:
    print(f"   {os.path.basename(f)}")

# Generate PDFs
print("\n8. Generating PDF reports...")
pdf_files = generate_all_investor_pdfs(
    loan=loan,
    period_data=period_2,
    allocation_data=allocation
)

print("\n📄 PDF filenames:")
for f in pdf_files:
    print(f"   {os.path.basename(f)}")

# Generate audit report
print("\n9. Generating audit report...")
audit_file = generate_audit_report(
    loan=loan,
    schedule=schedule,
    loan_id="LOAN-001"
)

print(f"\n📊 Audit report filename:")
print(f"   {os.path.basename(audit_file)}")

# Show preview of one text report
print("\n" + "=" * 80)
print("SAMPLE TEXT REPORT (InvestorA):")
print("=" * 80)
with open(text_files[0], 'r') as f:
    content = f.read()
    # Show first 50 lines
    lines = content.split('\n')[:50]
    print('\n'.join(lines))

print("\n" + "=" * 80)
print("✅ TEST COMPLETE")
print("=" * 80)

print("\n📋 Expected Results:")
print("   ✓ Filenames use 'ABC_Loan' instead of 'LOAN-001'")
print("   ✓ Filenames use 'InvestorA' and 'SovereignFund' instead of 'INV-A' and 'INV-B'")
print("   ✓ Tables show 4 columns (no Principal Activity column)")
print("   ✓ Prepayment shown below tables in 'Activity During Period'")
print("   ✓ Fees shown in ADDITIONAL INCOME section")

print("\n📁 Check these files:")
print("   - output/investor_reports/ABC_Loan_Period2_InvestorA.txt")
print("   - output/investor_reports_pdf/ABC_Loan_Period2_InvestorA.pdf")
print(f"   - {audit_file}")