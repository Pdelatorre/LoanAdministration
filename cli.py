"""
Command-line interface for Loan Administration System
"""
import argparse
from datetime import datetime
from loan import Loan
from sofr_rates import add_sofr_rate, load_sofr_rates
from loan_export import export_schedule_to_csv, export_schedule_to_text, export_segment_details_to_csv
from loan_storage import (
    save_loan, load_loan, list_all_loans, loan_exists,
    correct_loan, recreate_draft_loan, activate_loan,
    amend_loan, close_loan, get_loan_status,
    get_loan_history, load_loan_as_of,
)
import config


def create_loan_command(args):
    """Create a new loan (saved as DRAFT) and generate the interest schedule."""
    origination_date = datetime.strptime(args.origination_date, '%Y-%m-%d')
    maturity_date = datetime.strptime(args.maturity_date, '%Y-%m-%d')

    loan = Loan(
        loan_id=args.loan_id,
        borrower=args.borrower,
        loan_name=args.loan_name if args.loan_name else args.borrower,
        principal=args.principal,
        margin=args.margin / 100,
        origination_date=origination_date,
        maturity_date=maturity_date,
        sofr_floor=args.floor / 100 if args.floor else 0.0,
        sofr_ceiling=args.ceiling / 100 if args.ceiling else float('inf'),
        period_end_convention=args.convention,
        pik_rate=args.pik_rate / 100 if args.pik_rate else 0.0,
        interest_prepayment=args.interest_prepayment if args.interest_prepayment else 0.0,
        oid_amount=args.oid if args.oid else 0.0,
        closing_expenses=args.expenses if args.expenses else 0.0,
        warrant_oid_amount=args.warrant_oid if getattr(args, 'warrant_oid', None) else 0.0,
    )

    # Save as draft — raises ValueError if loan_id already exists
    try:
        save_loan(loan)
    except ValueError as e:
        print(f"\nError: {e}")
        return

    print(f"\n[DRAFT] Loan saved: {loan.loan_id}")
    print(f"   Borrower : {loan.borrower}")
    print(f"   Principal: ${loan.principal:,.2f}")
    print(f"   Periods  : {len(loan.periods)}")
    print(f"   Status   : DRAFT  (terms may still be corrected freely)")

    if loan.interest_prepayment > 0:
        print(f"   Prepaid interest: ${loan.interest_prepayment:,.2f}")
    if loan.pik_rate > 0:
        print(f"   PIK Rate: {loan.pik_rate * 100:.2f}%")
    if loan.oid_amount > 0:
        from oid_calculations import compute_net_investor_call, compute_net_borrower_advance
        net_call = compute_net_investor_call(loan.principal, loan.interest_prepayment, loan.oid_amount)
        net_advance = compute_net_borrower_advance(net_call, loan.closing_expenses)
        print(f"   OID Amount      : ${loan.oid_amount:,.2f}")
        if loan.closing_expenses > 0:
            print(f"   Closing Expenses: ${loan.closing_expenses:,.2f}")
        print(f"   Net Investor Call: ${net_call:,.2f}")
        print(f"   Net Borrower Advance: ${net_advance:,.2f}")

    print(f"\n   Next steps:")
    print(f"   1. Add investors  : python cli.py add-investor --loan-id {loan.loan_id} ...")
    print(f"   2. Add SOFR rates : python cli.py add-rate <date> <rate>")
    print(f"   3. Activate       : python cli.py activate-loan --loan-id {loan.loan_id}")

    # Generate schedule if all required SOFR rates are already present
    required_dates = loan.get_required_sofr_dates()
    available_rates = load_sofr_rates()
    missing_dates = [d for d in required_dates if d not in available_rates]

    if missing_dates:
        print(f"\n   Missing {len(missing_dates)} SOFR rates — schedule not generated yet.")
        return

    schedule = loan.calculate_schedule(sofr_rates=available_rates, include_payment_status=False)
    loan_info = {
        'loan_id': loan.loan_id,
        'borrower': loan.borrower,
        'principal': loan.principal,
        'margin': args.margin,
        'origination_date': args.origination_date,
        'maturity_date': args.maturity_date,
    }
    if loan.pik_rate > 0:
        loan_info['pik_rate'] = args.pik_rate
    if loan.oid_amount > 0:
        loan_info['oid_amount'] = loan.oid_amount
        loan_info['closing_expenses'] = loan.closing_expenses
        loan_info['interest_prepayment'] = loan.interest_prepayment

    csv_file = f"output/{loan.loan_id}_schedule.csv"
    txt_file = f"output/{loan.loan_id}_schedule.txt"
    seg_file = f"output/{loan.loan_id}_segments.csv"

    export_schedule_to_csv(schedule, csv_file, loan_info)
    export_schedule_to_text(schedule, txt_file, loan_info)
    export_segment_details_to_csv(schedule, seg_file, loan_info)

    total_interest = sum(e['interest_owed'] for e in schedule)
    if loan.pik_rate > 0:
        total_pik = sum(e['pik_amount'] for e in schedule)
        total_cash = sum(e['cash_due'] for e in schedule)
        final_principal = schedule[-1]['principal_ending']
        print(f"\n   Total projected interest : ${total_interest:,.2f}")
        print(f"   Total PIK capitalized    : ${total_pik:,.2f}")
        print(f"   Total cash payments      : ${total_cash:,.2f}")
        print(f"   Final principal          : ${final_principal:,.2f}")
    else:
        print(f"\n   Total projected interest: ${total_interest:,.2f}")
    print(f"   Schedule exported to {csv_file} and {txt_file}")


def correct_loan_command(args):
    """
    Correct a DRAFT loan's parameters (pre-production fix).

    Only the fields you supply are changed; everything else keeps its
    existing value. The old values are preserved in loans_history.csv.
    """
    if not loan_exists(args.loan_id):
        print(f"\nError: Loan '{args.loan_id}' not found.")
        return

    status = get_loan_status(args.loan_id)
    if status != 'draft':
        print(f"\nError: Loan '{args.loan_id}' is '{status}', not 'draft'.")
        print(f"       Use 'amend-loan' to modify an active loan.")
        return

    existing = load_loan(args.loan_id)

    loan = Loan(
        loan_id=args.loan_id,
        borrower=args.borrower if args.borrower else existing.borrower,
        loan_name=args.loan_name if args.loan_name else existing.loan_name,
        principal=args.principal if args.principal is not None else existing.principal,
        margin=(args.margin / 100) if args.margin is not None else existing.margin,
        origination_date=(datetime.strptime(args.origination_date, '%Y-%m-%d')
                          if args.origination_date else existing.origination_date),
        maturity_date=(datetime.strptime(args.maturity_date, '%Y-%m-%d')
                       if args.maturity_date else existing.maturity_date),
        sofr_floor=((args.floor / 100) if args.floor is not None else existing.sofr_floor),
        sofr_ceiling=((args.ceiling / 100) if args.ceiling is not None else existing.sofr_ceiling),
        period_end_convention=args.convention if args.convention else existing.period_end_convention,
        pik_rate=((args.pik_rate / 100) if args.pik_rate is not None else existing.pik_rate),
        interest_prepayment=(args.interest_prepayment
                             if args.interest_prepayment is not None
                             else existing.interest_prepayment),
        oid_amount=(args.oid if args.oid is not None else existing.oid_amount),
        closing_expenses=(args.expenses if args.expenses is not None else existing.closing_expenses),
        warrant_oid_amount=(args.warrant_oid if args.warrant_oid is not None
                            else getattr(existing, 'warrant_oid_amount', 0.0)),
    )
    loan.created_at = existing.created_at

    try:
        correct_loan(loan,
                     change_reason=args.reason or 'Draft correction via CLI',
                     changed_by=args.changed_by or '')
        print(f"\n[DRAFT] Loan '{args.loan_id}' corrected (version {existing.version + 1}).")
        print(f"   Reason: {args.reason or 'Draft correction via CLI'}")
        print(f"   Previous values preserved in loans_history.csv.")
    except ValueError as e:
        print(f"\nError: {e}")


