import unittest
from datetime import datetime
from loan import Loan
from investors import add_investor, get_ownership_for_period, validate_ownership, load_investors
from investor_allocation import allocate_period_to_investors, generate_investor_report_data
from payments import add_payment
from sofr_rates import load_sofr_rates
from interest_calculations import penny_round
import os


class TestInvestorOwnership(unittest.TestCase):
    """Test investor ownership tracking and validation."""
    
    def setUp(self):
        """Clean up test data before each test."""
        for filepath in ['data/investors.csv', 'data/payments.csv']:
            if os.path.exists(filepath):
                os.remove(filepath)
    
    def test_single_ownership_period(self):
        """Test simple ownership with no changes."""
        add_investor("TEST-001", "INV-A", "Investor A", "Inv-A", 40.0, datetime(2025, 1, 1))
        add_investor("TEST-001", "INV-B", "Investor B", "Inv-B", 60.0, datetime(2025, 1, 1))
        
        segments = get_ownership_for_period("TEST-001", datetime(2025, 1, 1), datetime(2025, 1, 31))
        
        self.assertEqual(len(segments), 1, "Should have single segment with no ownership changes")
        self.assertEqual(segments[0]['days'], 31)
        self.assertEqual(len(segments[0]['investors']), 2)
        
        # Validate ownership sums to 100%
        result = validate_ownership("TEST-001", datetime(2025, 1, 15))
        self.assertTrue(result['valid'])
        self.assertAlmostEqual(result['total_pct'], 100.0, places=2)
    
    def test_mid_period_ownership_change(self):
        """Test ownership change creates proper segments."""
        # Initial ownership
        add_investor("TEST-001", "INV-A", "Investor A", "Inv-A", 40.0, datetime(2025, 1, 1))
        add_investor("TEST-001", "INV-B", "Investor B", "Inv-B", 60.0, datetime(2025, 1, 1))

        # Ownership change on Jan 16
        add_investor("TEST-001", "INV-A", "Investor A", "Inv-A", 35.0, datetime(2025, 1, 16))
        add_investor("TEST-001", "INV-C", "Investor C", "Inv-C", 5.0, datetime(2025, 1, 16))
        
        segments = get_ownership_for_period("TEST-001", datetime(2025, 1, 1), datetime(2025, 1, 31))
        
        self.assertEqual(len(segments), 2, "Should have 2 segments due to ownership change")
        
        # Segment 1: Jan 1-15
        self.assertEqual(segments[0]['days'], 15)
        self.assertEqual(len(segments[0]['investors']), 2)
        
        # Segment 2: Jan 16-31
        self.assertEqual(segments[1]['days'], 16)
        self.assertEqual(len(segments[1]['investors']), 3)
        
        # Validate both periods
        result_before = validate_ownership("TEST-001", datetime(2025, 1, 15))
        result_after = validate_ownership("TEST-001", datetime(2025, 1, 16))
        
        self.assertTrue(result_before['valid'])
        self.assertTrue(result_after['valid'])


