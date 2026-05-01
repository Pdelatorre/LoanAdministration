from datetime import datetime, timedelta
from typing import List, Dict
import math


def penny_round(total: float, shares: List[float]) -> List[float]:
    """
    Distribute `total` across `shares` using the Largest Remainder Method so
    that every share is rounded to the nearest cent and the sum of all shares
    equals `total` exactly (to the penny).

    Algorithm
    ---------
    1. Floor every share to the penny.
    2. Sum the floored shares — the shortfall will be 0 or more cents.
    3. Rank investors by their fractional-cent remainder (largest first).
    4. Award one extra cent to each top-ranked investor until the shortfall
       is zero.

    This is the industry-standard approach used in bond/loan accounting:
    no one loses or gains more than $0.01, and the total is always exact.

    Args:
        total:  The precise total that must be distributed (e.g. interest_owed).
        shares: List of each investor's calculated (unrounded) share.
                Must sum to approximately `total`.

    Returns:
        List of penny-rounded amounts in the same order as `shares`,
        guaranteed to sum to round(total, 2).
    """
    if not shares:
        return []

    # Work in integer cents to avoid floating-point drift
    total_cents = round(total * 100)                         # e.g. 10000 for $100.00
    floored_cents = [math.floor(s * 100) for s in shares]   # floor each share to cents
    remainders = [s * 100 - fc for s, fc in zip(shares, floored_cents)]  # fractional remainders

    shortfall = total_cents - sum(floored_cents)             # always 0 or a small positive int

    # Sort indices by remainder descending; ties broken by original order (stable)
    ranked = sorted(range(len(shares)), key=lambda i: remainders[i], reverse=True)

    result_cents = floored_cents[:]
    for i in range(shortfall):
        result_cents[ranked[i]] += 1

    return [c / 100.0 for c in result_cents]


# Calculate effective interest rate with floor and ceiling
def calculate_effective_rate(
    sofr_rate: float,
    margin: float,
    floor: float = 0.0,
    ceiling: float = float('inf')
) -> float:
    """Calculates the effective interest rate applying floor and ceiling to the SOFR rate."""
    # Apply floor and ceiling to SOFR rate
    adjusted_sofr = max(floor, min(sofr_rate, ceiling))

    # Calculate effective rate, rounded to 7 decimal places (= 5 decimal places as a percentage)
    # to eliminate floating-point noise from the addition
    effective_rate = round(adjusted_sofr + margin, 7)

    return effective_rate


def calculate_period_interest(
    principal: float,
    annual_rate: float,
    days: int,
    day_count_convention: str = "actual/360"
) -> float:
    """
    Calculate interest for a period using the specified day count convention.
    
    Args:
        principal: The loan principal amount
        annual_rate: The annual interest rate as a decimal (e.g., 0.0700 for 7%)
        days: Number of days in the period
        day_count_convention: "actual/360", "actual/365", or "30/360"
    
    Returns:
        Interest amount for the period
    
    Formula for actual/360:
        Interest = Principal × Rate × (Days / 360)
    
    Example:
        # $1,000,000 loan at 7% for 30 days
        calculate_period_interest(1000000, 0.0700, 30, "actual/360")
        >>> 5833.33
    """
    if day_count_convention == "actual/360":
        interest = principal * annual_rate * (days / 360)
        return interest
    elif day_count_convention == "actual/365":
        interest = principal * annual_rate * (days / 365)
        return interest
    elif day_count_convention == "30/360":
        # 30/360 normalizes every month to 30 days regardless of actual calendar days.
        # Standard formula: Y1/M1/D1 → Y2/M2/D2
        # days_30_360 = 360*(Y2-Y1) + 30*(M2-M1) + min(D2,30) - min(D1,30)
        # Since we receive pre-computed start/end dates from the period schedule,
        # we reconstruct that count here via the ISDA 30/360 US formula.
        raise NotImplementedError(
            "30/360 day-count convention is not yet implemented correctly. "
            "This loan should use 'actual/360' or 'actual/365'. "
            "Please update the loan's day_count_convention setting."
        )
    else:
        raise ValueError(f"Unsupported day count convention: {day_count_convention}")


def calculate_segmented_interest(
    period_start: datetime,
    period_end: datetime,
    starting_principal: float,
    effective_rate: float,
    prepayments: List[Dict],
) -> tuple:
    """
    Calculate interest for a period with mid-period principal prepayments.
    
    Args:
        period_start: Period start date
        period_end: Period end date
        starting_principal: Principal at start of period
        effective_rate: Interest rate for the period
        prepayments: List of prepayment dicts with 'payment_date' and 'amount'
    
    Returns:
        (total_interest, ending_principal)
    """
    # 1. Filter and sort prepayments in this period
    period_prepayments = [p for p in prepayments 
                        if period_start <= p['payment_date'] <= period_end]
    period_prepayments.sort(key=lambda x: x['payment_date'])

    # 2. Build segments
    segments = []
    segment_details = []
    segment_num = 1
    current_principal = starting_principal

    if period_prepayments:
        # First segment: period_start to first prepayment date
        segments.append({
            'start': period_start,
            'end': period_prepayments[0]['payment_date'],
            'principal': current_principal
        })
        current_principal -= period_prepayments[0]['amount']
        
        # Middle segments (if multiple prepayments)
        for i in range(1, len(period_prepayments)):
            segments.append({
                'start': period_prepayments[i-1]['payment_date'] + timedelta(days=1),
                'end': period_prepayments[i]['payment_date'],
                'principal': current_principal
            })
            current_principal -= period_prepayments[i]['amount']
        
        # Last segment: last prepayment + 1 day to period_end
        segments.append({
            'start': period_prepayments[-1]['payment_date'] + timedelta(days=1),
            'end': period_end,
            'principal': current_principal
        })
    else:
        # No prepayments - single segment
        segments.append({
            'start': period_start,
            'end': period_end,
            'principal': starting_principal
        })

    # 3. Calculate interest for each segment and sum
    total_interest = 0
    for segment in segments:
        days = (segment['end'] - segment['start']).days + 1  # Include both start and end
        segment_interest = calculate_period_interest(
            segment['principal'],
            effective_rate,
            days
        )
        total_interest += segment_interest
    
        segment_details.append({
            'segment_num': segment_num,
            'start_date': segment['start'],
            'end_date': segment['end'],
            'days': days,
            'principal': segment['principal'],
            'interest': segment_interest
        })
        segment_num += 1

    # 4. Return total interest and ending principal
    return total_interest, current_principal, segment_details