"""
Regression test for amendment-aware OID handling.

Scenario:
  * Loan originated 2024-01-01, matures 2027-01-01 (3 yrs, monthly periods).
  * Cash OID $1,000,000 amortized day-weighted over original 3-yr life.
  * Warrant OID $300,000 amortized the same way.
  * After 12 periods (~Dec 2024), an amendment effective 2025-01-01 extends
    maturity to 2028-01-01 (one extra year) and capitalizes a $200,000
    amendment fee as additional cash OID. No new warrants are issued.

Assertions:
  (1) Pre-amendment periods (1..12) keep their ORIGINAL day-weighted OID
      (computed against the original 3-yr horizon).  No retroactive re-slicing.
  (2) Σ(period_oid over the whole life) == oid_amount + additional_oid (penny-tie).
  (3) Σ(period_warrant_oid over the whole life) == warrant_oid_amount.
  (4) Post-amendment periods (13..N) amortize the residual + $200K over
      (2025-01-01 → 2028-01-01).  Per-period values are CONSISTENT (within
      a penny of the calculated rate * period.days), and the unamortized
      residual drops to zero by maturity.
  (5) Warrant OID residual re-amortizes over the extended life — last period's
      warrant_oid_unamortized_end ≈ 0.

Run hermetically by chdir-ing into a temp directory and seeding minimal
SOFR rates so calculate_schedule succeeds.
"""

import os
import shutil
import tempfile
from datetime import datetime

# Run before any imports that grab default filepaths
_TMP = tempfile.mkdtemp(prefix="oid_amend_test_")
_ORIG_CWD = os.getcwd()
os.chdir(_TMP)
os.makedirs("data", exist_ok=True)

# Now imports — they will resolve "data/..." inside the temp dir
from loan import Loan
from loan_storage import save_loan, activate_loan, load_loan, amend_loan
from oid_amendments import record_oid_amendment, load_oid_amendments
from business_days import get_us_bank_holidays, add_business_days
from sofr_rates import add_sofr_rate


def _seed_sofr_for(loan: Loan) -> None:
    """Write a flat 5% SOFR for every reset date the loan needs."""
    for reset in loan.get_required_sofr_dates():
        add_sofr_rate(reset, 0.05, source="TEST")


