from datetime import datetime, timedelta
from typing import List

# Helper Functions
def get_nth_weekday(year: int, month: int, weekday: int, n: int) -> datetime:
    """Returns the date of the nth occurrence of a weekday in a given month and year."""
    first_day = datetime(year, month, 1)
    first_weekday = first_day.weekday()
    days_until_weekday = (weekday - first_weekday + 7) % 7
    first_occurrence = first_day + timedelta(days=days_until_weekday)
    if n > 0:
        nth_occurrence = first_occurrence + timedelta(weeks=n-1)
        return nth_occurrence
    else: # n == -1 for last occurrence
        fifth_occurrence = first_occurrence + timedelta(weeks=4)
        # Check if the fifth occurrence is in the same month
        if fifth_occurrence.month == month:
            return fifth_occurrence
        else: # If not, return the fourth occurrence
            return first_occurrence + timedelta(weeks=3)

def get_period_end_date(year: int, month: int, holidays: List[datetime], convention: str) -> datetime:
    """Returns the period end date based on the given convention."""
    if convention == "last_business_day":
        return get_last_business_day_of_month(year, month, holidays) 
    elif convention == "calendar_month_end":
        # Last day of the month
        if month == 12:
            return datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            return datetime(year, month + 1, 1) - timedelta(days=1)
    else:
        raise ValueError("Invalid period end convention")

# Main Function
def get_us_bank_holidays(year: int) -> List[datetime]:
    """Returns a list of US bank holidays for the given year."""
    # base holidays
    holidays = [
        datetime(year, 1, 1),  # New Year's Day
        datetime(year, 6, 19), # Juneteenth
        datetime(year, 7, 4),  # Independence Day
        datetime(year, 11, 11), # Veterans Day
        datetime(year, 12, 25)  # Christmas
    ]

    # Add floating holidays
    holidays.append(get_nth_weekday(year, 1, 0, 3))   # MLK Day - 3rd Monday of January
    holidays.append(get_nth_weekday(year, 2, 0, 3))   # Presidents Day - 3rd Monday of February
    holidays.append(get_nth_weekday(year, 5, 0, -1))  # Memorial Day - Last Monday of May
    holidays.append(get_nth_weekday(year, 9, 0, 1))   # Labor Day - 1st Monday of September
    holidays.append(get_nth_weekday(year, 11, 3, 4))  # Thanksgiving - 4th Thursday of November

    # Adjust for weekends
    observed_holidays = []
    for holiday in holidays:
        if holiday.weekday() == 5:  # Saturday
            observed_holidays.append(holiday - timedelta(days=1))
        elif holiday.weekday() == 6:  # Sunday
            observed_holidays.append(holiday + timedelta(days=1))
        else:
            observed_holidays.append(holiday)
    
    return observed_holidays

# For loans with last business day of month periods
def get_last_business_day_of_month(year: int, month: int, holidays: List[datetime]) -> datetime:
    """Returns the last business day of the month, considering weekends and holidays."""
    # Get the last day of the month
    if month == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)
    
    # Iterate backwards to find the last business day
    while True:
        if last_day.weekday() < 5 and last_day not in holidays:
            return last_day
        last_day -= timedelta(days=1)


# Used to determine SOFR rate
def add_business_days(start_date: datetime, days: int, holidays: List[datetime]) -> datetime:
    """Adds or subtracts business days from a given start date, considering weekends and holidays."""
    current_date = start_date
    step = 1 if days >= 0 else -1
    days_remaining = abs(days)
    
    while days_remaining > 0:
        current_date += timedelta(days=step)
        if current_date.weekday() < 5 and current_date not in holidays:
            days_remaining -= 1
    
    return current_date




