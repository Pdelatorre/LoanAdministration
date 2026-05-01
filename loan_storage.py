"""
Loan Storage — persist Loan objects to CSV files.

loans.csv         — current state of every loan (one row per loan)
loans_history.csv — append-only audit trail of every change
"""

import csv
import os
from datetime import datetime
from typing import List, Optional, Dict

from loan import Loan

LOANS_FILE = "data/loans.csv"
HISTORY_FILE = "data/loans_history.csv"

# Columns written to loans.csv
LOAN_FIELDS = [
    "loan_id",
    "loan_name",
    "borrower",
    "principal",
    "margin",
    "origination_date",
    "maturity_date",
    "sofr_floor",
    "sofr_ceiling",
    "period_end_convention",
    "pik_rate",
    "interest_prepayment",
    "oid_amount",
    "closing_expenses",
    "status",          # draft | active | closed
    "version",
    "created_at",
    "activated_at",
    "closed_at",
]

# Columns appended to loans_history.csv
HISTORY_FIELDS = LOAN_FIELDS + [
    "change_type",    # created | corrected | recreated | activated | amended | closed
    "change_reason",
    "changed_by",
    "recorded_at",
]


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_dir(filepath: str) -> None:
    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)


def _loan_to_row(loan: Loan) -> Dict:
    """Serialize a Loan object to a dict suitable for CSV writing."""
    ceiling = loan.sofr_ceiling
    ceiling_str = "" if ceiling == float("inf") else f"{ceiling:.7f}"

    return {
        "loan_id":               loan.loan_id,
        "loan_name":             loan.loan_name,
        "borrower":              loan.borrower,
        "principal":             f"{loan.principal:.2f}",
        "margin":                f"{loan.margin:.7f}",
        "origination_date":      loan.origination_date.strftime("%Y-%m-%d"),
        "maturity_date":         loan.maturity_date.strftime("%Y-%m-%d"),
        "sofr_floor":            f"{loan.sofr_floor:.7f}",
        "sofr_ceiling":          ceiling_str,
        "period_end_convention": loan.period_end_convention,
        "pik_rate":              f"{loan.pik_rate:.7f}",
        "interest_prepayment":   f"{loan.interest_prepayment:.2f}",
        "oid_amount":            f"{loan.oid_amount:.2f}",
        "closing_expenses":      f"{loan.closing_expenses:.2f}",
        "status":                getattr(loan, "status", "draft"),
        "version":               getattr(loan, "version", 1),
        "created_at":            _fmt_dt(getattr(loan, "created_at", None)),
        "activated_at":          _fmt_dt(getattr(loan, "activated_at", None)),
        "closed_at":             _fmt_dt(getattr(loan, "closed_at", None)),
    }


def _row_to_loan(row: Dict) -> Loan:
    """Deserialize a CSV row back to a Loan object."""
    ceiling_str = row.get("sofr_ceiling", "")
    ceiling = float("inf") if ceiling_str == "" else float(ceiling_str)

    loan = Loan(
        loan_id=row["loan_id"],
        loan_name=row.get("loan_name", row["borrower"]),
        borrower=row["borrower"],
        principal=float(row["principal"]),
        margin=float(row["margin"]),
        origination_date=datetime.strptime(row["origination_date"], "%Y-%m-%d"),
        maturity_date=datetime.strptime(row["maturity_date"], "%Y-%m-%d"),
        sofr_floor=float(row.get("sofr_floor", 0)),
        sofr_ceiling=ceiling,
        period_end_convention=row.get("period_end_convention", "last_business_day"),
        pik_rate=float(row.get("pik_rate", 0)),
        interest_prepayment=float(row.get("interest_prepayment", 0)),
        oid_amount=float(row.get("oid_amount") or 0),
        closing_expenses=float(row.get("closing_expenses") or 0),
    )

    loan.status = row.get("status", "draft")
    loan.version = int(row.get("version", 1))
    loan.created_at = _parse_dt(row.get("created_at"))
    loan.activated_at = _parse_dt(row.get("activated_at"))
    loan.closed_at = _parse_dt(row.get("closed_at"))

    return loan


def _fmt_dt(dt) -> str:
    if dt is None:
        return ""
    if isinstance(dt, str):
        return dt
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _parse_dt(value: str):
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _load_all_rows(filepath: str = LOANS_FILE) -> List[Dict]:
    """Return every row from loans.csv as a list of dicts."""
    try:
        with open(filepath, "r", newline="") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        return []