def main() -> int:
    try:
        # ── 1. Create & activate the loan ────────────────────────────────
        orig    = datetime(2024, 1, 1)
        mat_old = datetime(2027, 1, 1)

        loan = Loan(
            loan_id="OID-AMEND-TEST",
            borrower="Test Borrower",
            principal=10_000_000.0,
            margin=0.03,
            origination_date=orig,
            maturity_date=mat_old,
            oid_amount=1_000_000.0,
            warrant_oid_amount=300_000.0,
            closing_expenses=0.0,
        )
        save_loan(loan)
        activate_loan("OID-AMEND-TEST")
        _seed_sofr_for(loan)

        # ── 2. Baseline schedule (pre-amendment) ─────────────────────────
        baseline = loan.calculate_schedule(include_payment_status=False)
        # Snapshot the first 12 periods' OID values
        pre_oid_snapshot = [
            (e['period_number'], e['period_oid'], e['period_warrant_oid'])
            for e in baseline[:12]
        ]
        baseline_total_oid         = round(sum(e['period_oid'] for e in baseline), 2)
        baseline_total_warrant_oid = round(sum(e['period_warrant_oid'] for e in baseline), 2)

        assert baseline_total_oid == 1_000_000.00, \
            f"baseline cash OID Σ = {baseline_total_oid}, expected 1,000,000.00"
        assert baseline_total_warrant_oid == 300_000.00, \
            f"baseline warrant OID Σ = {baseline_total_warrant_oid}, expected 300,000.00"

        # Residual cash OID & warrant OID at end of period 12
        period12 = baseline[11]
        residual_cash_oid    = period12['oid_unamortized_end']
        residual_warrant_oid = period12['warrant_oid_unamortized_end']

        # ── 3. Amend: extend maturity 1yr, add $200k cash OID ────────────
        mat_new       = datetime(2028, 1, 1)
        eff_date      = datetime(2025, 1, 1)
        additional    = 200_000.0

        record_oid_amendment(
            loan_id="OID-AMEND-TEST",
            effective_date=eff_date,
            prior_maturity_date=mat_old,
            new_maturity_date=mat_new,
            additional_oid=additional,
            reason="Test: extend 1yr + $200k amendment fee capitalized",
            recorded_by="test",
        )

        amended = Loan(
            loan_id="OID-AMEND-TEST",
            borrower="Test Borrower",
            principal=10_000_000.0,
            margin=0.03,
            origination_date=orig,
            maturity_date=mat_new,
            oid_amount=1_000_000.0,             # original, unchanged
            warrant_oid_amount=300_000.0,       # original, unchanged
        )
        amended.created_at   = loan.created_at
        amended.activated_at = loan.activated_at
        amend_loan(amended,
                   change_reason="Test: extend 1yr + $200k amendment fee",
                   changed_by="test")
        # SOFR for the extra year
        _seed_sofr_for(amended)

        # ── 4. Post-amendment schedule ───────────────────────────────────
        post = amended.calculate_schedule(include_payment_status=False)

        # (1) Pre-amendment periods unchanged
        for (pn, old_oid, old_warr), entry in zip(pre_oid_snapshot, post[:12]):
            assert entry['period_number'] == pn
            assert entry['period_oid'] == old_oid, (
                f"Period {pn} cash OID changed after amendment: "
                f"was {old_oid}, now {entry['period_oid']}"
            )
            assert entry['period_warrant_oid'] == old_warr, (
                f"Period {pn} warrant OID changed after amendment: "
                f"was {old_warr}, now {entry['period_warrant_oid']}"
            )

        # (2) Cash OID sum ties to original + additional
        total_cash = round(sum(e['period_oid'] for e in post), 2)
        expected_cash = round(1_000_000.0 + additional, 2)
        assert total_cash == expected_cash, \
            f"cash OID Σ = {total_cash}, expected {expected_cash}"

        # (3) Warrant OID sum ties to original (no additions)
        total_warr = round(sum(e['period_warrant_oid'] for e in post), 2)
        assert total_warr == 300_000.00, \
            f"warrant OID Σ = {total_warr}, expected 300,000.00"

        # (4a) Period 13 unamortized_start should reflect the addition crediting
        period13 = post[12]
        assert period13['start_date'].date() == eff_date.date(), (
            f"period 13 start expected {eff_date.date()}, got {period13['start_date'].date()}"
        )
        expected_carry_in = round(residual_cash_oid + additional, 2)
        assert period13['oid_unamortized_start'] == expected_carry_in, (
            f"period 13 cash OID unamortized_start = {period13['oid_unamortized_start']}, "
            f"expected residual {residual_cash_oid} + additional {additional} "
            f"= {expected_carry_in}"
        )

        # (4b) Warrant residual carried in unchanged (no addition)
        assert period13['warrant_oid_unamortized_start'] == residual_warrant_oid, (
            f"period 13 warrant unamortized_start = "
            f"{period13['warrant_oid_unamortized_start']}, expected {residual_warrant_oid}"
        )

        # (5) Terminal residuals drive to zero
        last = post[-1]
        assert last['oid_unamortized_end'] == 0.0, \
            f"final cash OID unamortized_end = {last['oid_unamortized_end']}, expected 0"
        assert last['warrant_oid_unamortized_end'] == 0.0, \
            f"final warrant OID unamortized_end = {last['warrant_oid_unamortized_end']}, expected 0"

        # ── 5. Inspect the post-amendment per-period rate ────────────────
        # Periods 13.. should have per-period OID consistent with day-weighted
        # carry_in over (eff_date → mat_new).  Spot-check period 13.
        horizon_days = (mat_new - eff_date).days
        expected_p13 = round(expected_carry_in * period13['days'] / horizon_days, 2)
        # Allow ±$0.02 tolerance for compounded penny-rounding
        assert abs(period13['period_oid'] - expected_p13) <= 0.02, (
            f"period 13 cash OID = {period13['period_oid']}, "
            f"expected ≈ {expected_p13} (carry_in {expected_carry_in} * "
            f"{period13['days']}/{horizon_days})"
        )

        print("=" * 72)
        print("✅ All amendment-aware OID assertions passed.")
        print("-" * 72)
        print(f"Pre-amend period 12: cash residual=${residual_cash_oid:,.2f}  "
              f"warrant residual=${residual_warrant_oid:,.2f}")
        print(f"Amendment effective {eff_date.date()}: + ${additional:,.2f} cash OID, "
              f"maturity extended to {mat_new.date()}")
        print(f"Post-amend period 13: cash OID=${period13['period_oid']:,.2f}  "
              f"warrant OID=${period13['period_warrant_oid']:,.2f}")
        print(f"Σ cash OID = ${total_cash:,.2f}  (orig $1,000,000 + add ${additional:,.0f})")
        print(f"Σ warrant OID = ${total_warr:,.2f}  (orig $300,000, no additions)")
        print(f"Last period unamortized: cash=${last['oid_unamortized_end']:.2f}, "
              f"warrant=${last['warrant_oid_unamortized_end']:.2f}")
        return 0
    finally:
        os.chdir(_ORIG_CWD)
        shutil.rmtree(_TMP, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