def recreate_draft_command(args):
    """
    Recreate a draft loan from scratch (fundamental parameter error).

    All existing draft values are discarded and replaced. The old record
    is preserved in loans_history.csv with change_type='recreated'.
    Version counter resets to 1.
    """
    if not loan_exists(args.loan_id):
        print(f"\nError: Loan '{args.loan_id}' not found.")
        return

    status = get_loan_status(args.loan_id)
    if status != 'draft':
        print(f"\nError: Loan '{args.loan_id}' is '{status}'. Only draft loans can be recreated.")
        return

    loan = Loan(
        loan_id=args.loan_id,
        borrower=args.borrower,
        loan_name=args.loan_name if args.loan_name else args.borrower,
        principal=args.principal,
        margin=args.margin / 100,
        origination_date=datetime.strptime(args.origination_date, '%Y-%m-%d'),
        maturity_date=datetime.strptime(args.maturity_date, '%Y-%m-%d'),
        sofr_floor=args.floor / 100 if args.floor else 0.0,
        sofr_ceiling=args.ceiling / 100 if args.ceiling else float('inf'),
        period_end_convention=args.convention,
        pik_rate=args.pik_rate / 100 if args.pik_rate else 0.0,
        interest_prepayment=args.interest_prepayment or 0.0,
        oid_amount=args.oid or 0.0,
        closing_expenses=args.expenses or 0.0,
        warrant_oid_amount=args.warrant_oid or 0.0,
    )

    try:
        recreate_draft_loan(loan,
                            change_reason=args.reason,
                            changed_by=args.changed_by or '')
        print(f"\n[DRAFT] Loan '{args.loan_id}' recreated from scratch (version reset to 1).")
        print(f"   Reason: {args.reason}")
        print(f"   Previous record preserved in loans_history.csv.")
    except ValueError as e:
        print(f"\nError: {e}")


def activate_loan_command(args):
    """
    Activate a loan (mark it as live after first period closes).

    Once active, loan terms are locked. Any subsequent changes require
    'amend-loan' with a mandatory documented reason.
    """
    if not loan_exists(args.loan_id):
        print(f"\nError: Loan '{args.loan_id}' not found.")
        return

    try:
        activate_loan(args.loan_id, changed_by=args.changed_by or '')
        print(f"\n[ACTIVE] Loan '{args.loan_id}' is now active.")
        print(f"   Terms are locked. Use 'amend-loan' to make documented changes.")
    except ValueError as e:
        print(f"\nError: {e}")


def amend_loan_command(args):
    """
    Amend an active loan's terms with mandatory documentation.

    Use this when the credit agreement is formally amended. --reason is
    required and becomes part of the permanent audit trail.
    """
    if not loan_exists(args.loan_id):
        print(f"\nError: Loan '{args.loan_id}' not found.")
        return

    status = get_loan_status(args.loan_id)
    if status != 'active':
        print(f"\nError: Loan '{args.loan_id}' has status '{status}'.")
        print(f"       amend-loan is for active loans. For drafts, use correct-loan.")
        return

    existing = load_loan(args.loan_id)

    # OID at origination is fixed for the life of the loan; the only way to
    # *add* OID after activation is via --additional-oid, which is recorded
    # as an amendment event (so historical periods keep their original OID).
    new_maturity_date = (datetime.strptime(args.maturity_date, '%Y-%m-%d')
                         if args.maturity_date else existing.maturity_date)
    maturity_changed = new_maturity_date != existing.maturity_date
    additional_oid = float(getattr(args, 'additional_oid', 0.0) or 0.0)

    effective_date = None
    if maturity_changed or additional_oid > 0:
        if not args.effective_date:
            print("\nError: --effective-date is required when --maturity-date "
                  "changes or --additional-oid > 0.")
            print("       This date drives the OID re-amortization split so "
                  "historical periods keep their original OID and only the "
                  "unamortized residual (+ any new OID) is re-amortized over "
                  "remaining life.")
            return
        try:
            effective_date = datetime.strptime(args.effective_date, '%Y-%m-%d')
        except ValueError:
            print(f"\nError: --effective-date must be YYYY-MM-DD (got '{args.effective_date}').")
            return
        if not (existing.origination_date <= effective_date <= new_maturity_date):
            print(f"\nError: --effective-date ({effective_date.date()}) must fall between "
                  f"origination ({existing.origination_date.date()}) and "
                  f"new maturity ({new_maturity_date.date()}).")
            return

    loan = Loan(
        loan_id=args.loan_id,
        borrower=args.borrower if args.borrower else existing.borrower,
        loan_name=args.loan_name if args.loan_name else existing.loan_name,
        principal=args.principal if args.principal is not None else existing.principal,
        margin=(args.margin / 100) if args.margin is not None else existing.margin,
        origination_date=(datetime.strptime(args.origination_date, '%Y-%m-%d')
                          if args.origination_date else existing.origination_date),
        maturity_date=new_maturity_date,
        sofr_floor=((args.floor / 100) if args.floor is not None else existing.sofr_floor),
        sofr_ceiling=((args.ceiling / 100) if args.ceiling is not None else existing.sofr_ceiling),
        period_end_convention=args.convention if args.convention else existing.period_end_convention,
        pik_rate=((args.pik_rate / 100) if args.pik_rate is not None else existing.pik_rate),
        interest_prepayment=(args.interest_prepayment
                             if args.interest_prepayment is not None
                             else existing.interest_prepayment),
        # IMPORTANT: oid_amount and warrant_oid_amount are NOT amendable here.
        # Additions go into oid_amendments.csv so the historical schedule is
        # preserved.  Warrants are never re-issued post-origination.
        oid_amount=existing.oid_amount,
        closing_expenses=(args.expenses if args.expenses is not None else existing.closing_expenses),
        warrant_oid_amount=getattr(existing, 'warrant_oid_amount', 0.0),
    )
    loan.created_at = existing.created_at
    loan.activated_at = existing.activated_at

    try:
        # Record the OID amendment event FIRST (it carries the snapshot of
        # prior_maturity_date needed to replay the pre-amendment schedule).
        if effective_date is not None:
            from oid_amendments import record_oid_amendment
            record_oid_amendment(
                loan_id=args.loan_id,
                effective_date=effective_date,
                prior_maturity_date=existing.maturity_date,
                new_maturity_date=new_maturity_date,
                additional_oid=additional_oid,
                reason=args.reason,
                recorded_by=args.changed_by or '',
            )

        amend_loan(loan, change_reason=args.reason, changed_by=args.changed_by or '')
        print(f"\n[ACTIVE] Loan '{args.loan_id}' amended (version {existing.version + 1}).")
        print(f"   Reason: {args.reason}")
        print(f"   Amendment recorded in loans_history.csv.")
        if effective_date is not None:
            print(f"   OID amendment event recorded in data/oid_amendments.csv:")
            print(f"     Effective date     : {effective_date.date()}")
            print(f"     Prior maturity     : {existing.maturity_date.date()}")
            print(f"     New maturity       : {new_maturity_date.date()}")
            if additional_oid > 0:
                print(f"     Additional OID     : ${additional_oid:,.2f}")
            print(f"   Pre-amendment periods retain their original OID; the "
                  f"unamortized residual{' + additional OID' if additional_oid > 0 else ''} "
                  f"will be re-amortized over the remaining periods.")
    except ValueError as e:
        print(f"\nError: {e}")


