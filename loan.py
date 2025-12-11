from datetime import datetime
from typing import List, Dict
from business_days import get_us_bank_holidays, add_business_days
from loan_periods import generate_interest_periods
from interest_calculations import calculate_effective_rate, calculate_period_interest


class Loan:
    """Represents a floating-rate loan with interest-only payments."""
    
    def __init__(
        self,
        loan_id: str,
        borrower: str,
        principal: float,
        margin: float,
        origination_date: datetime,
        maturity_date: datetime,
        sofr_floor: float = 0.0,
        sofr_ceiling: float = float('inf'),
        period_end_convention: str = "last_business_day"
    ):
        """
        Initialize a loan.
        
        Args:
            loan_id: Unique identifier for the loan
            borrower: Borrower name
            principal: Loan amount
            margin: Spread over SOFR (as decimal, e.g., 0.0250 for 2.50%)
            origination_date: When the loan starts
            maturity_date: When the loan matures
            sofr_floor: Minimum SOFR rate (default 0%)
            sofr_ceiling: Maximum SOFR rate (default unlimited)
            period_end_convention: "last_business_day" or "calendar_month_end"
        """
        self.loan_id = loan_id
        self.borrower = borrower
        self.principal = principal
        self.margin = margin
        self.origination_date = origination_date
        self.maturity_date = maturity_date
        self.sofr_floor = sofr_floor
        self.sofr_ceiling = sofr_ceiling
        self.period_end_convention = period_end_convention
        
        # Generate holidays once
        self.holidays = self._get_relevant_holidays()
        
        # Generate interest periods
        self.periods = self._generate_periods()
    

    def _get_relevant_holidays(self) -> List[datetime]:
        """Get all holidays for years covering the loan term."""
        holidays = []
        for year in range(self.origination_date.year, self.maturity_date.year + 1):
            holidays.extend(get_us_bank_holidays(year))
        return holidays
    

    def _generate_periods(self) -> List[Dict]:
        """Generate all interest periods for the loan."""
        return generate_interest_periods(
            self.origination_date,
            self.maturity_date,
            self.holidays,
            self.period_end_convention
        )
    

    def calculate_interest_schedule(self, sofr_rates: Dict[datetime, float]) -> List[Dict]:
        """Calculate interest amounts for each period based on provided SOFR rates.
        
        Args:
            sofr_rates: Dictionary mapping SOFR reset dates to SOFR rates (as decimals)"""
        schedule = []
    
        for period in self.periods:
            # Calculate SOFR reset date (2 business days before period start)
            sofr_reset_date = add_business_days(
                period['start_date'],
                -2,
                self.holidays
            )
        
            # Get the SOFR rate for this reset date
            # If not provided, we'll need to handle this - for now, raise an error
            if sofr_reset_date not in sofr_rates:
                raise ValueError(
                    f"SOFR rate not provided for reset date {sofr_reset_date.strftime('%Y-%m-%d')}"
                )
        
            sofr_rate = sofr_rates[sofr_reset_date]
        
            # Calculate effective rate (apply floor/ceiling, add margin)
            effective_rate = calculate_effective_rate(
                sofr_rate,
                self.margin,
                self.sofr_floor,
                self.sofr_ceiling
            )
        
            # Calculate interest for the period
            interest_amount = calculate_period_interest(
                self.principal,
                effective_rate,
                period['days'],
                day_count_convention="actual/360"  # Assuming actual/360 for this loan
            )
        
            # Build the schedule entry
            schedule_entry = {
                **period,  # Include all original period data
                'sofr_reset_date': sofr_reset_date,
                'sofr_rate': sofr_rate,
                'effective_rate': effective_rate,
                'interest_amount': interest_amount
            }
        
            schedule.append(schedule_entry)
    
        return schedule


    def calculate_interest_schedule_from_file(
        self, 
        sofr_filepath: str = "data/sofr_rates.csv",
        raise_on_missing: bool = True
    )   -> List[Dict]:
        """
        Calculate interest schedule using SOFR rates from CSV file.
    
        Args:
            sofr_filepath: Path to SOFR rates CSV file
            raise_on_missing: If True, raise error when rates are missing.
    
        Returns:
            List of period dicts with interest calculations
        """
        from sofr_rates import load_sofr_rates
    
        # Load all available SOFR rates
        sofr_rates = load_sofr_rates(sofr_filepath)
    
        # Check if we have all required rates
        required_dates = self.get_required_sofr_dates()
        missing_dates = [d for d in required_dates if d not in sofr_rates]
    
        if missing_dates:
            if raise_on_missing:
                missing_str = ", ".join([d.strftime('%Y-%m-%d') for d in missing_dates])
                raise ValueError(f"Missing SOFR rates for dates: {missing_str}")
            else:
                print(f"Warning: Missing rates for {len(missing_dates)} dates")
    
        # Use the existing method to do the calculation
        return self.calculate_interest_schedule(sofr_rates)
    
    def get_required_sofr_dates(self) -> List[datetime]:
        """
        Get list of all SOFR reset dates needed for this loan.
        Useful for knowing which rates you need to enter.
    
        Returns:
            List of reset dates
        """
        reset_dates = []
        for period in self.periods:
            reset_date = add_business_days(
                period['start_date'],
                -2,
                self.holidays
            )
            reset_dates.append(reset_date)
        return reset_dates
    