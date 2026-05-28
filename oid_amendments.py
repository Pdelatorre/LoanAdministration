"""
OID Amendments — persist and load amendment events that change OID amortization.

When a loan is amended in a way that affects OID — typically a maturity
extension and/or a capitalized amendment fee that adds to OID — we record one
row here.  ``calculate_schedule`` reads these rows so it can:

    * preserve pre-amendment OID recognition (do NOT retroactively re-slice
      historical periods),
    * carry the unamortized residual forward to the amendment effective date,
    * combine the residual with any new OID added in the amendment, and
    * re-amortize that combined amount over the remaining periods to the new
      maturity date.

Warrant OID uses the same segmentation but is NEVER increased at amendment
(warrants are not re-issued).  Its residual still re-amortizes over the
extended life when maturity is pushed out.

CSV: data/oid_amendments.csv
Columns:
    loan_id              — joins to loans.csv
    sequence             — 1-indexed ordinal per loan (1, 2, 3, ...)
    effective_date       — YYYY-MM-DD, the date the amended terms take effect
                           for OID accounting (typically the credit-agreement
                           effective date)
    prior_maturity_date  — maturity_date in force IMMEDIATELY BEFORE this
                           amendment (snapshot — used to compute the original
                           horizon for pre-amendment day-weighting)
    new_maturity_date    — maturity_date after this amendment
    additional_oid       — capitalized amendment fee (or other new OID) added
                           at the effective date.  Set 0 if the amendment is
                           a pure maturity extension.
    recorded_at          — wall-clock when this row was written
    recorded_by          — operator
    reason               — free-text (mirrors the amend_loan reason)
"""

import csv
import os
from datetime import datetime
from typing import List, Dict, Optional


OID_AMENDMENTS_FILE = "data/oid_amendments.csv"

OID_AMENDMENT_FIELDS = [
    "loan_id",
    "sequence",
    "effective_date",
    "prior_maturity_date",
    "new_maturity_date",
    "additional_oid",
    "recorded_at",
    "recorded_by",
    "reason",
]


def _ensure_dir(filepath: str) -> None:
    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)


def _parse_date(value: str) -> Optional[datetime]:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d")


def load_oid_amendments(loan_id: str,
                        filepath: str = OID_AMENDMENTS_FILE) -> List[Dict]:
    """
    Return all OID amendment events for ``loan_id``, sorted by effective_date.

    Date fields are parsed into datetimes; ``additional_oid`` is a float.
    Returns ``[]`` if the file does not exist or the loan has no amendments.
    """
    try:
        with open(filepath, "r", newline="") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        return []

    events: List[Dict] = []
    for row in rows:
        if row.get("loan_id") != loan_id:
            continue
        events.append({
            "loan_id":             row["loan_id"],
            "sequence":            int(row.get("sequence") or 0),
            "effective_date":      _parse_date(row.get("effective_date")),
            "prior_maturity_date": _parse_date(row.get("prior_maturity_date")),
            "new_maturity_date":   _parse_date(row.get("new_maturity_date")),
            "additional_oid":      float(row.get("additional_oid") or 0),
            "recorded_at":         row.get("recorded_at", ""),
            "recorded_by":         row.get("recorded_by", ""),
            "reason":              row.get("reason", ""),
        })

    events.sort(key=lambda e: e["effective_date"])
    return events


def record_oid_amendment(loan_id: str,
                         effective_date: datetime,
                         prior_maturity_date: datetime,
                         new_maturity_date: datetime,
                         additional_oid: float = 0.0,
                         reason: str = "",
                         recorded_by: str = "",
                         filepath: str = OID_AMENDMENTS_FILE) -> Dict:
    """
    Append a new OID amendment event.

    The caller is responsible for validating dates (we do basic sanity here:
    effective_date must lie between origination and new_maturity, and the new
    maturity must not be before the effective date).  Returns the row written.
    """
    if effective_date is None:
        raise ValueError("effective_date is required for an OID amendment.")
    if new_maturity_date is None:
        raise ValueError("new_maturity_date is required.")
    if effective_date > new_maturity_date:
        raise ValueError(
            f"effective_date ({effective_date.date()}) cannot be after "
            f"new_maturity_date ({new_maturity_date.date()})."
        )
    if additional_oid < 0:
        raise ValueError("additional_oid must be >= 0.")

    existing = load_oid_amendments(loan_id, filepath)
    next_seq = (max((e["sequence"] for e in existing), default=0)) + 1

    row = {
        "loan_id":             loan_id,
        "sequence":            str(next_seq),
        "effective_date":      effective_date.strftime("%Y-%m-%d"),
        "prior_maturity_date": prior_maturity_date.strftime("%Y-%m-%d")
                                if prior_maturity_date else "",
        "new_maturity_date":   new_maturity_date.strftime("%Y-%m-%d"),
        "additional_oid":      f"{additional_oid:.2f}",
        "recorded_at":         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "recorded_by":         recorded_by,
        "reason":              reason,
    }

    _ensure_dir(filepath)
    file_is_new = not os.path.exists(filepath) or os.path.getsize(filepath) == 0
    with open(filepath, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OID_AMENDMENT_FIELDS)
        if file_is_new:
            writer.writeheader()
        writer.writerow(row)

    return row