def _write_all_rows(rows: List[Dict], filepath: str = LOANS_FILE) -> None:
    """Overwrite loans.csv with the given rows."""
    _ensure_dir(filepath)
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOAN_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _append_history(row: Dict, filepath: str = HISTORY_FILE) -> None:
    """Append one row to loans_history.csv."""
    _ensure_dir(filepath)
    file_is_new = not os.path.exists(filepath) or os.path.getsize(filepath) == 0
    with open(filepath, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HISTORY_FIELDS)
        if file_is_new:
            writer.writeheader()
        writer.writerow(row)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def loan_exists(loan_id: str, filepath: str = LOANS_FILE) -> bool:
    """Return True if the loan_id is present in loans.csv."""
    for row in _load_all_rows(filepath):
        if row["loan_id"] == loan_id:
            return True
    return False


def list_all_loans(filepath: str = LOANS_FILE) -> List[str]:
    """Return a list of all loan IDs currently in loans.csv."""
    return [row["loan_id"] for row in _load_all_rows(filepath)]


def load_loan(loan_id: str, filepath: str = LOANS_FILE) -> Optional[Loan]:
    """Load the current state of a loan by ID. Returns None if not found."""
    for row in _load_all_rows(filepath):
        if row["loan_id"] == loan_id:
            return _row_to_loan(row)
    return None


def get_loan_status(loan_id: str, filepath: str = LOANS_FILE) -> Optional[str]:
    """Return the status string ('draft', 'active', 'closed') or None."""
    for row in _load_all_rows(filepath):
        if row["loan_id"] == loan_id:
            return row.get("status", "draft")
    return None


def get_loan_history(loan_id: str, filepath: str = HISTORY_FILE) -> List[Dict]:
    """Return all history rows for a loan, oldest first."""
    try:
        with open(filepath, "r", newline="") as f:
            rows = list(csv.DictReader(f))
        return [r for r in rows if r["loan_id"] == loan_id]
    except FileNotFoundError:
        return []


def load_loan_as_of(loan_id: str, as_of: datetime,
                    filepath: str = HISTORY_FILE) -> Optional[Loan]:
    """
    Return the loan as it appeared at or before *as_of* (uses history file).
    Falls back to the current record if no history entry qualifies.
    """
    rows = get_loan_history(loan_id, filepath)
    # Filter to rows recorded on or before as_of
    qualifying = []
    for row in rows:
        recorded = _parse_dt(row.get("recorded_at"))
        if recorded and recorded <= as_of:
            qualifying.append(row)

    if qualifying:
        # The last qualifying row is the most recent state at that time
        return _row_to_loan(qualifying[-1])

    # Fall back to current state
    return load_loan(loan_id)


# ─────────────────────────────────────────────────────────────────────────────
# Lifecycle mutators
# ─────────────────────────────────────────────────────────────────────────────

def save_loan(loan: Loan, filepath: str = LOANS_FILE,
              history_filepath: str = HISTORY_FILE) -> None:
    """
    Persist a brand-new loan as DRAFT (version 1).

    Raises ValueError if loan_id already exists.
    """
    if loan_exists(loan.loan_id, filepath):
        raise ValueError(
            f"Loan '{loan.loan_id}' already exists. "
            f"Use correct_loan() to update a draft or amend_loan() to amend an active loan."
        )

    now = datetime.now()
    loan.status = "draft"
    loan.version = 1
    loan.created_at = now
    loan.activated_at = None
    loan.closed_at = None

    row = _loan_to_row(loan)

    # Read existing rows then rewrite the whole file (ensures the header always
    # matches LOAN_FIELDS, even when new columns were added to the schema).
    existing_rows = _load_all_rows(filepath)
    _write_all_rows(existing_rows + [row], filepath)

    # Write to history
    history_row = dict(row)
    history_row["change_type"] = "created"
    history_row["change_reason"] = "Initial loan creation"
    history_row["changed_by"] = ""
    history_row["recorded_at"] = _fmt_dt(now)
    _append_history(history_row, history_filepath)

    print(f"✅ Loan saved (DRAFT): {loan.loan_id}")


def _update_loan_row(loan: Loan, change_type: str, change_reason: str,
                     changed_by: str, filepath: str = LOANS_FILE,
                     history_filepath: str = HISTORY_FILE) -> None:
    """Internal: replace the loan row in loans.csv and append to history."""
    rows = _load_all_rows(filepath)
    new_rows = []
    found = False
    for row in rows:
        if row["loan_id"] == loan.loan_id:
            new_rows.append(_loan_to_row(loan))
            found = True
        else:
            new_rows.append(row)

    if not found:
        raise ValueError(f"Loan '{loan.loan_id}' not found in {filepath}.")

    _write_all_rows(new_rows, filepath)

    now = datetime.now()
    history_row = _loan_to_row(loan)
    history_row["change_type"] = change_type
    history_row["change_reason"] = change_reason
    history_row["changed_by"] = changed_by
    history_row["recorded_at"] = _fmt_dt(now)
    _append_history(history_row, history_filepath)


