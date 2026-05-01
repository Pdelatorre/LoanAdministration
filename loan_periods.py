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
    # Track the target billing month separately from the start date.
    # With last-business-day convention the next period may start on a date
    # still in the previous calendar month (e.g. Sep 30 when Sep 29 is the
    # last business day of September), so we cannot derive the billing month
    # from current_start_date.month — we advance it independently each iteration.
    if origination_date.month == 12:
        target_year, target_month = origination_date.year + 1, 1
    else:
        target_year, target_month = origination_date.year, origination_date.month + 1

    current_start_date = first_period_end + timedelta(days=1)

    while (target_year, target_month) < (maturity_date.year, maturity_date.month):
        current_end_date = get_period_end_date(target_year, target_month, holidays, period_end_convention)

        middle_period = {
            'period_number': period_number,
            'start_date': current_start_date,
            'end_date': current_end_date,
            'payment_due_date': current_end_date,
            'days': (current_end_date - current_start_date).days + 1
        }
        periods.append(middle_period)
        period_number += 1

        # Next period starts the calendar day after this period ends
        current_start_date = current_end_date + timedelta(days=1)

        # Advance the target billing month by one
        if target_month == 12:
            target_year, target_month = target_year + 1, 1
        else:
            target_month += 1

    # Last period — end date is the last business day of the maturity month,
    # capped at maturity_date for stub/early-payoff scenarios where maturity
    # falls before that month's last business day.
    last_period_start = current_start_date  # Day after last middle period's end
    last_period_end = get_period_end_date(maturity_date.year, maturity_date.month, holidays, period_end_convention)
    if maturity_date < last_period_end:
        last_period_end = maturity_date

    last_period = {
        'period_number': period_number,
        'start_date': last_period_start,
        'end_date': last_period_end,
        'payment_due_date': last_period_end,
        'days': (last_period_end - last_period_start).days + 1
    }
    periods.append(last_period)

    return periods