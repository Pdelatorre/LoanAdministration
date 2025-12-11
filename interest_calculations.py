

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


if __name__ == "__main__":
    # Test 1: Standard 30-day period
    interest1 = calculate_period_interest(1000000, 0.0700, 30)
    print(f"Test 1: ${interest1:,.2f} (expected $5,833.33)")
    
    # Test 2: 17-day partial period (like your Jan 15-31 example)
    interest2 = calculate_period_interest(1000000, 0.0700, 17)
    print(f"Test 2: ${interest2:,.2f} (expected $3,305.56)")
    
    # Test 3: Full 31-day month
    interest3 = calculate_period_interest(1000000, 0.0700, 31)
    print(f"Test 3: ${interest3:,.2f} (expected $6,027.78)")
    
    # Test 4: Different rate and principal
    interest4 = calculate_period_interest(2500000, 0.0825, 28)
    print(f"Test 4: ${interest4:,.2f} (expected $16,041.67)")