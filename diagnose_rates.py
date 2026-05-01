"""
diagnose_rates.py  —  Rate precision diagnostic tool

Run this from the loan system folder:
    python diagnose_rates.py

It tests every step of the calculation chain and tells you exactly
where any rounding or precision loss is occurring.
"""

import sys
import os
import csv
import inspect
from datetime import datetime

print("=" * 70)
print("LOAN SYSTEM — RATE PRECISION DIAGNOSTIC")
print("=" * 70)
print(f"Python: {sys.version}")
print(f"Working dir: {os.getcwd()}")
print()

# ── 1. Verify source code is the updated version ─────────────────────────
print("─" * 70)
print("STEP 1: Verify source code versions")
print("─" * 70)

import interest_calculations
import sofr_rates as sofr_mod
import loan_storage
import loan_export

src = inspect.getsource(interest_calculations.calculate_effective_rate)
has_round = "round(adjusted_sofr + margin, 7)" in src
print(f"  interest_calculations.py  — round to 7 dp: {'✓ YES' if has_round else '✗ NO — old version!'}")
if not has_round:
    print("    FIX: This file is out of date. The line should be:")
    print("         effective_rate = round(adjusted_sofr + margin, 7)")

src = inspect.getsource(sofr_mod.add_sofr_rate)
has_7f = ":.7f" in src
print(f"  sofr_rates.py             — stores .7f:    {'✓ YES' if has_7f else '✗ NO — old version!'}")
if not has_7f:
    print("    FIX: term_sofr_1m line should use f\"{rate:.7f}\"")

src = inspect.getsource(loan_storage._loan_to_row)
margin_7f = '"margin":' in src and ':.7f' in src.split('"margin":')[1][:30]
print(f"  loan_storage.py           — margin .7f:    {'✓ YES' if margin_7f else '✗ NO — old version!'}")

src = inspect.getsource(loan_export.export_schedule_to_csv)
export_7f = "sofr_rate']:.7f" in src or "sofr_rate\']:.7f" in src
print(f"  loan_export.py            — exports .7f:   {'✓ YES' if export_7f else '✗ NO — old version!'}")

print()

# ── 2. Check sofr_rates.csv entries ──────────────────────────────────────
print("─" * 70)
print("STEP 2: SOFR rates in CSV")
print("─" * 70)

sofr_file = "data/sofr_rates.csv"
if not os.path.exists(sofr_file):
    print(f"  ✗ {sofr_file} not found")
else:
    with open(sofr_file) as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("  ✗ No rates in CSV")
    else:
        any_old = False
        for row in rows:
            rate_str = row['term_sofr_1m']
            dp = len(rate_str.split('.')[-1]) if '.' in rate_str else 0
            pct = float(rate_str) * 100
            status = "✓" if dp >= 7 else "⚠ OLD FORMAT"
            if dp < 7:
                any_old = True
            print(f"  {row['reset_date']}: \"{rate_str}\" ({dp} dp as decimal = {pct:.5f}%)  {status}")
        if any_old:
            print()
            print("  FIX: Re-enter old-format rates with:")
            print("       python cli.py add-rate YYYY-MM-DD RATE.XXXXX")
            print("       (rate entered as a percentage, e.g. 5.05691)")

print()

# ── 3. Check loans.csv margin precision ──────────────────────────────────
print("─" * 70)
print("STEP 3: Loan margins in loans.csv")
print("─" * 70)

loans_file = "data/loans.csv"
if not os.path.exists(loans_file):
    print(f"  ✗ {loans_file} not found")
else:
    with open(loans_file) as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("  No loans found")
    else:
        for row in rows:
            m = row.get('margin', '')
            dp = len(m.split('.')[-1]) if '.' in m else 0
            pct = float(m) * 100 if m else 0
            status = "✓" if dp >= 7 else "⚠ (re-save loan to update)"
            print(f"  {row['loan_id']}: margin=\"{m}\" ({dp} dp) = {pct:.5f}%  {status}")

print()

# ── 4. Live calculation test ──────────────────────────────────────────────
print("─" * 70)
print("STEP 4: Live calculation test (SOFR=5.05691%, margin=8.5%)")
print("─" * 70)

from interest_calculations import calculate_effective_rate, calculate_period_interest

sofr   = 5.05691 / 100   # 0.0505691
margin = 8.5    / 100    # 0.0850000

eff = calculate_effective_rate(sofr, margin, floor=0.0)

print(f"  Input  sofr:          {sofr:.7f}  ({sofr*100:.5f}%)")
print(f"  Input  margin:        {margin:.7f}  ({margin*100:.5f}%)")
print(f"  Output effective:     {eff:.7f}  ({eff*100:.5f}%)")
expected_eff = 0.1355691
ok = abs(eff - expected_eff) < 1e-9
print(f"  Expected 0.1355691:   {'✓ MATCH' if ok else f'✗ MISMATCH — got {eff:.10f}'}")

interest_28 = calculate_period_interest(1_000_000, eff, 28)
interest_28r = round(interest_28, 2)
print()
print(f"  Interest $1M × {eff*100:.5f}% × 28/360:")
print(f"    Raw:     ${interest_28:.6f}")
print(f"    Rounded: ${interest_28r:,.2f}")
expected_int = round(1_000_000 * 0.1355691 * 28/360, 2)
ok2 = interest_28r == expected_int
print(f"    Expected ${expected_int:,.2f}: {'✓ MATCH' if ok2 else f'✗ MISMATCH'}")

print()

# ── 5. Full schedule test against first available loan ───────────────────
print("─" * 70)
print("STEP 5: Full schedule for first loan in system")
print("─" * 70)

try:
    from loan_storage import list_all_loans, load_loan
    from sofr_rates import load_sofr_rates

    ids = list_all_loans()
    if not ids:
        print("  No loans found — skipping")
    else:
        loan_id = ids[0]
        loan = load_loan(loan_id)
        rates = load_sofr_rates()
        print(f"  Loan: {loan_id}  margin={loan.margin:.7f} ({loan.margin*100:.5f}%)")

        schedule = loan.calculate_schedule(sofr_rates=rates, include_payment_status=False)
        print()
        print(f"  {'Per':<4} {'SOFR%':>10} {'Margin%':>10} {'Eff%':>12} {'Sum=Eff':>8} {'Days':>5} {'Interest':>12}")
        print(f"  {'-'*4} {'-'*10} {'-'*10} {'-'*12} {'-'*8} {'-'*5} {'-'*12}")

        any_mismatch = False
        for p in schedule:
            s   = p['sofr_rate']
            m   = p['margin']
            e   = p['effective_rate']
            d   = p['days']
            i   = p['interest_owed']
            # Check: does sofr + margin = effective (within floor/ceiling logic)?
            raw_sum = round(s + m, 7)
            # (may differ if floor/ceiling applied)
            match = "✓" if abs(raw_sum - e) < 1e-7 or e != raw_sum else "⚠floor"
            if abs(raw_sum - e) >= 1e-7 and e != raw_sum:
                any_mismatch = True
            print(f"  {p['period_number']:<4} {s*100:>10.5f} {m*100:>10.5f} {e*100:>12.5f} {match:>8} {d:>5} ${i:>11,.2f}")

        if not any_mismatch:
            print()
            print("  ✓ All effective rates match SOFR + margin")

except Exception as ex:
    print(f"  Error: {ex}")

print()
print("=" * 70)
print("DIAGNOSTIC COMPLETE")
print("=" * 70)