def close_loan_command(args):
    """Mark a loan as closed (fully repaid). Status becomes read-only."""
    if not loan_exists(args.loan_id):
        print(f"\nError: Loan '{args.loan_id}' not found.")
        return

    try:
        close_loan(args.loan_id,
                   change_reason=args.reason or 'Loan closed',
                   changed_by=args.changed_by or '')
        print(f"\n[CLOSED] Loan '{args.loan_id}' is now closed.")
    except ValueError as e:
        print(f"\nError: {e}")


def loan_history_command(args):
    """Display the full audit history for a loan."""
    if not loan_exists(args.loan_id):
        print(f"\nError: Loan '{args.loan_id}' not found.")
        return

    history = get_loan_history(args.loan_id)

    if not history:
        print(f"\nNo history found for '{args.loan_id}' (loans_history.csv may not exist yet).")
        return

    loan = load_loan(args.loan_id)
    print(f"\nAudit History — {args.loan_id}  ({loan.borrower})")
    print(f"Current: status={loan.status.upper()}  version={loan.version}  "
          f"principal=${loan.principal:,.2f}  margin={loan.margin * 100:.4f}%")
    print("=" * 110)
    print(f"{'Ver':<5} {'Recorded At':<22} {'Change Type':<14} {'Changed By':<15} {'Reason'}")
    print("=" * 110)

    for row in history:
        ver = row.get('version', '?')
        recorded = row.get('recorded_at', '')
        ctype = row.get('change_type', '')
        cby = row.get('changed_by', '') or 'system'
        reason = row.get('change_reason', '')
        print(f"{ver:<5} {recorded:<22} {ctype:<14} {cby:<15} {reason}")

    print("=" * 110)


def add_rate_command(args):
    """Add a SOFR rate."""
    rate_date = datetime.strptime(args.date, '%Y-%m-%d')
    rate_value = args.rate / 100  # Convert from percentage

    add_sofr_rate(rate_date, rate_value)
    print(f"Added SOFR rate: {args.date} = {args.rate}%")


def add_pik_command(args):
    """Add a PIK Election."""
    from pik_elections import add_pik_election
    pik_elected = args.pik_elected.lower() == 'true'

    add_pik_election(args.loan_id, args.period_number, pik_elected)

    pik_status = "PIK" if pik_elected else "Cash"
    print(f"Period {args.period_number} for Loan {args.loan_id} set to {pik_status}.")


def list_rates_command(args):
    """List all SOFR rates."""
    rates = load_sofr_rates()

    if not rates:
        print("No SOFR rates found. Add rates with:")
        print("  python cli.py add-rate <date> <rate>")
        return

    print(f"\nAvailable SOFR Rates ({len(rates)} total):\n")
    print(f"{'Date':<15} {'Rate':<10}")
    print("-" * 25)

    for date, rate in sorted(rates.items()):
        print(f"{date.strftime('%Y-%m-%d'):<15} {rate * 100:>8.5f}%")


def add_payment_command(args):
    """Record a payment via CLI."""
    from payments import add_payment

    payment_date = datetime.strptime(args.date, '%Y-%m-%d')

    add_payment(
        loan_id=args.loan_id,
        payment_date=payment_date,
        amount=args.amount,
        payment_type=args.type,
        period_number=args.period,
        notes=args.notes,
    )


def list_payments_command(args):
    """List all payments for a loan."""
    from payments import load_payments

    payments = load_payments(args.loan_id)

    if not payments:
        print(f"No payments found for loan {args.loan_id}")
        return

    print(f"\nPayment History for {args.loan_id}")
    print(f"{'Payment ID':<25} {'Date':<12} {'Type':<22} {'Period':<8} {'Amount':>15}")
    print("=" * 90)

    for p in payments:
        period = str(p['period_number']) if p['period_number'] else 'N/A'
        print(f"{p['payment_id']:<25} "
              f"{p['payment_date'].strftime('%Y-%m-%d'):<12} "
              f"{p['payment_type']:<22} "
              f"{period:<8} "
              f"${p['amount']:>14,.2f}")

    total_interest = sum(p['amount'] for p in payments if p['payment_type'] == 'interest')
    total_principal = sum(p['amount'] for p in payments if p['payment_type'] == 'principal_prepayment')

    print("=" * 90)
    print(f"Total Interest Paid: ${total_interest:,.2f}")
    print(f"Total Principal Prepaid: ${total_principal:,.2f}")


def add_investor_command(args):
    """Add investor via CLI."""
    from investors import add_investor

    effective_date = datetime.strptime(args.effective_date, '%Y-%m-%d')

    add_investor(
        loan_id=args.loan_id,
        investor_id=args.investor_id,
        investor_name=args.investor_name,
        investor_short_name=args.investor_short_name,
        ownership_pct=args.ownership_pct,
        effective_date=effective_date,
    )


def list_investors_command(args):
    """List investors for a loan via CLI."""
    from investors import validate_ownership

    target_date = datetime.strptime(args.date, '%Y-%m-%d') if args.date else datetime.now()

    result = validate_ownership(args.loan_id, target_date)

    print(f"\nInvestors for {args.loan_id} as of {target_date.strftime('%Y-%m-%d')}")
    print(f"{'Investor ID':<15} {'Investor Name':<30} {'Ownership %':>12}")
    print("=" * 60)

    for inv in result['investors']:
        print(f"{inv['investor_id']:<15} {inv['investor_name']:<30} {inv['ownership_pct']:>11.2f}%")

    print("=" * 60)
    print(f"Total Ownership: {result['total_pct']:.2f}%")

    if not result['valid']:
        print(f"WARNING: Ownership does not sum to 100%!")


