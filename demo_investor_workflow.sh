#!/bin/bash

echo "============================================"
echo "INVESTOR REPORTING WORKFLOW DEMO"
echo "============================================"

# Clean up
echo ""
echo "🧹 Cleaning up old data..."
rm -f data/investors.csv data/payments.csv
rm -rf output/investor_reports

# Step 1: Create loan
echo ""
echo "📋 Step 1: Creating loan..."
python cli.py create \
  --loan-id LOAN-ABC \
  --borrower "ABC Company LLC" \
  --loan-name "ABC" \
  --principal 5000000 \
  --margin 2.5 \
  --origination-date 2025-01-15 \
  --maturity-date 2025-03-31

# Step 2: Add investors
echo ""
echo "👥 Step 2: Adding investors..."
python cli.py add-investor \
  --loan-id LOAN-ABC \
  --investor-id INV-A \
  --investor-name "Investor A LLC" \
  --ownership-pct 40.0 \
  --effective-date 2025-01-01

python cli.py add-investor \
  --loan-id LOAN-ABC \
  --investor-id INV-B \
  --investor-name "Investor B Fund" \
  --ownership-pct 60.0 \
  --effective-date 2025-01-01

# Step 3: Record activity
echo ""
echo "💰 Step 3: Recording principal prepayment..."
python cli.py add-payment \
  --loan-id LOAN-ABC \
  --date 2025-02-15 \
  --amount 500000.00 \
  --type principal_prepayment \
  --notes "Mid-period prepayment"

# Step 4: List investors
echo ""
echo "👥 Step 4: Current investor ownership..."
python cli.py list-investors LOAN-ABC

# Step 5: Generate investor reports (Python script needed)
echo ""
echo "📊 Step 5: Generating investor reports..."
python - <<EOF
from datetime import datetime
from loan import Loan
from investor_allocation import allocate_period_to_investors
from investor_reports import generate_all_investor_statements_for_loan
from sofr_rates import load_sofr_rates

# Recreate loan
loan = Loan(
    loan_id="LOAN-ABC",
    borrower="ABC Company LLC",
    loan_name="ABC",
    principal=5000000,
    margin=0.025,
    origination_date=datetime(2025, 1, 15),
    maturity_date=datetime(2025, 3, 31)
)

# Generate schedule
sofr_rates = load_sofr_rates()
schedule = loan.calculate_schedule(sofr_rates=sofr_rates, include_payment_status=False)

# Generate reports for Period 2
allocation = allocate_period_to_investors("LOAN-ABC", schedule[1])
filepaths = generate_all_investor_statements_for_loan(
    loan=loan,
    period_data=schedule[1],
    allocation_data=allocation,
    company_name="ABC Capital Management"
)

print(f"\n✅ Generated {len(filepaths)} investor reports")
for fp in filepaths:
    print(f"   {fp}")
EOF

echo ""
echo "============================================"
echo "✅ WORKFLOW COMPLETE!"
echo "============================================"
echo ""
echo "📁 Check these directories:"
echo "   - output/LOAN-ABC_schedule.csv (loan schedule)"
echo "   - output/investor_reports/ (investor statements)"
echo ""