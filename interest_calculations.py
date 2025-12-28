from datetime import datetime, timedelta
from typing import List, Dict

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
    
    # Calculate effective rate
    effective_rate = adjusted_sofr + margin
    
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
        interest = principal * annual_rate * (days / 360)
        return interest
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