def add_fee_command(args):
    """Add a fee to a loan."""
    from fees import add_fee

    fee_date = datetime.strptime(args.date, '%Y-%m-%d')
    add_fee(
        loan_id=args.loan_id,
        fee_date=fee_date,
        fee_type=args.type,
        amount=args.amount,
        cash_or_pik=args.cash_or_pik,
        period_number=args.period,
        description=args.description,
    )


def list_fees_command(args):
    """List all fees for a loan."""
    from fees import load_fees, get_fee_display_name

    fees = load_fees(args.loan_id)

    if not fees:
        print(f"\nNo fees found for {args.loan_id}")
    else:
        print(f"\nFees for {args.loan_id}:")
        print("=" * 100)
        print(f"{'Date':<12} | {'Type':<25} | {'Amount':>14} | {'C/P':<4} | {'Period':<6} | {'Description'}")
        print("=" * 100)
        for fee in fees:
            period_str = f"P{fee['period_number']}" if fee['period_number'] else "N/A"
            print(f"{fee['fee_date'].strftime('%Y-%m-%d'):<12} | "
                  f"{get_fee_display_name(fee['fee_type']):<25} | "
                  f"${fee['amount']:>12,.2f} | "
                  f"{fee['cash_or_pik']:>4} | "
                  f"{period_str:<6} | "
                  f"{fee['description']}")
        print("=" * 100)
        total = sum(f['amount'] for f in fees)
        print(f"{'TOTAL':<12} | {'':<25} | ${total:>12,.2f}")
        print()


def list_loans_command(args):
    """List all loans in the system with status and version."""
    all_ids = list_all_loans()
    if not all_ids:
        print("\nNo loans in system.")
        print("   Create one with: python cli.py create ...")
        return

    sofr_rates = load_sofr_rates()

    print(f"\nLoans in System ({len(all_ids)} total)\n")
    print(f"{'Loan ID':<15} {'Status':<8} {'Ver':<5} {'Borrower':<30} {'Principal':>16} {'Periods'}")
    print("=" * 95)

    for loan_id in all_ids:
        loan = load_loan(loan_id)
        if loan:
            total_periods = len(loan.periods)
            print(f"{loan.loan_id:<15} {loan.status.upper():<8} {loan.version:<5} "
                  f"{loan.borrower:<30} ${loan.principal:>14,.2f}   {total_periods}")


def _check_statement_hold(period_data):
    """
    Check whether the statement hold period has elapsed for a given period.

    Returns (allowed: bool, eligible_date: datetime) where:
      allowed       = True if today >= period_end + STATEMENT_HOLD_DAYS business days
      eligible_date = the first date statements are allowed to be issued

    If STATEMENT_HOLD_DAYS is 0 the hold is disabled and allowed is always True.
    """
    from datetime import datetime
    from business_days import add_business_days, get_us_bank_holidays

    hold_days = config.STATEMENT_HOLD_DAYS
    period_end = period_data['end_date']

    if hold_days <= 0:
        return True, period_end

    # Normalize to midnight so time components don't affect the comparison
    period_end = period_end.replace(hour=0, minute=0, second=0, microsecond=0)

    holidays = get_us_bank_holidays(period_end.year)
    if period_end.month >= 11:
        holidays += get_us_bank_holidays(period_end.year + 1)

    eligible_date = add_business_days(period_end, hold_days, holidays)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    return today >= eligible_date, eligible_date


def _build_partial_schedule(loan, sofr_rates, include_payment_status=False):
    """
    Build as much of the loan schedule as available SOFR rates allow.

    calculate_schedule() raises ValueError on the first missing SOFR rate.
    This helper figures out which periods have rates, temporarily restricts
    the loan's period list to only those periods, calls calculate_schedule()
    so it succeeds, then appends minimal skeleton entries (sofr_rate=None)
    for every remaining period so callers can still see the full period list.

    PIK elections are always loaded from file so the schedule correctly
    reflects any elections recorded via add-pik.

    include_payment_status: when True, each completed schedule entry will
        include payment_status / amount_paid / payment_date / days_past_due
        fields (used by the audit report). Skeleton entries always get
        payment_status='Projected'.
    """
    from business_days import add_business_days
    from pik_elections import load_pik_elections

    # Always load PIK elections from file
    pik_elections = load_pik_elections(loan.loan_id)

    # Partition periods into those with rates vs those without
    completed_periods = []
    skeleton_periods = []

    for period in loan.periods:
        reset_date = add_business_days(period['start_date'], -2, loan.holidays)
        if reset_date in sofr_rates:
            completed_periods.append(period)
        else:
            skeleton_periods.append({
                **period,
                'sofr_reset_date': reset_date,
                'sofr_rate': None,
                'payment_status': 'Projected',
                'amount_paid': 0.0,
                'payment_date': None,
                'days_past_due': 0,
            })

    if not completed_periods:
        return skeleton_periods

    if not skeleton_periods:
        return loan.calculate_schedule(
            sofr_rates=sofr_rates,
            pik_elections=pik_elections,
            include_payment_status=include_payment_status)

    # Some rates present, some missing — calculate only completed periods
    original_periods = loan.periods
    try:
        loan.periods = completed_periods
        completed_schedule = loan.calculate_schedule(
            sofr_rates=sofr_rates,
            pik_elections=pik_elections,
            include_payment_status=include_payment_status)
    finally:
        loan.periods = original_periods

    return completed_schedule + skeleton_periods


def check_periods_command(args):
    """Check which periods have SOFR rates and are ready for reporting."""
    if not loan_exists(args.loan_id):
        print(f"\nError: Loan '{args.loan_id}' not found.")
        print(f"   Available loans: {', '.join(list_all_loans())}")
        return

    loan = load_loan(args.loan_id)
    sofr_rates = load_sofr_rates()
    schedule = _build_partial_schedule(loan, sofr_rates)

    print(f"\nPeriod Status — {args.loan_id}  ({loan.borrower})")
    print(f"Status: {loan.status.upper()}   Version: {loan.version}   Total Periods: {len(schedule)}")
    print("\n" + "=" * 90)
    print(f"{'Period':<8} {'Start Date':<12} {'End Date':<12} {'SOFR Rate':<12} {'Status':<15}")
    print("=" * 90)

    ready_count = 0
    for i, period in enumerate(schedule, 1):
        start = period['start_date'].strftime('%Y-%m-%d')
        end = period['end_date'].strftime('%Y-%m-%d')

        if period.get('sofr_rate') is not None:
            sofr = f"{period['sofr_rate'] * 100:.5f}%"
            status_label = "Ready"
            ready_count += 1
        else:
            sofr = "Missing"
            status_label = "Waiting"

        print(f"{i:<8} {start:<12} {end:<12} {sofr:<12} {status_label:<15}")

    print("=" * 90)
    print(f"\n{ready_count} of {len(schedule)} periods ready for reporting.")

    if ready_count < len(schedule):
        print(f"\nAdd SOFR rates with: python cli.py add-rate <date> <rate>")


