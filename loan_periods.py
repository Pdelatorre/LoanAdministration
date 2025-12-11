from datetime import datetime, timedelta
from typing import List
from business_days import get_period_end_date, get_us_bank_holidays

# Generate interest periods for loans
def generate_interest_periods(
    origination_date: datetime,
    maturity_date: datetime,
    holidays: List[datetime],
    period_end_convention: str = "last_business_day" # or "calendar_month_end"
) -> List[dict]:
    
    periods = []
    period_number = 1
    
    # First period
    first_period_end = get_period_end_date(origination_date.year, origination_date.month, holidays, period_end_convention)
    
    first_period = {
        'period_number': period_number,
        'start_date': origination_date,
        'end_date': first_period_end,
        'payment_due_date': first_period_end,
        'days': (first_period_end - origination_date).days + 1
    }
    periods.append(first_period)
    period_number += 1
    
    # Check if this is a single-period loan (origination and maturity in same month)
    if origination_date.year == maturity_date.year and origination_date.month == maturity_date.month:
    # Replace the first period with one that ends on maturity date
        periods[0] = {
            'period_number': 1,
            'start_date': origination_date,
            'end_date': maturity_date,
            'payment_due_date': maturity_date,
            'days': (maturity_date - origination_date).days + 1
        }
        return periods  # Exit early - no middle or final periods needed


    # Middle periods
    current_start_date = first_period_end + timedelta(days=1) # First day of next month
    while current_start_date < maturity_date.replace(day=1):
        current_end_date = get_period_end_date(current_start_date.year, current_start_date.month, holidays, period_end_convention)
        
        middle_period = {
            'period_number': period_number,
            'start_date': current_start_date,
            'end_date': current_end_date,
            'payment_due_date': current_end_date,
            'days': (current_end_date - current_start_date).days + 1
        }
        periods.append(middle_period)
        period_number += 1
        
        # Move to the first day of the next month
        if current_start_date.month == 12:
            current_start_date = datetime(current_start_date.year + 1, 1, 1)
        else:
            current_start_date = datetime(current_start_date.year, current_start_date.month + 1, 1)

    # Last period
    last_period_start = current_start_date # First day of final month
    
    last_period = {
        'period_number': period_number,
        'start_date': last_period_start,
        'end_date': maturity_date,
        'payment_due_date': maturity_date,
        'days': (maturity_date - last_period_start).days + 1
    }
    periods.append(last_period)

    return periods