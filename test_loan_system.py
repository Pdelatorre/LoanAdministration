"""
Unit tests for Loan Administration System
Run with: python test_loan_system.py
"""
import unittest
from datetime import datetime
from business_days import (
    get_us_bank_holidays,
    get_last_business_day_of_month,
    add_business_days,
    get_nth_weekday
)
from interest_calculations import calculate_effective_rate, calculate_period_interest
from loan_periods import generate_interest_periods


class TestBusinessDays(unittest.TestCase):
    """Test business day calculations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.holidays_2025 = get_us_bank_holidays(2025)
    
    def test_us_bank_holidays_count(self):
        """Test that we get the correct number of holidays."""
        # Should have 9 federal holidays
        self.assertEqual(len(self.holidays_2025), 10)
    
    def test_mlk_day_2025(self):
        """Test MLK Day is calculated correctly (3rd Monday of January)."""
        mlk_day = datetime(2025, 1, 20)
        self.assertIn(mlk_day, self.holidays_2025)
        self.assertEqual(mlk_day.weekday(), 0)  # Monday
    
    def test_last_business_day_regular_month(self):
        """Test last business day for a month ending on weekday."""
        # January 31, 2025 is a Friday
        last_bd = get_last_business_day_of_month(2025, 1, self.holidays_2025)
        self.assertEqual(last_bd, datetime(2025, 1, 31))
    
    def test_last_business_day_weekend(self):
        """Test last business day when month ends on weekend."""
        # August 31, 2025 is a Sunday, so should roll back to Friday Aug 29
        last_bd = get_last_business_day_of_month(2025, 8, self.holidays_2025)
        self.assertEqual(last_bd, datetime(2025, 8, 29))
    
    def test_add_business_days_forward(self):
        """Test adding business days forward."""
        # Friday Jan 31 + 2 business days = Tuesday Feb 4
        result = add_business_days(datetime(2025, 1, 31), 2, self.holidays_2025)
        self.assertEqual(result, datetime(2025, 2, 4))
    
    def test_add_business_days_backward(self):
        """Test subtracting business days."""
        # Monday Feb 3 - 2 business days = Thursday Jan 30
        result = add_business_days(datetime(2025, 2, 3), -2, self.holidays_2025)
        self.assertEqual(result, datetime(2025, 1, 30))
    
    def test_nth_weekday_third_monday(self):
        """Test finding 3rd Monday of a month."""
        # 3rd Monday of January 2025 is MLK Day (Jan 20)
        result = get_nth_weekday(2025, 1, 0, 3)
        self.assertEqual(result, datetime(2025, 1, 20))
    
    def test_nth_weekday_last_monday(self):
        """Test finding last Monday of a month."""
        # Last Monday of May 2025 is Memorial Day (May 26)
        result = get_nth_weekday(2025, 5, 0, -1)
        self.assertEqual(result, datetime(2025, 5, 26))


class TestInterestCalculations(unittest.TestCase):
    """Test interest calculation functions."""
    
    def test_calculate_effective_rate_normal(self):
        """Test effective rate calculation within bounds."""
        rate = calculate_effective_rate(0.0450, 0.0250, 0.0000, 0.0800)
        self.assertAlmostEqual(rate, 0.0700, places=4)
    
    def test_calculate_effective_rate_below_floor(self):
        """Test that floor is applied correctly."""
        rate = calculate_effective_rate(0.0050, 0.0250, 0.0100, 0.0800)
        self.assertAlmostEqual(rate, 0.0350, places=4)  # 1% floor + 2.5% margin
    
    def test_calculate_effective_rate_above_ceiling(self):
        """Test that ceiling is applied correctly."""
        rate = calculate_effective_rate(0.0900, 0.0250, 0.0000, 0.0800)
        self.assertAlmostEqual(rate, 0.1050, places=4)  # 8% ceiling + 2.5% margin
    
    def test_calculate_period_interest_30_days(self):
        """Test interest calculation for 30-day period."""
        interest = calculate_period_interest(1000000, 0.0700, 30)
        self.assertAlmostEqual(interest, 5833.33, places=2)
    
    def test_calculate_period_interest_17_days(self):
        """Test interest calculation for partial period."""
        interest = calculate_period_interest(1000000, 0.0700, 17)
        self.assertAlmostEqual(interest, 3305.56, places=2)


class TestLoanPeriods(unittest.TestCase):
    """Test loan period generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.holidays = get_us_bank_holidays(2025)
    
    def test_period_generation_mid_month_start(self):
        """Test period generation starting mid-month."""
        periods = generate_interest_periods(
            datetime(2025, 1, 15),
            datetime(2025, 3, 31),
            self.holidays
        )
        
        # Should have 3 periods
        self.assertEqual(len(periods), 3)
        
        # First period: Jan 15-31
        self.assertEqual(periods[0]['start_date'], datetime(2025, 1, 15))
        self.assertEqual(periods[0]['end_date'], datetime(2025, 1, 31))
        self.assertEqual(periods[0]['days'], 17)
        
        # Last period: Mar 1-31
        self.assertEqual(periods[2]['start_date'], datetime(2025, 3, 1))
        self.assertEqual(periods[2]['end_date'], datetime(2025, 3, 31))
    
    def test_single_period_loan(self):
        """Test loan that starts and matures in same month."""
        periods = generate_interest_periods(
            datetime(2025, 1, 15),
            datetime(2025, 1, 31),
            self.holidays
        )
        
        # Should have only 1 period
        self.assertEqual(len(periods), 1)
        self.assertEqual(periods[0]['start_date'], datetime(2025, 1, 15))
        self.assertEqual(periods[0]['end_date'], datetime(2025, 1, 31))