def generate_period_reports_command(args):
    """Generate investor reports for a specific period."""
    import os
    from investor_allocation import allocate_period_to_investors
    from investor_reports import generate_all_investor_statements_for_loan
    from investor_reports_pdf import generate_all_investor_pdfs

    if not loan_exists(args.loan_id):
        print(f"\nError: Loan '{args.loan_id}' not found.")
        return

    loan = load_loan(args.loan_id)
    sofr_rates = load_sofr_rates()
    schedule = _build_partial_schedule(loan, sofr_rates)

    if args.period > len(schedule):
        print(f"\nError: Period {args.period} does not exist (loan has {len(loan.periods)} periods).")
        return

    period_data = schedule[args.period - 1]

    if period_data.get('sofr_rate') is None:
        reset_date = period_data.get('sofr_reset_date') or period_data.get('reset_date')
        reset_str = reset_date.strftime('%Y-%m-%d') if reset_date else '(unknown)'
        print(f"\nError: Period {args.period} does not have a SOFR rate yet.")
        print(f"   Add rate for {reset_str} with:")
        print(f"   python cli.py add-rate {reset_str} <rate>")
        return

    # Statement hold check
    allowed, eligible_date = _check_statement_hold(period_data)
    if not allowed:
        hold = config.STATEMENT_HOLD_DAYS
        day_word = 'business day' if hold == 1 else 'business days'
        if args.force:
            print(f"\nWarning: Period {args.period} is within the {hold}-{day_word} statement hold "
                  f"(eligible {eligible_date.strftime('%Y-%m-%d')}). Proceeding due to --force.")
        else:
            print(f"\nHold: Period {args.period} statements are not yet eligible for issuance.")
            print(f"   Period closed : {period_data['end_date'].strftime('%Y-%m-%d')}")
            print(f"   Eligible date : {eligible_date.strftime('%Y-%m-%d')} ({hold} {day_word} after close)")
            print(f"   Use --force to override the hold.")
            return

    if loan.status == 'draft':
        print(f"\nWarning: Loan '{args.loan_id}' is still DRAFT.")
        print(f"   Run 'activate-loan' before generating final reports.")

    output_dir = os.path.join(config.INVESTOR_REPORTS_DIR)
    os.makedirs(output_dir, exist_ok=True)

    existing_reports = [f for f in os.listdir(output_dir)
                        if f.startswith(f"{loan.loan_name}_Period{args.period}_")]

    if existing_reports and not args.force:
        print(f"\nWarning: Reports already exist for Period {args.period}:")
        for r in existing_reports:
            print(f"   {r}")
        print(f"\nUse --force to overwrite.")
        return

    allocation = allocate_period_to_investors(args.loan_id, period_data)

    print(f"\nGenerating reports for Period {args.period}...")
    print(f"   Date range  : {period_data['start_date'].strftime('%Y-%m-%d')} "
          f"to {period_data['end_date'].strftime('%Y-%m-%d')}")
    print(f"   Interest    : ${period_data['interest_owed']:.2f}")
    print(f"   Loan version: {loan.version} (status: {loan.status})")

    text_files = generate_all_investor_statements_for_loan(
        loan=loan, period_data=period_data, allocation_data=allocation,
        schedule=schedule)
    pdf_files = generate_all_investor_pdfs(
        loan=loan, period_data=period_data, allocation_data=allocation,
        schedule=schedule)

    print(f"\nGenerated {len(text_files)} text reports and {len(pdf_files)} PDF reports.")
    print(f"   Text: {config.INVESTOR_REPORTS_DIR}")
    print(f"   PDF : {config.INVESTOR_REPORTS_PDF_DIR}")


def generate_all_period_reports_command(args):
    """Generate investor reports for all completed periods (batch)."""
    from investor_allocation import allocate_period_to_investors
    from investor_reports import generate_all_investor_statements_for_loan
    from investor_reports_pdf import generate_all_investor_pdfs

    if not loan_exists(args.loan_id):
        print(f"\nError: Loan '{args.loan_id}' not found.")
        return

    loan = load_loan(args.loan_id)
    sofr_rates = load_sofr_rates()
    schedule = _build_partial_schedule(loan, sofr_rates)

    periods_with_sofr = [i + 1 for i, p in enumerate(schedule)
                         if p.get('sofr_rate') is not None]

    if not periods_with_sofr:
        print(f"\nNo periods have SOFR rates yet.")
        return

    start = args.start_period
    end = args.end_period if args.end_period else max(periods_with_sofr)
    periods_to_generate = [p for p in periods_with_sofr if start <= p <= end]

    if not periods_to_generate:
        print(f"\nNo periods match criteria (start: {start}, end: {end}).")
        return

    if loan.status == 'draft':
        print(f"\nWarning: Loan '{args.loan_id}' is still DRAFT.")

    # Filter by statement hold — skip periods not yet eligible unless --force
    held_periods = []
    if not args.force:
        eligible = []
        for p in periods_to_generate:
            allowed, eligible_date = _check_statement_hold(schedule[p - 1])
            if allowed:
                eligible.append(p)
            else:
                held_periods.append((p, eligible_date))
        periods_to_generate = eligible

    if held_periods:
        hold = config.STATEMENT_HOLD_DAYS
        day_word = 'business day' if hold == 1 else 'business days'
        print(f"\nHold: {len(held_periods)} period(s) skipped — within {hold}-{day_word} statement hold:")
        for p, ed in held_periods:
            print(f"   Period {p}: eligible {ed.strftime('%Y-%m-%d')}  (use --force to override)")

    if not periods_to_generate:
        print(f"\nNo eligible periods to generate.")
        return

    print(f"\nGenerating reports for {len(periods_to_generate)} periods...")
    print(f"   Loan    : {loan.loan_name} ({args.loan_id})")
    print(f"   Status  : {loan.status.upper()}  Version: {loan.version}")
    print(f"   Periods : {', '.join(map(str, periods_to_generate))}")

    total_text = total_pdf = 0

    for period_num in periods_to_generate:
        period_data = schedule[period_num - 1]
        allocation = allocate_period_to_investors(args.loan_id, period_data)

        print(f"\n   Period {period_num}: {period_data['start_date'].strftime('%Y-%m-%d')} "
              f"to {period_data['end_date'].strftime('%Y-%m-%d')}")

        text_files = generate_all_investor_statements_for_loan(
            loan=loan, period_data=period_data, allocation_data=allocation,
            schedule=schedule)
        pdf_files = generate_all_investor_pdfs(
            loan=loan, period_data=period_data, allocation_data=allocation,
            schedule=schedule)

        total_text += len(text_files)
        total_pdf += len(pdf_files)
        print(f"      Generated {len(text_files)} text, {len(pdf_files)} PDF.")

    print(f"\nTotal: {total_text} text reports and {total_pdf} PDF reports generated.")


def generate_audit_report_command(args):
    """Generate comprehensive Excel audit report."""
    from audit_reports import generate_audit_report

    if not loan_exists(args.loan_id):
        print(f"\nError: Loan '{args.loan_id}' not found.")
        return

    loan = load_loan(args.loan_id)
    sofr_rates = load_sofr_rates()
    schedule = _build_partial_schedule(loan, sofr_rates, include_payment_status=True)

    print(f"\nGenerating audit report for {args.loan_id}...")
    print(f"   Loan status: {loan.status.upper()}  Version: {loan.version}")

    filepath = generate_audit_report(loan=loan, schedule=schedule, loan_id=args.loan_id)

    print(f"\nAudit report generated: {filepath}")


