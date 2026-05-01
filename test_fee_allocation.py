from datetime import datetime
from fees import add_fee, load_fees
from investors import add_investor
from fee_allocation import (
    allocate_fee_to_investors,
    get_period_fees_with_allocations,
    calculate_investor_fee_totals
)
import os

# Clean up
for filepath in ['data/fees.csv', 'data/investors.csv']:
    if os.path.exists(filepath):
        os.remove(filepath)

print("=" * 80)
print("TESTING FEE ALLOCATION")
print("=" * 80)

# Add investors for TEST-001
print("\n1. Adding investors...")
add_investor("TEST-001", "INV-A", "Investor A LLC", "Inv-A", 40.0, datetime(2025, 1, 1))
add_investor("TEST-001", "INV-B", "Investor B Fund", "Inv-B", 35.0, datetime(2025, 1, 1))
add_investor("TEST-001", "INV-C", "Investor C Capital", "Inv-C", 25.0, datetime(2025, 1, 1))

# Add fees
print("\n2. Adding fees...")
add_fee(
    loan_id="TEST-001",
    fee_date=datetime(2025, 2, 15),
    fee_type="prepayment_fee",
    amount=10000.00,
    period_number=2,
    description="Early payoff penalty"
)

add_fee(
    loan_id="TEST-001",
    fee_date=datetime(2025, 2, 20),
    fee_type="amendment_fee",
    amount=5000.00,
    period_number=2,
    description="Rate modification"
)

# Test allocation
print("\n3. Testing fee allocation...")
print("\nPrepayment Fee Allocation (Feb 15, $10,000):")
print("-" * 80)

allocation = allocate_fee_to_investors(
    loan_id="TEST-001",
    fee_date=datetime(2025, 2, 15),
    fee_amount=10000.00,
    fee_type="prepayment_fee"
)

for inv in allocation['investor_allocations']:
    print(f"{inv['investor_name']:20} | "
          f"{inv['ownership_pct']:5.1f}% | "
          f"${inv['fee_share']:>10,.2f}")

print(f"\n{'TOTAL':20} | {'100.0%':>6} | "
      f"${sum(i['fee_share'] for i in allocation['investor_allocations']):>10,.2f}")

# Test period fees with allocations
print("\n4. Testing period fees with allocations...")
print("\nPeriod 2 Fees:")
print("-" * 80)

period_fees = get_period_fees_with_allocations("TEST-001", 2)

for fee in period_fees:
    print(f"\n{fee['fee_type'].upper()} - ${fee['amount']:,.2f} ({fee['fee_date'].strftime('%Y-%m-%d')})")
    print(f"Description: {fee['description']}")
    print("\nAllocations:")
    for inv in fee['allocations']['investor_allocations']:
        print(f"  {inv['investor_name']:20} | ${inv['fee_share']:>10,.2f}")

# Test investor fee totals
print("\n5. Testing investor fee totals...")
print("\nInvestor A - Period 2 Fee Summary:")
print("-" * 80)

inv_a_fees = calculate_investor_fee_totals("TEST-001", 2, "INV-A")

print(f"\nFee Details:")
for detail in inv_a_fees['fee_details']:
    print(f"  {detail['display_name']:20} | "
          f"{detail['fee_date'].strftime('%Y-%m-%d')} | "
          f"${detail['investor_share']:>10,.2f} | "
          f"({detail['ownership_pct']:.1f}% of ${detail['total_amount']:,.2f})")

print(f"\n{'Total Fees:':20} | {'':<10} | ${inv_a_fees['total_fees']:>10,.2f}")

print("\n" + "=" * 80)
print("✅ FEE ALLOCATION TESTS COMPLETE")
print("=" * 80)