def correct_loan(loan: Loan, change_reason: str = "Draft correction",
                 changed_by: str = "",
                 filepath: str = LOANS_FILE,
                 history_filepath: str = HISTORY_FILE) -> None:
    """
    Correct parameters on a DRAFT loan.  Increments version.
    Raises ValueError if loan is not in draft status.
    """
    current_status = get_loan_status(loan.loan_id, filepath)
    if current_status != "draft":
        raise ValueError(
            f"correct_loan() requires status='draft'; "
            f"loan '{loan.loan_id}' is '{current_status}'."
        )

    existing = load_loan(loan.loan_id, filepath)
    loan.status = "draft"
    loan.version = existing.version + 1
    loan.created_at = existing.created_at
    loan.activated_at = existing.activated_at
    loan.closed_at = existing.closed_at

    _update_loan_row(loan, "corrected", change_reason, changed_by,
                     filepath, history_filepath)
    print(f"✅ Loan '{loan.loan_id}' corrected (version {loan.version}).")


def recreate_draft_loan(loan: Loan, change_reason: str,
                        changed_by: str = "",
                        filepath: str = LOANS_FILE,
                        history_filepath: str = HISTORY_FILE) -> None:
    """
    Replace a draft loan from scratch — version resets to 1.
    Raises ValueError if loan is not in draft status.
    """
    current_status = get_loan_status(loan.loan_id, filepath)
    if current_status != "draft":
        raise ValueError(
            f"recreate_draft_loan() requires status='draft'; "
            f"loan '{loan.loan_id}' is '{current_status}'."
        )

    now = datetime.now()
    loan.status = "draft"
    loan.version = 1
    loan.created_at = now
    loan.activated_at = None
    loan.closed_at = None

    _update_loan_row(loan, "recreated", change_reason, changed_by,
                     filepath, history_filepath)
    print(f"✅ Loan '{loan.loan_id}' recreated from scratch (version reset to 1).")


def activate_loan(loan_id: str, changed_by: str = "",
                  filepath: str = LOANS_FILE,
                  history_filepath: str = HISTORY_FILE) -> None:
    """
    Move a loan from DRAFT → ACTIVE.
    Raises ValueError if not in draft status.
    """
    loan = load_loan(loan_id, filepath)
    if loan is None:
        raise ValueError(f"Loan '{loan_id}' not found.")
    if loan.status != "draft":
        raise ValueError(
            f"activate_loan() requires status='draft'; "
            f"loan '{loan_id}' is '{loan.status}'."
        )

    loan.status = "active"
    loan.version += 1
    loan.activated_at = datetime.now()

    _update_loan_row(loan, "activated", "Loan activated — terms now locked.",
                     changed_by, filepath, history_filepath)
    print(f"✅ Loan '{loan_id}' is now ACTIVE (version {loan.version}).")


def amend_loan(loan: Loan, change_reason: str,
               changed_by: str = "",
               filepath: str = LOANS_FILE,
               history_filepath: str = HISTORY_FILE) -> None:
    """
    Amend an ACTIVE loan with a documented reason.  Increments version.
    Raises ValueError if loan is not active.
    """
    current_status = get_loan_status(loan.loan_id, filepath)
    if current_status != "active":
        raise ValueError(
            f"amend_loan() requires status='active'; "
            f"loan '{loan.loan_id}' is '{current_status}'."
        )

    existing = load_loan(loan.loan_id, filepath)
    loan.status = "active"
    loan.version = existing.version + 1
    loan.created_at = existing.created_at
    loan.activated_at = existing.activated_at
    loan.closed_at = existing.closed_at

    _update_loan_row(loan, "amended", change_reason, changed_by,
                     filepath, history_filepath)
    print(f"✅ Loan '{loan.loan_id}' amended (version {loan.version}).")


def close_loan(loan_id: str, change_reason: str = "Loan closed",
               changed_by: str = "",
               filepath: str = LOANS_FILE,
               history_filepath: str = HISTORY_FILE) -> None:
    """
    Move a loan to CLOSED status.
    Raises ValueError if loan is already closed.
    """
    loan = load_loan(loan_id, filepath)
    if loan is None:
        raise ValueError(f"Loan '{loan_id}' not found.")
    if loan.status == "closed":
        raise ValueError(f"Loan '{loan_id}' is already closed.")

    loan.status = "closed"
    loan.version += 1
    loan.closed_at = datetime.now()

    _update_loan_row(loan, "closed", change_reason, changed_by,
                     filepath, history_filepath)
    print(f"✅ Loan '{loan_id}' is now CLOSED.")