def generate_schedule_command(args):
    """Generate and export the interest schedule for all periods with SOFR rates."""
    import os

    if not loan_exists(args.loan_id):
        print(f"\nError: Loan '{args.loan_id}' not found.")
        return

    loan = load_loan(args.loan_id)
    sofr_rates = load_sofr_rates()
    schedule = _build_partial_schedule(loan, sofr_rates)

    # Only include periods that have a full calculation (sofr_rate is not None)
    completed = [p for p in schedule if p.get('sofr_rate') is not None]
    pending   = [p for p in schedule if p.get('sofr_rate') is None]

    if not completed:
        print(f"\nNo SOFR rates loaded yet — schedule cannot be calculated.")
        print(f"   Add rates with: python cli.py add-rate <date> <rate>")
        return

    loan_info = {
        'loan_id':          loan.loan_id,
        'borrower':         loan.borrower,
        'principal':        loan.principal,
        'margin':           loan.margin * 100,
        'origination_date': loan.origination_date.strftime('%Y-%m-%d'),
        'maturity_date':    loan.maturity_date.strftime('%Y-%m-%d'),
    }
    if loan.oid_amount > 0:
        loan_info['oid_amount']          = loan.oid_amount
        loan_info['closing_expenses']    = loan.closing_expenses
        loan_info['interest_prepayment'] = loan.interest_prepayment

    os.makedirs('output', exist_ok=True)
    csv_file = f"output/{loan.loan_id}_schedule.csv"
    txt_file = f"output/{loan.loan_id}_schedule.txt"

    export_schedule_to_csv(completed, csv_file, loan_info)
    export_schedule_to_text(completed, txt_file, loan_info)

    # Print terminal summary
    print(f"\nInterest Schedule — {loan.loan_id}  ({loan.borrower})")
    print(f"Status: {loan.status.upper()}   Principal: ${loan.principal:,.2f}   "
          f"Margin: {loan.margin * 100:.2f}%")
    print(f"\n{'Per':<4} {'Start':<12} {'End':<12} {'Due Date':<12} "
          f"{'SOFR':>9} {'Eff Rate':>11} {'Interest':>12} {'Prepaid':>10} "
          f"{'PIK':>8} {'Cash Due':>12} {'Prin End':>14}")
    print("=" * 124)

    for p in completed:
        pik_str = f"${p['pik_amount']:,.2f}" if p['pik_amount'] else "—"
        print(
            f"{p['period_number']:<4} "
            f"{p['start_date'].strftime('%Y-%m-%d'):<12} "
            f"{p['end_date'].strftime('%Y-%m-%d'):<12} "
            f"{p['payment_due_date'].strftime('%Y-%m-%d'):<12} "
            f"{p['sofr_rate']*100:>8.5f}% "
            f"{p['effective_rate']*100:>10.5f}% "
            f"${p['interest_owed']:>11,.2f} "
            f"${p['prepaid_applied']:>9,.2f} "
            f"{pik_str:>9} "
            f"${p['cash_due']:>11,.2f} "
            f"${p['principal_ending']:>13,.2f}"
        )

    print("=" * 124)
    total_interest = sum(p['interest_owed'] for p in completed)
    total_cash     = sum(p['cash_due']      for p in completed)
    total_pik      = sum(p['pik_amount']    for p in completed)
    print(f"{'TOTAL':<4} {'':<12} {'':<12} {'':<12} {'':<9} {'':<11} "
          f"${total_interest:>11,.2f} {'':>10} "
          f"${total_pik:>8,.2f} "
          f"${total_cash:>11,.2f}")

    if pending:
        print(f"\n   ⚠  {len(pending)} period(s) not yet calculated (SOFR missing):")
        for p in pending:
            reset_str = p['sofr_reset_date'].strftime('%Y-%m-%d') if p.get('sofr_reset_date') else '?'
            print(f"      Period {p['period_number']}: needs rate for {reset_str}")

    print(f"\n   Exported: {csv_file}")
    print(f"   Exported: {txt_file}")


def generate_investor_reports_command(args):
    """Generate investor reports for a period (alias kept for backward compatibility)."""
    # Delegate to the new implementation
    args.force = False
    generate_period_reports_command(args)


def generate_distribution_notice_command(args):
    """Generate interim or supplemental distribution notices for all investors."""
    from datetime import datetime
    from distribution_notices import generate_all_investor_notices
    from distribution_notices_pdf import generate_all_investor_notice_pdfs

    if not loan_exists(args.loan_id):
        print(f"\nError: Loan '{args.loan_id}' not found.")
        return

    loan = load_loan(args.loan_id)
    sofr_rates = load_sofr_rates()
    schedule = _build_partial_schedule(loan, sofr_rates)

    if args.period > len(schedule):
        print(f"\nError: Period {args.period} does not exist "
              f"(loan has {len(loan.periods)} periods).")
        return

    period_data = schedule[args.period - 1]

    try:
        effective_date = datetime.strptime(args.effective_date, '%Y-%m-%d')
    except ValueError:
        print(f"\nError: Invalid --effective-date '{args.effective_date}'. Use YYYY-MM-DD.")
        return

    original_statement_date = None
    if args.original_statement_date:
        try:
            original_statement_date = datetime.strptime(
                args.original_statement_date, '%Y-%m-%d'
            )
        except ValueError:
            print(f"\nError: Invalid --original-statement-date. Use YYYY-MM-DD.")
            return

    if args.notice_type == 'supplemental' and not args.original_statement_date:
        print(
            f"\nNote: No --original-statement-date provided for supplemental notice. "
            f"Defaulting to period end ({period_data['end_date'].strftime('%Y-%m-%d')})."
        )

    type_label = 'Interim' if args.notice_type == 'interim' else 'Supplemental'
    print(f"\nGenerating {type_label} Distribution Notices...")
    print(f"   Loan          : {loan.loan_name} ({args.loan_id})")
    print(f"   Period        : {args.period}  "
          f"({period_data['start_date'].strftime('%Y-%m-%d')} "
          f"to {period_data['end_date'].strftime('%Y-%m-%d')})")
    print(f"   Effective Date: {effective_date.strftime('%Y-%m-%d')}")
    print(f"   Description   : {args.description}")
    print(f"   Total Amount  : ${args.amount:,.2f}")
    if args.wire_ref:
        print(f"   Wire Ref      : {args.wire_ref}")

    text_files = generate_all_investor_notices(
        loan_id=args.loan_id,
        loan_name=loan.loan_name,
        period_number=args.period,
        period_start=period_data['start_date'],
        period_end=period_data['end_date'],
        notice_type=args.notice_type,
        effective_date=effective_date,
        description=args.description,
        total_amount=args.amount,
        wire_ref=args.wire_ref,
        original_statement_date=original_statement_date,
    )

    pdf_files = generate_all_investor_notice_pdfs(
        loan_id=args.loan_id,
        loan_name=loan.loan_name,
        period_number=args.period,
        period_start=period_data['start_date'],
        period_end=period_data['end_date'],
        notice_type=args.notice_type,
        effective_date=effective_date,
        description=args.description,
        total_amount=args.amount,
        wire_ref=args.wire_ref,
        original_statement_date=original_statement_date,
    )

    print(f"\nGenerated {len(text_files)} text and {len(pdf_files)} PDF notices.")
    print(f"   Text: {config.DISTRIBUTION_NOTICES_DIR}")
    print(f"   PDF : {config.DISTRIBUTION_NOTICES_PDF_DIR}")


