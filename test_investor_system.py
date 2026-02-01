import unittest
from datetime import datetime
from loan import Loan
from investors import add_investor, get_ownership_for_period, validate_ownership, load_investors
from investor_allocation import allocate_period_to_investors, generate_investor_report_data
from payments import add_payment
from sofr_rates import load_sofr_rates
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
        add_investor("TEST-001", "INV-A", "Investor A", 40.0, datetime(2025, 1, 1))
        add_investor("TEST-001", "INV-B", "Investor B", 60.0, datetime(2025, 1, 1))
        
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
        add_investor("TEST-001", "INV-A", "Investor A", 40.0, datetime(2025, 1, 1))
        add_investor("TEST-001", "INV-B", "Investor B", 60.0, datetime(2025, 1, 1))
        
        # Ownership change on Jan 16
        add_investor("TEST-001", "INV-A", "Investor A", 35.0, datetime(2025, 1, 16))
        add_investor("TEST-001", "INV-C", "Investor C", 5.0, datetime(2025, 1, 16))
        
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
        add_investor("ALLOC-001", "INV-A", "Investor A", 40.0, datetime(2025, 1, 1))
        add_investor("ALLOC-001", "INV-B", "Investor B", 60.0, datetime(2025, 1, 1))
        
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
        add_investor("ALLOC-002", "INV-A", "Investor A", 40.0, datetime(2025, 1, 1))
        add_investor("ALLOC-002", "INV-B", "Investor B", 60.0, datetime(2025, 1, 1))
        
        # Ownership change on Jan 25
        add_investor("ALLOC-002", "INV-A", "Investor A", 30.0, datetime(2025, 1, 25))
        add_investor("ALLOC-002", "INV-C", "Investor C", 10.0, datetime(2025, 1, 25))
        
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
        add_investor("ALLOC-003", "INV-A", "Investor A", 50.0, datetime(2025, 1, 1))
        add_investor("ALLOC-003", "INV-B", "Investor B", 50.0, datetime(2025, 1, 1))
        
        # Add principal prepayment in period 2
        add_payment("ALLOC-003", datetime(2025, 2, 15), 100000.0, "principal_prepayment")
        
        # Generate schedule
        schedule = loan.calculate_schedule(sofr_rates=self.sofr_rates, include_payment_status=False)
        
        # Allocate period 2 (with prepayment)
        allocation = allocate_period_to_investors("ALLOC-003", schedule[1])
        
        # Each investor should get 50% of prepayment
        for inv in allocation['investor_allocations']:
            self.assertAlmostEqual(inv['principal_prepayment'], 50000.0, places=2)


def run_tests():
    """Run all investor tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestInvestorOwnership))
    suite.addTests(loader.loadTestsFromTestCase(TestInvestorAllocation))
    
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