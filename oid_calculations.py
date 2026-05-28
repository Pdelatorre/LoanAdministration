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

from datetime import datetime
from typing import List, Dict, Optional


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


# ─────────────────────────────────────────────────────────────────────────────
# Amendment-aware (segmented) OID amortization
# ─────────────────────────────────────────────────────────────────────────────
#
# When a loan is amended (typically a maturity extension and/or a capitalized
# amendment fee that adds new OID), the historical periods MUST keep the OID
# they were originally recognized for.  Re-running the whole loan's
# day-weighted schedule from origination → NEW maturity would retroactively
# shrink every prior period's OID — that's wrong.
#
# The segmented model below handles this:
#
#   * Periods are partitioned into segments by amendment effective_date.
#   * Each segment has its own "amortization horizon" = (segment_start_date →
#     maturity_in_force_during_that_segment).  This horizon was the schedule
#     the OID was originally being amortized against during that segment.
#   * Each period's OID = carry_in_amount * period.days / horizon_days, where
#     carry_in_amount is the sum of (residual entering the segment + any
#     new OID added at that segment's amendment).
#   * The residual at the end of a segment = carry_in - sum(periods amortized
#     in segment).  It carries forward to the next segment.
#   * The very last period of the FINAL segment absorbs penny-rounding so the
#     total recognized exactly equals (base_amount + Σ additions).
#
# Warrants use this same function with additional_key=None (no additions at
# amendment); the residual still re-amortizes over the extended life when
# maturity is pushed out, because the final segment's horizon ends at the
# new maturity.


def build_oid_schedule_with_amendments(
    periods: List[Dict],
    origination_date: datetime,
    current_maturity_date: datetime,
    base_amount: float,
    amendments: List[Dict],
    additional_key: Optional[str] = None,
) -> List[float]:
    """
    Build a per-period OID schedule honoring amendment events.

    Args:
        periods:               Full period list, origination → current maturity.
                               Each must contain ``start_date``, ``end_date``,
                               and ``days``.
        origination_date:      Loan origination date.
        current_maturity_date: Current (post-amendment) maturity date.
        base_amount:           Original OID at closing (cash OID, or warrant OID).
        amendments:            Sorted list of amendment events.  Each dict must
                               provide ``effective_date``, ``prior_maturity_date``,
                               ``new_maturity_date``, and optionally a numeric
                               value under ``additional_key``.
        additional_key:        Key inside each amendment dict that holds the
                               amount of new OID added at that effective date
                               (e.g. ``"additional_oid"`` for cash OID).  Pass
                               ``None`` to disable additions (warrant OID).

    Returns:
        List of floats, one per ``periods`` entry, summing to
        ``base_amount + Σ additions`` (to the penny).
    """
    if not periods:
        return []

    # Total amount that must be recognized across the whole life
    total_additions = 0.0
    if additional_key:
        total_additions = sum(
            float(a.get(additional_key) or 0) for a in amendments
        )
    grand_total = round(base_amount + total_additions, 2)

    if grand_total == 0:
        return [0.0] * len(periods)

    # ── Build segment definitions ────────────────────────────────────────
    # Segment 0:  origination_date → first amendment effective_date
    #             (or current_maturity_date if no amendments)
    #             horizon: maturity that was in force at origination, which
    #             equals amendments[0]["prior_maturity_date"] if any, else
    #             current_maturity_date.
    # Segment i (≥1):  amendments[i-1].effective_date → next boundary
    #                  horizon ends at amendments[i-1].new_maturity_date.

    segments: List[Dict] = []
    if amendments:
        segments.append({
            "start_date":  origination_date,
            "end_date":    amendments[0]["effective_date"],
            "horizon_end": amendments[0]["prior_maturity_date"]
                           or current_maturity_date,
        })
        for i, amd in enumerate(amendments):
            seg_start = amd["effective_date"]
            if i + 1 < len(amendments):
                seg_end = amendments[i + 1]["effective_date"]
            else:
                seg_end = current_maturity_date
            segments.append({
                "start_date":  seg_start,
                "end_date":    seg_end,
                "horizon_end": amd["new_maturity_date"] or current_maturity_date,
            })
    else:
        segments.append({
            "start_date":  origination_date,
            "end_date":    current_maturity_date,
            "horizon_end": current_maturity_date,
        })

    # ── Partition periods into segments by start_date ────────────────────
    seg_periods: List[List[int]] = [[] for _ in segments]
    for i, p in enumerate(periods):
        placed = False
        for s_idx, seg in enumerate(segments):
            if seg["start_date"] <= p["start_date"] < seg["end_date"]:
                seg_periods[s_idx].append(i)
                placed = True
                break
        if not placed:
            # Period sits on or after the final boundary — assign to last segment
            seg_periods[-1].append(i)

    # ── Walk segments computing per-period OID ───────────────────────────
    result: List[float] = [0.0] * len(periods)
    carry_in = float(base_amount)
    last_seg_idx = len(segments) - 1

    for s_idx, seg in enumerate(segments):
        # Apply addition at this segment's start (segment 0 has none)
        if s_idx > 0 and additional_key:
            addition = float(amendments[s_idx - 1].get(additional_key) or 0)
            carry_in = round(carry_in + addition, 2)

        idxs = seg_periods[s_idx]
        if not idxs:
            continue

        horizon_days = (seg["horizon_end"] - seg["start_date"]).days
        if horizon_days <= 0 or carry_in == 0:
            # Nothing meaningful to amortize this segment.  Force terminal
            # absorption if this is the last segment so the total still ties.
            if s_idx == last_seg_idx:
                last_i = idxs[-1]
                result[last_i] = round(carry_in, 2)
                carry_in = 0.0
            continue

        is_terminal = (s_idx == last_seg_idx)
        amortized_in_seg = 0.0

        for k, i in enumerate(idxs):
            is_last_period_overall = is_terminal and (k == len(idxs) - 1)
            if is_last_period_overall:
                # Absorb rounding so Σ result == grand_total exactly
                v = round(carry_in - amortized_in_seg, 2)
            else:
                v = round(carry_in * periods[i]["days"] / horizon_days, 2)
                amortized_in_seg += v
            result[i] = v

        # Residual carried into the next segment
        carry_in = round(carry_in - amortized_in_seg, 2)

    return result