def main():
    parser = argparse.ArgumentParser(
        description='Loan Administration System - Calculate floating-rate loan schedules',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # ── Loan lifecycle ────────────────────────────────────────────────────────

    # create
    p = subparsers.add_parser('create', help='Create a loan (saved as draft)')
    p.add_argument('--loan-id', required=True, help='Unique loan identifier')
    p.add_argument('--borrower', required=True, help='Borrower name')
    p.add_argument('--principal', type=float, required=True, help='Loan amount')
    p.add_argument('--margin', type=float, required=True, help='Margin over SOFR (in %%)')
    p.add_argument('--origination-date', required=True, help='Origination date (YYYY-MM-DD)')
    p.add_argument('--maturity-date', required=True, help='Maturity date (YYYY-MM-DD)')
    p.add_argument('--floor', type=float, help='SOFR floor (in %%)')
    p.add_argument('--ceiling', type=float, help='SOFR ceiling (in %%)')
    p.add_argument('--convention', default='last_business_day',
                   choices=['last_business_day', 'calendar_month_end'],
                   help='Period end convention')
    p.add_argument('--pik-rate', type=float, default=0.0, help='PIK rate (in %%)')
    p.add_argument('--interest-prepayment', type=float, default=0.0,
                   help='Interest prepaid at loan close (in dollars)')
    p.add_argument('--oid', type=float, default=0.0,
                   help='Original Issue Discount at closing (in dollars)')
    p.add_argument('--warrant-oid', type=float, default=0.0,
                   help='Warrant OID at closing (in dollars). Set at origination only; '
                        'never increased by amendments. Reported separately from cash OID.')
    p.add_argument('--expenses', type=float, default=0.0,
                   help='Closing expenses deducted from investor call before borrower wire (in dollars)')
    p.add_argument('--loan-name', help='Display name for loan (defaults to borrower name)')
    p.set_defaults(func=create_loan_command)

    # correct-loan
    p = subparsers.add_parser('correct-loan',
        help='Correct a DRAFT loan\'s parameters (pre-production, audit-logged)')
    p.add_argument('--loan-id', required=True)
    p.add_argument('--borrower')
    p.add_argument('--loan-name')
    p.add_argument('--principal', type=float)
    p.add_argument('--margin', type=float, help='Margin in %% (e.g. 2.5 for 2.5%%)')
    p.add_argument('--origination-date')
    p.add_argument('--maturity-date')
    p.add_argument('--floor', type=float)
    p.add_argument('--ceiling', type=float)
    p.add_argument('--convention', choices=['last_business_day', 'calendar_month_end'])
    p.add_argument('--pik-rate', type=float)
    p.add_argument('--interest-prepayment', type=float)
    p.add_argument('--oid', type=float, help='OID amount (in dollars)')
    p.add_argument('--warrant-oid', type=float,
                   help='Warrant OID at closing (in dollars, drafts only)')
    p.add_argument('--expenses', type=float, help='Closing expenses (in dollars)')
    p.add_argument('--reason', default='', help='Reason (stored in audit trail)')
    p.add_argument('--changed-by', default='')
    p.set_defaults(func=correct_loan_command)

    # recreate-draft
    p = subparsers.add_parser('recreate-draft',
        help='Recreate a draft loan from scratch (--reason required)')
    p.add_argument('--loan-id', required=True)
    p.add_argument('--borrower', required=True)
    p.add_argument('--principal', type=float, required=True)
    p.add_argument('--margin', type=float, required=True)
    p.add_argument('--origination-date', required=True)
    p.add_argument('--maturity-date', required=True)
    p.add_argument('--floor', type=float)
    p.add_argument('--ceiling', type=float)
    p.add_argument('--convention', default='last_business_day',
                   choices=['last_business_day', 'calendar_month_end'])
    p.add_argument('--pik-rate', type=float, default=0.0)
    p.add_argument('--interest-prepayment', type=float, default=0.0)
    p.add_argument('--oid', type=float, default=0.0, help='OID amount (in dollars)')
    p.add_argument('--warrant-oid', type=float, default=0.0,
                   help='Warrant OID at closing (in dollars)')
    p.add_argument('--expenses', type=float, default=0.0, help='Closing expenses (in dollars)')
    p.add_argument('--loan-name')
    p.add_argument('--reason', required=True, help='Reason this loan is being recreated')
    p.add_argument('--changed-by', default='')
    p.set_defaults(func=recreate_draft_command)

    # activate-loan
    p = subparsers.add_parser('activate-loan',
        help='Activate a loan (mark as live; terms will be locked)')
    p.add_argument('--loan-id', required=True)
    p.add_argument('--changed-by', default='')
    p.set_defaults(func=activate_loan_command)

    # amend-loan
    p = subparsers.add_parser('amend-loan',
        help='Amend an active loan\'s terms (--reason required, permanently logged)')
    p.add_argument('--loan-id', required=True)
    p.add_argument('--borrower')
    p.add_argument('--loan-name')
    p.add_argument('--principal', type=float)
    p.add_argument('--margin', type=float)
    p.add_argument('--origination-date')
    p.add_argument('--maturity-date')
    p.add_argument('--floor', type=float)
    p.add_argument('--ceiling', type=float)
    p.add_argument('--convention', choices=['last_business_day', 'calendar_month_end'])
    p.add_argument('--pik-rate', type=float)
    p.add_argument('--interest-prepayment', type=float)
    p.add_argument('--expenses', type=float, help='Closing expenses (in dollars)')
    # OID at origination is fixed; only ADDITIONAL OID (e.g. capitalized
    # amendment fee) can be added via amendment, and it requires an
    # --effective-date so the historical schedule is preserved.
    p.add_argument('--additional-oid', type=float, default=0.0,
        help='Capitalized OID added by this amendment (e.g. amendment fee '
             'rolled into OID). Requires --effective-date. Combined with the '
             'unamortized OID residual and re-amortized over remaining life.')
    p.add_argument('--effective-date',
        help='Amendment effective date (YYYY-MM-DD). Required when '
             '--maturity-date changes or --additional-oid > 0. Used to '
             'segment the OID schedule so pre-amendment periods keep their '
             'original OID and the residual is re-amortized over the '
             'remaining periods to the new maturity.')
    p.add_argument('--reason', required=True,
        help='Mandatory amendment reason (e.g. "Amendment No.1 - margin reduced per CA dated 2026-03-01")')
    p.add_argument('--changed-by', default='')
    p.set_defaults(func=amend_loan_command)

    # close-loan
    p = subparsers.add_parser('close-loan', help='Mark a loan as closed (fully repaid)')
    p.add_argument('--loan-id', required=True)
    p.add_argument('--reason', default='')
    p.add_argument('--changed-by', default='')
    p.set_defaults(func=close_loan_command)

    # loan-history
    p = subparsers.add_parser('loan-history', help='Display full audit history for a loan')
    p.add_argument('loan_id')
    p.set_defaults(func=loan_history_command)

    # list-loans
    p = subparsers.add_parser('list-loans', help='List all loans with status and version')
    p.set_defaults(func=list_loans_command)

    # ── SOFR rates ────────────────────────────────────────────────────────────

    # add-rate
    p = subparsers.add_parser('add-rate', help='Add a SOFR rate')
    p.add_argument('date', help='Reset date (YYYY-MM-DD)')
    p.add_argument('rate', type=float, help='SOFR rate (in %%)')
    p.set_defaults(func=add_rate_command)

    # list-rates
    p = subparsers.add_parser('list-rates', help='List all SOFR rates')
    p.set_defaults(func=list_rates_command)

    # ── PIK elections ─────────────────────────────────────────────────────────

    # add-pik
    p = subparsers.add_parser('add-pik', help='Add a PIK election')
    p.add_argument('loan_id', help='Loan ID')
    p.add_argument('period_number', type=int, help='Period number')
    p.add_argument('pik_elected', help='PIK elected (True/False)')
    p.set_defaults(func=add_pik_command)

    # ── Payments ──────────────────────────────────────────────────────────────

    # add-payment
    p = subparsers.add_parser('add-payment', help='Record a payment')
    p.add_argument('--loan-id', required=True)
    p.add_argument('--date', required=True, help='Payment date (YYYY-MM-DD)')
    p.add_argument('--amount', type=float, required=True)
    p.add_argument('--type', required=True, choices=['interest', 'principal_prepayment'])
    p.add_argument('--period', type=int, help='Period number (for interest payments)')
    p.add_argument('--notes', default='')
    p.set_defaults(func=add_payment_command)

    # list-payments
    p = subparsers.add_parser('list-payments', help='List payments for a loan')
    p.add_argument('loan_id')
    p.set_defaults(func=list_payments_command)

    # ── Investors ─────────────────────────────────────────────────────────────

    # add-investor
    p = subparsers.add_parser('add-investor', help='Add investor to loan')
    p.add_argument('--loan-id', required=True)
    p.add_argument('--investor-id', required=True)
    p.add_argument('--investor-name', required=True)
    p.add_argument('--investor-short-name', required=True, help='Short name for reports')
    p.add_argument('--ownership-pct', type=float, required=True, help='e.g. 40.0 for 40%%')
    p.add_argument('--effective-date', required=True, help='YYYY-MM-DD')
    p.set_defaults(func=add_investor_command)

    # list-investors
    p = subparsers.add_parser('list-investors', help='List investors for a loan')
    p.add_argument('loan_id')
    p.add_argument('--date', help='Show ownership as of date (YYYY-MM-DD, defaults to today)')
    p.set_defaults(func=list_investors_command)

    # ── Fees ──────────────────────────────────────────────────────────────────

    # add-fee
    p = subparsers.add_parser('add-fee', help='Add a fee to a loan')
    p.add_argument('--loan-id', required=True)
    p.add_argument('--date', required=True, help='Fee date (YYYY-MM-DD)')
    p.add_argument('--type', required=True,
                   choices=['prepayment_fee', 'prepayment_interest', 'amendment_fee',
                            'exit_fee', 'waiver_fee', 'default_interest', 'other'])
    p.add_argument('--amount', type=float, required=True)
    p.add_argument('--cash-or-pik', default='cash', choices=['cash', 'pik'])
    p.add_argument('--period', type=int)
    p.add_argument('--description', default='')
    p.set_defaults(func=add_fee_command)

    # list-fees
    p = subparsers.add_parser('list-fees', help='List all fees for a loan')
    p.add_argument('loan_id')
    p.set_defaults(func=list_fees_command)

    # ── Reports ───────────────────────────────────────────────────────────────

    # generate-schedule
    p = subparsers.add_parser('generate-schedule',
        help='Generate and export interest schedule for all periods with SOFR rates')
    p.add_argument('--loan-id', required=True)
    p.set_defaults(func=generate_schedule_command)

    # check-periods
    p = subparsers.add_parser('check-periods',
        help='Show which periods have SOFR rates and are ready for reporting')
    p.add_argument('loan_id')
    p.set_defaults(func=check_periods_command)

    # generate-period-reports
    p = subparsers.add_parser('generate-period-reports',
        help='Generate investor reports for a specific period')
    p.add_argument('--loan-id', required=True)
    p.add_argument('--period', type=int, required=True)
    p.add_argument('--force', action='store_true', help='Overwrite existing reports')
    p.set_defaults(func=generate_period_reports_command)

    # generate-all-period-reports
    p = subparsers.add_parser('generate-all-period-reports',
        help='Batch-generate reports for all periods with SOFR rates')
    p.add_argument('--loan-id', required=True)
    p.add_argument('--start-period', type=int, default=1)
    p.add_argument('--end-period', type=int)
    p.set_defaults(func=generate_all_period_reports_command)

    # generate-audit-report
    p = subparsers.add_parser('generate-audit-report',
        help='Generate comprehensive Excel audit report')
    p.add_argument('--loan-id', required=True)
    p.set_defaults(func=generate_audit_report_command)

    # generate-distribution-notice
    p = subparsers.add_parser('generate-distribution-notice',
        help='Generate interim or supplemental distribution notice for all investors')
    p.add_argument('--loan-id', required=True)
    p.add_argument('--period', type=int, required=True,
        help='Period number this notice belongs to')
    p.add_argument('--type', dest='notice_type', required=True,
        choices=['interim', 'supplemental'],
        help='"interim" for mid-period wire; "supplemental" for post-statement event')
    p.add_argument('--effective-date', required=True, metavar='YYYY-MM-DD',
        help='Date the distribution is effective / wire date')
    p.add_argument('--amount', type=float, required=True,
        help='Total distribution amount (will be allocated to investors by ownership)')
    p.add_argument('--description', required=True,
        help='Description of the distribution (e.g. "Amendment Fee — Amendment No. 1")')
    p.add_argument('--wire-ref', default=None,
        help='Optional wire reference number')
    p.add_argument('--original-statement-date', default=None, metavar='YYYY-MM-DD',
        help='For supplemental notices: date the original period statement was issued')
    p.set_defaults(func=generate_distribution_notice_command)

    # generate-investor-reports (backward-compatible alias)
    p = subparsers.add_parser('generate-investor-reports',
        help='Generate investor reports for a period (use generate-period-reports instead)')
    p.add_argument('--loan-id', required=True)
    p.add_argument('--period', type=int, required=True)
    p.add_argument('--company-name', default=config.COMPANY_NAME)
    p.set_defaults(func=generate_investor_reports_command)

    # ─────────────────────────────────────────────────────────────────────────

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    args.func(args)


if __name__ == '__main__':
    main()
