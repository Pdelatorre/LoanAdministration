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
        self.assertEqual(len(self.holidays_2025), 9)
    
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


def run_tests():
    """Run all tests and print results."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestBusinessDays))
    suite.addTests(loader.loadTestsFromTestCase(TestInterestCalculations))
    suite.addTests(loader.loadTestsFromTestCase(TestLoanPeriods))
    
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