class TestPIKCalculations(unittest.TestCase):
    """Test PIK interest calculations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.holidays = get_us_bank_holidays(2025)
    
    def test_pik_capitalization(self):
        """Test that PIK amount is capitalized to principal."""
        from loan import Loan
        
        loan = Loan(
            loan_id="TEST-PIK",
            borrower="Test",
            principal=1000000,
            margin=0.025,
            origination_date=datetime(2025, 1, 15),
            maturity_date=datetime(2025, 3, 31),
            pik_rate=0.05
        )
        
        sofr_rates = {
            datetime(2025, 1, 13): 0.0450,
            datetime(2025, 1, 30): 0.0450,
            datetime(2025, 2, 27): 0.0450
        }
        
        pik_elections = {1: True, 2: False, 3: True}
        
        schedule = loan.calculate_schedule(sofr_rates=sofr_rates, pik_elections=pik_elections)
        
        # Period 1: PIK elected, principal should grow
        self.assertTrue(schedule[0]['pik_elected'])
        self.assertGreater(schedule[0]['principal_ending'], 1000000)
        
        # Period 2: No PIK, principal should stay flat
        self.assertFalse(schedule[1]['pik_elected'])
        self.assertEqual(schedule[1]['principal_ending'], schedule[1]['principal_beginning'])
    
    def test_pik_reduces_cash_payment(self):
        """Test that PIK amount reduces cash payment."""
        from loan import Loan
        
        loan = Loan(
            loan_id="TEST-PIK",
            borrower="Test",
            principal=1000000,
            margin=0.025,
            origination_date=datetime(2025, 1, 15),
            maturity_date=datetime(2025, 2, 28),
            pik_rate=0.05
        )
        
        sofr_rates = {
            datetime(2025, 1, 13): 0.0450,
            datetime(2025, 1, 30): 0.0450
        }
        
        # Compare PIK vs no PIK
        pik_schedule = loan.calculate_schedule(sofr_rates=sofr_rates, pik_elections={1: True})
        cash_schedule = loan.calculate_schedule(sofr_rates=sofr_rates, pik_elections={1: False})
        
        # PIK election should reduce cash payment
        self.assertLess(pik_schedule[0]['cash_due'], cash_schedule[0]['cash_due'])
        
        # Interest owed should be the same
        self.assertAlmostEqual(pik_schedule[0]['interest_owed'], cash_schedule[0]['interest_owed'], places=2)
    
    def test_no_pik_rate_means_all_cash(self):
        """Test that loan with pik_rate=0 works like regular loan."""
        from loan import Loan
        
        loan = Loan(
            loan_id="TEST-NO-PIK",
            borrower="Test",
            principal=1000000,
            margin=0.025,
            origination_date=datetime(2025, 1, 15),
            maturity_date=datetime(2025, 2, 28),
            pik_rate=0.0  # No PIK
        )
        
        sofr_rates = {
            datetime(2025, 1, 13): 0.0450,
            datetime(2025, 1, 30): 0.0450
        }
        
        schedule = loan.calculate_schedule(sofr_rates=sofr_rates)
        
        # All periods should have zero PIK
        for period in schedule:
            self.assertEqual(period['pik_amount'], 0.0)
            self.assertEqual(period['cash_due'], period['interest_owed'])
            self.assertEqual(period['principal_ending'], period['principal_beginning'])


class TestInterestPrepayment(unittest.TestCase):
    """Test interest prepayment functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.holidays = get_us_bank_holidays(2025)
        self.sofr_rates = {
            datetime(2025, 1, 13): 0.0450,
            datetime(2025, 1, 30): 0.0450,
            datetime(2025, 2, 27): 0.0450,
            datetime(2025, 3, 28): 0.0450
        }
    
    def test_prepaid_applies_to_periods(self):
        """Test that prepaid balance applies to future periods."""
        from loan import Loan
        
        loan = Loan(
            loan_id="TEST-PREPAID",
            borrower="Test",
            principal=1000000,
            margin=0.025,
            origination_date=datetime(2025, 1, 15),
            maturity_date=datetime(2025, 4, 30),
            interest_prepayment=100000.00
        )
        
        schedule = loan.calculate_schedule(sofr_rates=self.sofr_rates)
        
        # Check first period
        self.assertEqual(schedule[0]['prepaid_balance_start'], 100000.00)
        self.assertGreater(schedule[0]['prepaid_applied'], 0)
        self.assertEqual(schedule[0]['cash_due'], 0.00)
        
        # Prepaid should decrease each period
        self.assertLess(schedule[1]['prepaid_balance_start'], 100000.00)
        self.assertLess(schedule[1]['prepaid_balance_start'], schedule[0]['prepaid_balance_start'])
    
    def test_prepaid_exhaustion(self):
        """Test partial coverage when prepaid runs out."""
        from loan import Loan
        
        loan = Loan(
            loan_id="TEST-EXHAUST",
            borrower="Test",
            principal=1000000,
            margin=0.025,
            origination_date=datetime(2025, 1, 15),
            maturity_date=datetime(2025, 4, 30),
            interest_prepayment=10000.00  # Small amount
        )
        
        schedule = loan.calculate_schedule(sofr_rates=self.sofr_rates)
        
        # Find period where prepaid runs out
        exhaust_period = None
        for period in schedule:
            if period['prepaid_balance_start'] > 0 and period['prepaid_balance_end'] == 0:
                exhaust_period = period
                break
        
        # Should have partial coverage in exhaustion period
        self.assertIsNotNone(exhaust_period)
        self.assertGreater(exhaust_period['prepaid_applied'], 0)
        self.assertGreater(exhaust_period['cash_due'], 0)
        self.assertEqual(exhaust_period['interest_owed'], 
                        exhaust_period['prepaid_applied'] + exhaust_period['cash_due'])
    
    def test_prepaid_blocks_pik(self):
        """Test that PIK is blocked when prepaid exists."""
        from loan import Loan
        
        loan = Loan(
            loan_id="TEST-PIK-BLOCK",
            borrower="Test",
            principal=1000000,
            margin=0.025,
            origination_date=datetime(2025, 1, 15),
            maturity_date=datetime(2025, 4, 30),
            interest_prepayment=20000.00,
            pik_rate=0.03
        )
        
        # Try to elect PIK on all periods
        pik_elections = {1: True, 2: True, 3: True, 4: True}
        schedule = loan.calculate_schedule(sofr_rates=self.sofr_rates, pik_elections=pik_elections)
        
        # PIK should be blocked in periods with prepaid
        for period in schedule:
            if period['prepaid_balance_start'] > 0:
                self.assertFalse(period['pik_elected'], 
                               f"Period {period['period_number']} should not allow PIK with prepaid balance")
                self.assertEqual(period['pik_amount'], 0.00)
    
    def test_pik_allowed_after_prepaid_exhausted(self):
        """Test that PIK is allowed once prepaid is exhausted."""
        from loan import Loan
        
        loan = Loan(
            loan_id="TEST-PIK-AFTER",
            borrower="Test",
            principal=1000000,
            margin=0.025,
            origination_date=datetime(2025, 1, 15),
            maturity_date=datetime(2025, 4, 30),
            interest_prepayment=5000.00,  # Very small
            pik_rate=0.03
        )
        
        pik_elections = {1: True, 2: True, 3: True, 4: True}
        schedule = loan.calculate_schedule(sofr_rates=self.sofr_rates, pik_elections=pik_elections)
        
        # Find first period with no prepaid
        for period in schedule:
            if period['prepaid_balance_start'] == 0:
                self.assertTrue(period['pik_elected'], 
                              f"Period {period['period_number']} should allow PIK with no prepaid")
                self.assertGreater(period['pik_amount'], 0)
                break