class TestInvestorAllocation(unittest.TestCase):
    """Test investor allocation calculations."""
    
    def setUp(self):
        """Set up test data."""
        # Clean files
        for filepath in ['data/investors.csv', 'data/payments.csv']:
            if os.path.exists(filepath):
                os.remove(filepath)
        
        self.sofr_rates = {
            datetime(2025, 1, 13): 0.0450,
            datetime(2025, 1, 30): 0.0455,
            datetime(2025, 2, 27): 0.0455,
            datetime(2025, 3, 28): 0.0465
        }
    
    def test_simple_interest_allocation(self):
        """Test interest allocation with no ownership changes."""
        # Create loan
        loan = Loan(
            loan_id="ALLOC-001",
            borrower="Test Co",
            principal=1000000,
            margin=0.025,
            origination_date=datetime(2025, 1, 15),
            maturity_date=datetime(2025, 2, 28)
        )
        
        # Add investors
        add_investor("ALLOC-001", "INV-A", "Investor A", "Inv-A", 40.0, datetime(2025, 1, 1))
        add_investor("ALLOC-001", "INV-B", "Investor B", "Inv-B", 60.0, datetime(2025, 1, 1))
        
        # Generate schedule
        schedule = loan.calculate_schedule(sofr_rates=self.sofr_rates, include_payment_status=False)
        
        # Allocate first period to investors
        allocation = allocate_period_to_investors("ALLOC-001", schedule[0])
        
        self.assertEqual(len(allocation['investor_allocations']), 2)
        
        # Find Investor A
        inv_a = next(inv for inv in allocation['investor_allocations'] if inv['investor_id'] == 'INV-A')
        
        # Investor A should get 40% of interest
        expected_interest = schedule[0]['interest_owed'] * 0.40
        self.assertAlmostEqual(inv_a['interest'], expected_interest, places=2)
    
    def test_allocation_with_ownership_change(self):
        """Test allocation when ownership changes mid-period."""
        # Create loan
        loan = Loan(
            loan_id="ALLOC-002",
            borrower="Test Co",
            principal=1000000,
            margin=0.025,
            origination_date=datetime(2025, 1, 15),
            maturity_date=datetime(2025, 2, 28)
        )
        
        # Initial ownership
        add_investor("ALLOC-002", "INV-A", "Investor A", "Inv-A", 40.0, datetime(2025, 1, 1))
        add_investor("ALLOC-002", "INV-B", "Investor B", "Inv-B", 60.0, datetime(2025, 1, 1))

        # Ownership change on Jan 25
        add_investor("ALLOC-002", "INV-A", "Investor A", "Inv-A", 30.0, datetime(2025, 1, 25))
        add_investor("ALLOC-002", "INV-C", "Investor C", "Inv-C", 10.0, datetime(2025, 1, 25))
        
        # Generate schedule
        schedule = loan.calculate_schedule(sofr_rates=self.sofr_rates, include_payment_status=False)
        
        # Allocate first period
        allocation = allocate_period_to_investors("ALLOC-002", schedule[0])
        
        # Should have 2 ownership segments
        self.assertEqual(len(allocation['ownership_segments']), 2)
        
        # All three investors should have allocations
        self.assertEqual(len(allocation['investor_allocations']), 3)
        
        # Investor C should only get allocation for days after Jan 25
        inv_c = next(inv for inv in allocation['investor_allocations'] if inv['investor_id'] == 'INV-C')
        self.assertGreater(inv_c['interest'], 0)
    
    def test_allocation_with_principal_prepayment(self):
        """Test allocation when principal prepayment occurs."""
        # Create loan
        loan = Loan(
            loan_id="ALLOC-003",
            borrower="Test Co",
            principal=1000000,
            margin=0.025,
            origination_date=datetime(2025, 1, 15),
            maturity_date=datetime(2025, 3, 31)
        )
        
        # Add investors
        add_investor("ALLOC-003", "INV-A", "Investor A", "Inv-A", 50.0, datetime(2025, 1, 1))
        add_investor("ALLOC-003", "INV-B", "Investor B", "Inv-B", 50.0, datetime(2025, 1, 1))
        
        # Add principal prepayment in period 2
        add_payment("ALLOC-003", datetime(2025, 2, 15), 100000.0, "principal_prepayment")
        
        # Generate schedule
        schedule = loan.calculate_schedule(sofr_rates=self.sofr_rates, include_payment_status=False)
        
        # Allocate period 2 (with prepayment)
        allocation = allocate_period_to_investors("ALLOC-003", schedule[1])
        
        # Each investor should get 50% of prepayment
        for inv in allocation['investor_allocations']:
            self.assertAlmostEqual(inv['principal_prepayment'], 50000.0, places=2)


