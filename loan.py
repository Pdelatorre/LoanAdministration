from datetime import datetime
from typing import List, Dict
from business_days import get_us_bank_holidays, add_business_days
from loan_periods import generate_interest_periods
from interest_calculations import calculate_effective_rate, calculate_period_interest, calculate_segmented_interest


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
        period_end_convention: str = "last_business_day",
        pik_rate: float = 0.0,
        interest_prepayment: float = 0.0
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
            pik_rate: PIK rate (as decimal, e.g., 0.0250 for 2.50%)
            interest_prepayment: Prepayment amount
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
        self.pik_rate = pik_rate
        self.interest_prepayment = interest_prepayment
        
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


    def calculate_schedule(
        self,
        sofr_rates: Dict[datetime, float] = None,
        pik_elections: Dict[int, bool] = None,
        sofr_filepath: str = "data/sofr_rates.csv",
        pik_filepath: str = "data/pik_elections.csv",
        include_payment_status: bool = True,
        payments_filepath: str = "data/payments.csv",
    ) -> List[Dict]:
        """
        Calculate complete loan schedule with optional PIK.
    
        Automatically detects if this is a PIK loan (pik_rate > 0) and includes
        PIK calculations if applicable.
    
        Args:
            sofr_rates: SOFR rates dict (if None, loads from file)
            pik_elections: PIK elections dict (if None, loads from file for PIK loans)
            sofr_filepath: Path to SOFR rates CSV
            pik_filepath: Path to PIK elections CSV
    
        Returns:
            Complete schedule with all calculations
        """
        
        # Load SOFR Rates
        if sofr_rates is None:
            from sofr_rates import load_sofr_rates
            sofr_rates = load_sofr_rates(sofr_filepath)

        # Determine if PIK loan
        is_pik_loan = self.pik_rate > 0
        
        if is_pik_loan:
            if pik_elections is None:
                from pik_elections import load_pik_elections
                pik_elections = load_pik_elections(self.loan_id, pik_filepath)
                if not pik_elections:
                    # Default to no PIK if none provided
                    pik_elections = {p['period_number']: False for p in self.periods}
        else:
            # Not a PIK Loan, use standard schedule calculation
            pik_elections = {p['period_number']: False for p in self.periods}

        from payments import load_payments
        payments = load_payments(self.loan_id, payments_filepath)
        prepayments = [p for p in payments if p['payment_type'] == 'principal_prepayment']

        schedule = []
        current_principal = self.principal  # Track running principal balance
        current_prepaid_balance = self.interest_prepayment  # Track running prepaid balance
        
        for period in self.periods:
            period_num = period['period_number']
            
            # Calculate SOFR reset date
            sofr_reset_date = add_business_days(
                period['start_date'],
                -2,
                self.holidays
            )
            
            # Get SOFR rate
            if sofr_reset_date not in sofr_rates:
                raise ValueError(
                    f"SOFR rate not provided for reset date {sofr_reset_date.strftime('%Y-%m-%d')}"
                )
            
            sofr_rate = sofr_rates[sofr_reset_date]
            
            # Calculate effective interest rate
            effective_rate = calculate_effective_rate(
                sofr_rate,
                self.margin,
                self.sofr_floor,
                self.sofr_ceiling
            )
            
            # Check if there are prepayments in this period
            period_prepayments = [p for p in prepayments 
                                if period['start_date'] <= p['payment_date'] <= period['end_date']]

            if period_prepayments:
                # Use segmented calculation
                interest_owed, principal_after_prepayment, segments = calculate_segmented_interest(
                    period['start_date'],
                    period['end_date'],
                    current_principal,
                    effective_rate,
                    prepayments
                )
            else:
                # Normal calculation (no prepayments)
                interest_owed = calculate_period_interest(
                    current_principal,
                    effective_rate,
                    period['days']
                )
                principal_after_prepayment = current_principal
                segments = []

            # Apply interest prepayment if applicable
            prepaid_balance_start = current_prepaid_balance

            if current_prepaid_balance > 0:
                prepaid_applied = min(current_prepaid_balance, interest_owed)
                prepaid_balance_end = current_prepaid_balance - prepaid_applied
            else:
                prepaid_applied = 0.0
                prepaid_balance_end = 0.0

            current_prepaid_balance = prepaid_balance_end

            # Check if PIK is elected for this period
            pik_elected = pik_elections.get(period_num, False) and prepaid_balance_start == 0
                
            if pik_elected:
                # Calculate PIK amount
                pik_amount = calculate_period_interest(
                    principal_after_prepayment,
                    self.pik_rate,
                    period['days']
                )
                    
                # Validate: PIK shouldn't exceed interest owed
                if pik_amount > interest_owed:
                    print(f"Warning: Period {period_num} - PIK amount (${pik_amount:,.2f}) "
                        f"exceeds interest owed (${interest_owed:,.2f}). "
                        f"Capping PIK at interest owed.")
                    pik_amount = interest_owed
                    
                principal_ending = principal_after_prepayment + pik_amount
            else:
                # No PIK
                pik_amount = 0.0
                principal_ending = principal_after_prepayment

                if pik_elections.get(period_num, False) and prepaid_balance_start > 0:
                    print(f"Note: Period {period_num} - PIK election ignored due to prepaid balance of ${prepaid_balance_start:,.2f}")
                
            # Calculate final cash due
            cash_due = interest_owed - prepaid_applied - pik_amount
                
            # Build schedule entry
            schedule_entry = {
                **period,  # Include all original period data
                'principal_beginning': current_principal,
                'sofr_reset_date': sofr_reset_date,
                'sofr_rate': sofr_rate,
                'effective_rate': effective_rate,
                'interest_owed': interest_owed,
                'prepaid_balance_start': prepaid_balance_start,
                'prepaid_applied': prepaid_applied,
                'prepaid_balance_end': prepaid_balance_end,
                'pik_elected': pik_elected,
                'pik_rate': self.pik_rate,
                'pik_amount': pik_amount,
                'cash_due': cash_due,
                'principal_ending': principal_ending,
                'segments': segments,
                'prepayments': period_prepayments
            }
                
            schedule.append(schedule_entry)

            # Update principal for next period
            current_principal = principal_ending
        
        # Add payment status if requested
        if include_payment_status:
            for entry in schedule:
                period_num = entry['period_number']

                period_payments = [p for p in payments
                                   if p['payment_type'] == 'interest' 
                                   and p['period_number'] == period_num]

                amount_paid = sum(p['amount'] for p in period_payments)

                tolerance = 0.01

                if amount_paid >= entry['cash_due'] - tolerance:
                    payment_status = 'Paid'
                elif amount_paid > tolerance:
                    payment_status = 'Partially Paid'
                else:
                    payment_status = 'Unpaid'

                payment_date = None
                if period_payments:
                    payment_dates = [p['payment_date'] for p in period_payments]
                    payment_date = max(payment_dates)

                days_past_due = 0
                if payment_status in ['Unpaid', 'Partially Paid']:
                    due_date = entry['payment_due_date']
                    today = datetime.now()
                    if today > due_date:
                        days_past_due = (today - due_date).days
                
                entry['amount_paid'] = amount_paid
                entry['payment_status'] = payment_status
                entry['payment_date'] = payment_date
                entry['days_past_due'] = max(0, days_past_due)

        return schedule


    def calculate_interest_schedule(self, sofr_rates: Dict[datetime, float]) -> List[Dict]:
        """Legacy method - use caclulate_shcedule() instead."""
        return self.calculate_schedule(sofr_rates=sofr_rates)


    def calculate_interest_schedule_from_file(
        self, 
        sofr_filepath: str = "data/sofr_rates.csv",
        raise_on_missing: bool = True
    )   -> List[Dict]:
        """Legacy method - use calculate_schedule() instead."""
        return self.calculate_schedule(sofr_filepath=sofr_filepath)
    

    def calculate_interest_schedule_with_pik(
        self,
        sofr_rates: Dict[datetime, float],
        pik_elections: Dict[int, bool]
        ) -> List[Dict]:
        """Legacy method - use calculate_schedule() instead."""
        return self.calculate_schedule(sofr_rates=sofr_rates, pik_elections=pik_elections)
    

    def calculate_interest_schedule_with_pik_from_file(
        self,
        sofr_filepath: str = "data/sofr_rates.csv",
        pik_filepath: str = "data/pik_elections.csv",
    ) -> List[Dict]:
        """legacy method - use calculate_schedule() instead."""
        return self.calculate_schedule(sofr_filepath=sofr_filepath, pik_filepath=pik_filepath)