class TestPrincipalPrepayments(unittest.TestCase):
    """Test principal prepayment functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.holidays = get_us_bank_holidays(2025)
        self.sofr_rates = {
            datetime(2025, 1, 13): 0.0450,
            datetime(2025, 1, 30): 0.0455,
            datetime(2025, 2, 27): 0.0455,
            datetime(2025, 3, 28): 0.0465
        }
    
    def test_mid_period_prepayment_creates_segments(self):
        """Test that mid-period prepayment creates segment breakdown."""
        from loan import Loan
        from payments import add_payment
        import os
        
        # Clean payments file
        if os.path.exists('data/payments.csv'):
            os.remove('data/payments.csv')
        
        loan = Loan(
            loan_id="PREPAY-TEST",
            borrower="Test",
            principal=1000000,
            margin=0.025,
            origination_date=datetime(2025, 1, 15),
            maturity_date=datetime(2025, 4, 30)
        )
        
        # Add prepayment
        add_payment("PREPAY-TEST", datetime(2025, 2, 15), 100000.00, "principal_prepayment")
        
        schedule = loan.calculate_schedule(sofr_rates=self.sofr_rates, include_payment_status=False)
        
        # Period 2 should have segments
        period_2 = schedule[1]
        self.assertEqual(len(period_2['segments']), 2, "Period 2 should have 2 segments")
        self.assertEqual(period_2['principal_beginning'], 1000000)
        self.assertEqual(period_2['principal_ending'], 900000)
        
        # Verify segments
        self.assertEqual(period_2['segments'][0]['principal'], 1000000)
        self.assertEqual(period_2['segments'][1]['principal'], 900000)
        
    def test_prepayment_reduces_future_interest(self):
        """Test that prepayment reduces interest on future periods."""
        from loan import Loan
        from payments import add_payment
        import os
        
        # Clean payments file
        if os.path.exists('data/payments.csv'):
            os.remove('data/payments.csv')
        
        loan = Loan(
            loan_id="FUTURE-TEST",
            borrower="Test",
            principal=1000000,
            margin=0.025,
            origination_date=datetime(2025, 1, 15),
            maturity_date=datetime(2025, 4, 30)
        )
        
        # Get schedule without prepayment
        schedule_before = loan.calculate_schedule(sofr_rates=self.sofr_rates, include_payment_status=False)
        period_3_before = schedule_before[2]['interest_owed']
        
        # Add prepayment
        add_payment("FUTURE-TEST", datetime(2025, 2, 15), 100000.00, "principal_prepayment")
        
        # Get schedule with prepayment
        schedule_after = loan.calculate_schedule(sofr_rates=self.sofr_rates, include_payment_status=False)
        period_3_after = schedule_after[2]['interest_owed']
        
        # Period 3 interest should be lower
        self.assertLess(period_3_after, period_3_before, "Period 3 interest should be reduced after prepayment")
        
    def test_multiple_prepayments_in_period(self):
        """Test handling of multiple prepayments in one period."""
        from loan import Loan
        from payments import add_payment
        import os
        
        # Clean payments file
        if os.path.exists('data/payments.csv'):
            os.remove('data/payments.csv')
        
        loan = Loan(
            loan_id="MULTI-PREPAY",
            borrower="Test",
            principal=1000000,
            margin=0.025,
            origination_date=datetime(2025, 1, 15),
            maturity_date=datetime(2025, 4, 30)
        )
        
        # Add two prepayments in Period 2
        add_payment("MULTI-PREPAY", datetime(2025, 2, 10), 50000.00, "principal_prepayment")
        add_payment("MULTI-PREPAY", datetime(2025, 2, 20), 30000.00, "principal_prepayment")
        
        schedule = loan.calculate_schedule(sofr_rates=self.sofr_rates, include_payment_status=False)
        
        # Period 2 should have 3 segments
        period_2 = schedule[1]
        self.assertEqual(len(period_2['segments']), 3, "Period 2 should have 3 segments with 2 prepayments")
        self.assertEqual(period_2['principal_ending'], 920000, "Principal should be reduced by both prepayments")


def run_tests():
    """Run all tests and print results."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestBusinessDays))
    suite.addTests(loader.loadTestsFromTestCase(TestInterestCalculations))
    suite.addTests(loader.loadTestsFromTestCase(TestLoanPeriods))
    suite.addTests(loader.loadTestsFromTestCase(TestPIKCalculations))
    suite.addTests(loader.loadTestsFromTestCase(TestInterestPrepayment))
    suite.addTests(loader.loadTestsFromTestCase(TestPrincipalPrepayments))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70)
    
    return result.wasSuccessful()




if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)