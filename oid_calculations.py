"""
OID (Original Issue Discount) calculations.

OID is a discount on the loan face value — borrowers receive less than face.
It is amortized to income over the loan life using day-weighted allocation.

Funding waterfall
-----------------
    Net Investor Call    = Principal - Interest Prepayment - OID
    Net Borrower Advance = Net Investor Call - Closing Expenses

    Investors do NOT fund OID (like interest prepayment, it is a call reduction).
    Closing Expenses come OUT of the investor call before wiring to borrower.
    The delta between investor call and borrower advance equals closing expenses.

OID amortization — day-weighted straight-line
----------------------------------------------
    period_oid = round(oid_amount * period_days / total_loan_days, 2)
    Last period absorbs any penny-rounding residual so the total is exact.
"""

from typing import List, Dict


def build_oid_schedule(oid_amount: float, periods: List[Dict]) -> List[float]:
    """
    Compute per-period OID amortization amounts using day-weighted allocation.

    Each period receives OID proportional to its share of total loan days.
    The last period receives the rounding residual to ensure the sum equals
    oid_amount exactly (to the penny).

    Args:
        oid_amount: Total OID to amortize (e.g. 500_000.0). Pass 0 for no OID.
        periods:    List of period dicts, each containing a 'days' key.

    Returns:
        List of floats (one per period) that sum exactly to oid_amount.
    """
    if oid_amount == 0 or not periods:
        return [0.0] * len(periods)

    total_days = sum(p['days'] for p in periods)
    oid_list: List[float] = []
    cumulative = 0.0

    for i, period in enumerate(periods):
        if i == len(periods) - 1:
            # Last period gets the residual — guarantees exact sum
            period_oid = round(oid_amount - cumulative, 2)
        else:
            period_oid = round(oid_amount * period['days'] / total_days, 2)
            cumulative += period_oid

        oid_list.append(period_oid)

    return oid_list


def compute_unamortized_oid(oid_amount: float,
                             cumulative_oid_recognized: float) -> float:
    """
    Return the unamortized OID balance (contra-asset on the loan book).

    Args:
        oid_amount:                Total OID at origination.
        cumulative_oid_recognized: Sum of OID amortized through the current period.

    Returns:
        Remaining unamortized OID (contra-asset balance).
    """
    return round(oid_amount - cumulative_oid_recognized, 2)


def compute_loan_book_value(principal: float, unamortized_oid: float) -> float:
    """
    Return the net carrying (book) value of the loan.

    Book Value = Principal (face) - Unamortized OID (contra-asset)

    Args:
        principal:        Outstanding face / principal balance.
        unamortized_oid:  Remaining contra-asset OID balance.

    Returns:
        Net carrying value.
    """
    return round(principal - unamortized_oid, 2)


def compute_net_investor_call(principal: float,
                               interest_prepayment: float,
                               oid_amount: float) -> float:
    """
    Compute the net amount investors must fund at closing.

    Net Investor Call = Principal - Interest Prepayment - OID

    Args:
        principal:            Loan face amount.
        interest_prepayment:  Prepaid interest withheld from the investor call.
        oid_amount:           Total OID discount applied at closing.

    Returns:
        Net investor call amount.
    """
    return round(principal - interest_prepayment - oid_amount, 2)


def compute_net_borrower_advance(net_investor_call: float,
                                  closing_expenses: float) -> float:
    """
    Compute the net funds wired to the borrower at closing.

    Net Borrower Advance = Net Investor Call - Closing Expenses

    Closing expenses are paid from within the investor call before wiring
    the remainder to the borrower.  They are NOT an additional cash call.

    Args:
        net_investor_call:  Amount funded by investors.
        closing_expenses:   Costs (legal, admin, etc.) deducted before wire.

    Returns:
        Net amount received by the borrower.
    """
    return round(net_investor_call - closing_expenses, 2)
