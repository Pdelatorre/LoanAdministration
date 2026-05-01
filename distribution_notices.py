"""
Distribution Notice generation — Interim and Supplemental.

Interim:      Mid-period wire; documents cash going out before the month-end
              statement. The period-end statement will incorporate this item
              at close.

Supplemental: Post-statement event; documents activity after a period is closed
              and statements have already been issued. References the original
              statement by date.
"""

from datetime import datetime
from typing import Dict, List, Optional
import os
import config


def allocate_notice_to_investors(
    loan_id: str,
    effective_date: datetime,
    total_amount: float
) -> List[Dict]:
    """
    Allocate a distribution amount to investors by ownership % on the effective date.

    Returns list of dicts:
        investor_id, investor_name, investor_short_name, ownership_pct, amount
    """
    from investors import load_investors, _get_investors_at_date
    from interest_calculations import penny_round

    all_investors = load_investors(loan_id)
    owners = _get_investors_at_date(all_investors, effective_date)

    if not owners:
        raise ValueError(
            f"No investors found for loan {loan_id} as of "
            f"{effective_date.strftime('%Y-%m-%d')}"
        )

    precise = [total_amount * (inv['ownership_pct'] / 100) for inv in owners]
    rounded = penny_round(total_amount, precise)

    return [
        {
            'investor_id':         inv['investor_id'],
            'investor_name':       inv['investor_name'],
            'investor_short_name': inv['investor_short_name'],
            'ownership_pct':       inv['ownership_pct'],
            'amount':              amt,
        }
        for inv, amt in zip(owners, rounded)
    ]


def generate_investor_notice(
    loan_name: str,
    period_number: int,
    period_start: datetime,
    period_end: datetime,
    notice_type: str,
    investor: Dict,
    effective_date: datetime,
    description: str,
    wire_ref: Optional[str] = None,
    original_statement_date: Optional[datetime] = None,
    company_name: str = None
) -> str:
    """
    Generate a formatted distribution notice for one investor.

    Args:
        notice_type:             'interim' or 'supplemental'
        investor:                Entry from allocate_notice_to_investors()
        original_statement_date: Required context for supplemental notices
    """
    if company_name is None:
        company_name = config.COMPANY_NAME

    notice_date = datetime.now()

    if notice_type == 'interim':
        type_display = 'INTERIM DISTRIBUTION NOTICE'
    else:
        type_display = 'SUPPLEMENTAL DISTRIBUTION NOTICE'

    title_line = f"│{type_display.center(61)}│"

    report = f"""
┌─────────────────────────────────────────────────────────────┐
│                    [{company_name}]                         │
{title_line}
└─────────────────────────────────────────────────────────────┘

{investor['investor_name']}

Loan: {loan_name}
Period: {period_start.strftime('%B %d, %Y')} - {period_end.strftime('%B %d, %Y')}
Notice Date: {notice_date.strftime('%B %d, %Y')}
Effective Date: {effective_date.strftime('%B %d, %Y')}

─────────────────────────────────────────────────────────────

"""

    if notice_type == 'interim':
        report += (
            "This notice confirms a distribution made outside of the regular\n"
            f"period-end statement. This amount will be reflected in the\n"
            f"Period {period_number} statement issued at period close.\n"
        )
    else:
        if original_statement_date:
            stmt_str = original_statement_date.strftime('%B %d, %Y').upper()
        else:
            stmt_str = period_end.strftime('%B %d, %Y').upper()
        report += (
            f"SUPPLEMENT TO PERIOD {period_number} STATEMENT DATED {stmt_str}\n\n"
            "This notice documents additional activity not reflected in the\n"
            "original period statement referenced above.\n"
        )

    report += f"""
─────────────────────────────────────────────────────────────

DISTRIBUTION DETAIL

{'Description:':20}{description}
"""

    if wire_ref:
        report += f"{'Wire Reference:':20}{wire_ref}\n"

    eff_label = f"Ownership ({effective_date.strftime('%m/%d/%Y')}):"
    report += f"""
─────────────────────────────────────────────────────────────

YOUR ALLOCATION

{eff_label:45} {investor['ownership_pct']:.2f}%
{'Distribution Amount:':45} ${investor['amount']:>12,.2f}

─────────────────────────────────────────────────────────────
"""

    return report


def generate_all_investor_notices(
    loan_id: str,
    loan_name: str,
    period_number: int,
    period_start: datetime,
    period_end: datetime,
    notice_type: str,
    effective_date: datetime,
    description: str,
    total_amount: float,
    wire_ref: Optional[str] = None,
    original_statement_date: Optional[datetime] = None,
    output_dir: str = None,
    company_name: str = None
) -> List[str]:
    """
    Generate distribution notices for all investors and save to files.

    Returns list of file paths written.
    """
    if output_dir is None:
        output_dir = config.DISTRIBUTION_NOTICES_DIR
    if company_name is None:
        company_name = config.COMPANY_NAME

    os.makedirs(output_dir, exist_ok=True)

    allocations = allocate_notice_to_investors(loan_id, effective_date, total_amount)
    type_label = 'Interim' if notice_type == 'interim' else 'Supplemental'
    date_str = effective_date.strftime('%Y-%m-%d')

    filepaths = []
    for investor in allocations:
        notice = generate_investor_notice(
            loan_name=loan_name,
            period_number=period_number,
            period_start=period_start,
            period_end=period_end,
            notice_type=notice_type,
            investor=investor,
            effective_date=effective_date,
            description=description,
            wire_ref=wire_ref,
            original_statement_date=original_statement_date,
            company_name=company_name,
        )

        filename = (
            f"{loan_name}_Period{period_number}_"
            f"{type_label}_{date_str}_{investor['investor_short_name']}.txt"
        )
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(notice)

        filepaths.append(filepath)
        print(f"✅ Generated notice: {filename}")

    return filepaths