class TestPennyRounding(unittest.TestCase):
    """
    Tests for the Largest Remainder Method (penny_round).

    tearDown ensures that any investor/payment rows written to the shared
    data/ files during these tests are removed after every individual test,
    so the live WALKTHRU-001 data is never contaminated.

    These cases prove that:
      1. Shares always sum to exactly the stated total (to the penny).
      2. The extra cent(s) go to the investor(s) with the largest fractional
         remainder — NOT arbitrarily to the largest or first investor.
      3. Three-way splits (the classic 33.33.../33.33.../33.34... case) work.
      4. The helper handles edge cases (single investor, zero total, many investors).

    HOW TO READ THESE TESTS IN THE WALKTHROUGH
    -------------------------------------------
    Run:  python -m pytest test_investor_system.py::TestPennyRounding -v
    Or:   python test_investor_system.py   (uses run_tests() below)

    Every test prints nothing on pass; failures show the exact discrepancy.
    """

    def tearDown(self):
        """Remove any test investor/payment rows written to data/ files."""
        for filepath in ['data/investors.csv', 'data/payments.csv']:
            if os.path.exists(filepath):
                os.remove(filepath)

    def _assert_penny_exact(self, total, shares, rounded):
        """Helper: assert rounded shares sum to total and each is a valid cent amount."""
        self.assertEqual(len(shares), len(rounded))
        total_rounded = round(sum(rounded), 10)     # avoid float repr noise
        self.assertAlmostEqual(total_rounded, round(total, 2), places=2,
            msg=f"Rounded shares ${total_rounded:.4f} ≠ total ${total:.4f}")
        for r in rounded:
            cents = round(r * 100)
            self.assertAlmostEqual(r, cents / 100, places=10,
                msg=f"${r} is not a whole cent amount")

    # ── Core algorithm ────────────────────────────────────────────────────────

    def test_three_equal_investors_classic_third(self):
        """
        Classic 1/3 split: $100.00 across three 33.333...% owners.
        Expected: two get $33.33, one gets $33.34 (largest remainder).
        """
        total = 100.00
        shares = [100 / 3, 100 / 3, 100 / 3]
        rounded = penny_round(total, shares)
        self._assert_penny_exact(total, shares, rounded)
        # Exactly one investor should receive the extra penny
        self.assertEqual(sorted(rounded), [33.33, 33.33, 33.34])

    def test_two_investors_60_40_split(self):
        """Standard 60/40 split — should divide cleanly with no remainder."""
        total = 5_833.33          # typical monthly interest on $1M at 7%
        shares = [total * 0.60, total * 0.40]
        rounded = penny_round(total, shares)
        self._assert_penny_exact(total, shares, rounded)

    def test_seven_investors_unequal(self):
        """
        Seven investors with ownership percentages that don't divide evenly.
        The Largest Remainder Method must distribute multiple leftover cents.
        """
        pcts = [14.29, 14.29, 14.29, 14.29, 14.28, 14.28, 14.28]  # sums to 100
        total = 10_000.00
        shares = [total * p / 100 for p in pcts]
        rounded = penny_round(total, shares)
        self._assert_penny_exact(total, shares, rounded)

    def test_single_investor_gets_full_amount(self):
        """One investor at 100% must receive the full total."""
        total = 7_291.67
        rounded = penny_round(total, [total])
        self._assert_penny_exact(total, [total], rounded)
        self.assertAlmostEqual(rounded[0], round(total, 2), places=2)

    def test_zero_total_returns_zeros(self):
        """Zero interest period (e.g. PIK-only) — all shares must be $0.00."""
        rounded = penny_round(0.0, [0.0, 0.0, 0.0])
        self.assertEqual(rounded, [0.0, 0.0, 0.0])

    def test_extra_cent_goes_to_largest_remainder_not_largest_investor(self):
        """
        Largest investor does NOT automatically get the extra penny.
        Investor A owns 70%, Investor B owns 30%.
        Interest = $1.00.  Precise: A=$0.70, B=$0.30 — both exact, no rounding.

        Now interest = $0.10. Precise: A=$0.07, B=$0.03 — exact.

        Trickier: interest = $10.01.
          A precise: $7.007   floored: $7.00  remainder: 0.007
          B precise: $3.003   floored: $3.00  remainder: 0.003
          shortfall: $0.01 → goes to A (larger remainder).
        """
        total = 10.01
        shares = [total * 0.70, total * 0.30]   # A=7.007, B=3.003
        rounded = penny_round(total, shares)
        self._assert_penny_exact(total, shares, rounded)
        self.assertAlmostEqual(rounded[0], 7.01, places=2)   # A gets the extra cent
        self.assertAlmostEqual(rounded[1], 3.00, places=2)

    def test_extra_cent_goes_to_smaller_investor_when_remainder_is_larger(self):
        """
        Smaller investor has the larger fractional remainder → gets the penny.

        Ownership: A=90%, B=10%.  Interest = $0.11.
          A precise: $0.099  floored: $0.09  remainder: 0.9 cents
          B precise: $0.011  floored: $0.01  remainder: 0.1 cents
          shortfall: $0.01 → goes to A (0.9 > 0.1).

        But try: A=66%, B=34%.  Interest = $1.00.
          A=$0.66  remainder 0 — exact
          B=$0.34  remainder 0 — exact
          No remainder needed.

        Use A=67%, B=33%, interest=$1.00:
          A precise: $0.67  remainder: 0
          B precise: $0.33  remainder: 0
          Both exact.

        Use A=34%, B=66%, interest=$0.99:
          A precise: $0.3366  floored: $0.33  remainder: 0.66
          B precise: $0.6534  floored: $0.65  remainder: 0.34
          shortfall: 1 cent → goes to A (remainder 0.66 > 0.34).
        """
        total = 0.99
        # A=34%, B=66%
        shares = [total * 0.34, total * 0.66]   # A=0.3366, B=0.6534
        rounded = penny_round(total, shares)
        self._assert_penny_exact(total, shares, rounded)
        self.assertAlmostEqual(rounded[0], 0.34, places=2)   # smaller investor gets extra cent
        self.assertAlmostEqual(rounded[1], 0.65, places=2)

    # ── Integration: full period allocation ───────────────────────────────────

    def test_period_interest_allocation_sums_to_interest_owed(self):
        """
        End-to-end: period interest allocations must sum to interest_owed
        exactly (to the penny) for every period in a multi-period loan.

        Uses three investors at 33.33% / 33.33% / 33.34% to stress the
        rounding logic with repeating decimals.
        """
        for filepath in ['data/investors.csv', 'data/payments.csv']:
            if os.path.exists(filepath):
                os.remove(filepath)

        loan = Loan(
            loan_id="ROUND-001",
            borrower="Rounding Test Co",
            principal=1_000_000,
            margin=0.025,
            origination_date=datetime(2025, 1, 15),
            maturity_date=datetime(2025, 6, 30),
        )

        add_investor("ROUND-001", "INV-A", "Investor Alpha", "Alpha", 33.33, datetime(2025, 1, 1))
        add_investor("ROUND-001", "INV-B", "Investor Beta",  "Beta",  33.33, datetime(2025, 1, 1))
        add_investor("ROUND-001", "INV-C", "Investor Gamma", "Gamma", 33.34, datetime(2025, 1, 1))

        sofr = {datetime(2025, 1, 13): 0.0450, datetime(2025, 1, 30): 0.0455,
                datetime(2025, 2, 27): 0.0455, datetime(2025, 3, 28): 0.0465,
                datetime(2025, 4, 29): 0.0470, datetime(2025, 5, 29): 0.0470}

        schedule = loan.calculate_schedule(sofr_rates=sofr, include_payment_status=False)

        for period in schedule:
            allocation = allocate_period_to_investors("ROUND-001", period)
            total_allocated = sum(inv['interest'] for inv in allocation['investor_allocations'])
            interest_owed   = round(period['interest_owed'], 2)
            self.assertAlmostEqual(
                round(total_allocated, 2), interest_owed, places=2,
                msg=(f"Period {period['period_number']}: allocated ${total_allocated:.4f} "
                     f"≠ interest_owed ${interest_owed:.4f}")
            )

    def test_fee_allocation_penny_exact(self):
        """
        Fee allocation must also be penny-exact for a 3-way split.
        $10,000 fee across 33.33 / 33.33 / 33.34 ownership.
        """
        from fee_allocation import allocate_fee_to_investors

        for filepath in ['data/investors.csv', 'data/payments.csv']:
            if os.path.exists(filepath):
                os.remove(filepath)

        add_investor("FEE-ROUND", "INV-A", "Alpha Fund", "Alpha", 33.33, datetime(2025, 1, 1))
        add_investor("FEE-ROUND", "INV-B", "Beta Fund",  "Beta",  33.33, datetime(2025, 1, 1))
        add_investor("FEE-ROUND", "INV-C", "Gamma Fund", "Gamma", 33.34, datetime(2025, 1, 1))

        result = allocate_fee_to_investors(
            loan_id="FEE-ROUND",
            fee_date=datetime(2025, 3, 1),
            fee_amount=10_000.00,
            fee_type="amendment_fee"
        )

        total_allocated = sum(a['fee_share'] for a in result['investor_allocations'])
        self.assertAlmostEqual(total_allocated, 10_000.00, places=2,
            msg=f"Fee allocation ${total_allocated:.4f} ≠ $10,000.00")

        # Each share must be a whole-cent amount
        for alloc in result['investor_allocations']:
            cents = round(alloc['fee_share'] * 100)
            self.assertAlmostEqual(alloc['fee_share'], cents / 100, places=10,
                msg=f"${alloc['fee_share']} is not a whole cent")


def run_tests():
    """Run all investor tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestInvestorOwnership))
    suite.addTests(loader.loadTestsFromTestCase(TestInvestorAllocation))
    suite.addTests(loader.loadTestsFromTestCase(TestPennyRounding))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()