"""
Command-line interface for Loan Administration System
"""
import argparse
from datetime import datetime
from loan import Loan
from sofr_rates import add_sofr_rate, load_sofr_rates
from loan_export import export_schedule_to_csv, export_schedule_to_text, export_segment_details_to_csv
import config


def create_loan_command(args):
    """Create a new loan and generate schedule."""
    loan = Loan(
        loan_id=args.loan_id,
        borrower=args.borrower,
        principal=args.principal,
        margin=args.margin / 100,  # Convert from percentage
        origination_date=datetime.strptime(args.origination_date, '%Y-%m-%d'),
        maturity_date=datetime.strptime(args.maturity_date, '%Y-%m-%d'),
        sofr_floor=args.floor / 100 if args.floor else 0.0,
        sofr_ceiling=args.ceiling / 100 if args.ceiling else float('inf'),
        period_end_convention=args.convention,
        pik_rate=args.pik_rate / 100 if args.pik_rate else 0.0, # Convert from percentage
        interest_prepayment=args.interest_prepayment,
        loan_name=args.loan_name
    )
    
    print(f"\n✅ Loan created: {loan.loan_id}")
    print(f"   Borrower: {loan.borrower}")
    print(f"   Principal: ${loan.principal:,.2f}")
    print(f"   Periods: {len(loan.periods)}")
    
    if loan.interest_prepayment > 0:
        print(f"   Interest Prepayment: ${loan.interest_prepayment:,.2f}")

    if loan.pik_rate > 0:
        print(f"   PIK Rate: {loan.pik_rate * 100:.2f}%")

    # Show required SOFR dates
    print(f"\n📅 Required SOFR reset dates:")
    required_dates = loan.get_required_sofr_dates()
    for date in required_dates:
        print(f"   {date.strftime('%Y-%m-%d')}")
    
    # Check which rates we have
    available_rates = load_sofr_rates()
    missing_dates = [d for d in required_dates if d not in available_rates]
    
    if missing_dates:
        print(f"\n⚠️  Missing {len(missing_dates)} SOFR rates. Add them with:")
        print(f"   python cli.py add-rate <date> <rate>")
        return
    
    # Calculate and export schedule
    schedule = loan.calculate_schedule()
    
    loan_info = {
        'loan_id': loan.loan_id,
        'borrower': loan.borrower,
        'principal': loan.principal,
        'margin': args.margin,
        'origination_date': args.origination_date,
        'maturity_date': args.maturity_date
    }
    
    if loan.pik_rate > 0:
            loan_info['pik_rate'] = args.pik_rate

    # Export files
    csv_file = f"output/{loan.loan_id}_schedule.csv"
    txt_file = f"output/{loan.loan_id}_schedule.txt"
    segment_file = f"output/{loan.loan_id}_segments.csv"
    
    export_schedule_to_csv(schedule, csv_file, loan_info)
    export_schedule_to_text(schedule, txt_file, loan_info)
    export_segment_details_to_csv(schedule, segment_file, loan_info)
    
    # Display summary
    total_interest = sum(entry['interest_owed'] for entry in schedule)
    print(f"\n💰 Interest Schedule Generated:")
    print(f"   Total Interest: ${total_interest:,.2f}")
    if loan.pik_rate > 0:
        total_pik = sum(entry['pik_amount'] for entry in schedule)
        total_cash = sum(entry['cash_due'] for entry in schedule)
        final_principal = schedule[-1]['principal_ending']
        print(f"   Total PIK Capitalized: ${total_pik:,.2f}")
        print(f"   Total Cash Payments: ${total_cash:,.2f}")
        print(f"   Final Principal: ${final_principal:,.2f}")
    print(f"   Exported to:")
    print(f"   - {csv_file}")
    print(f"   - {txt_file}")

def add_rate_command(args):
    """Add a SOFR rate."""
    rate_date = datetime.strptime(args.date, '%Y-%m-%d')
    rate_value = args.rate / 100  # Convert from percentage
    
    add_sofr_rate(rate_date, rate_value)
    print(f"✅ Added SOFR rate: {args.date} = {args.rate}%")

def add_pik_command(args):
    """Add a PIK Election."""
    from pik_elections import add_pik_election
    loan_id = args.loan_id
    period_number = args.period_number
    pik_elected = args.pik_elected.lower() == 'true' # Convert to boolean
    
    add_pik_election(loan_id, period_number, pik_elected)

    pik_status = "PIK" if pik_elected else "Cash"
    print(f"✅ Period {period_number} for Loan {loan_id} set to {pik_status}.")

def list_rates_command(args):
    """List all SOFR rates."""
    rates = load_sofr_rates()
    
    if not rates:
        print("No SOFR rates found. Add rates with:")
        print("  python cli.py add-rate <date> <rate>")
        return
    
    print(f"\n📊 Available SOFR Rates ({len(rates)} total):\n")
    print(f"{'Date':<15} {'Rate':<10}")
    print("-" * 25)
    
    for date, rate in sorted(rates.items()):
        print(f"{date.strftime('%Y-%m-%d'):<15} {rate*100:>6.3f}%")


def add_payment_command(args):
    """Record a payment via CLI."""
    from payments import add_payment
    from datetime import datetime
    
    payment_date = datetime.strptime(args.date, '%Y-%m-%d')
    
    add_payment(
        loan_id=args.loan_id,
        payment_date=payment_date,
        amount=args.amount,
        payment_type=args.type,
        period_number=args.period,
        notes=args.notes
    )

def list_payments_command(args):
    """List all payments for a loan."""
    from payments import load_payments
    
    payments = load_payments(args.loan_id)
    
    if not payments:
        print(f"No payments found for loan {args.loan_id}")
        return
    
    print(f"\n💰 Payment History for {args.loan_id}")
    print(f"{'Payment ID':<25} {'Date':<12} {'Type':<22} {'Period':<8} {'Amount':>15}")
    print("=" * 90)
    
    for p in payments:
        period = str(p['period_number']) if p['period_number'] else 'N/A'
        print(f"{p['payment_id']:<25} "
              f"{p['payment_date'].strftime('%Y-%m-%d'):<12} "
              f"{p['payment_type']:<22} "
              f"{period:<8} "
              f"${p['amount']:>14,.2f}")
    
    # Summary
    total_interest = sum(p['amount'] for p in payments if p['payment_type'] == 'interest')
    total_principal = sum(p['amount'] for p in payments if p['payment_type'] == 'principal_prepayment')
    
    print("=" * 90)
    print(f"Total Interest Paid: ${total_interest:,.2f}")
    print(f"Total Principal Prepaid: ${total_principal:,.2f}")


def add_investor_command(args):
    """Add investor via CLI."""
    from investors import add_investor
    from datetime import datetime
    
    effective_date = datetime.strptime(args.effective_date, '%Y-%m-%d')
    
    add_investor(
        loan_id=args.loan_id,
        investor_id=args.investor_id,
        investor_name=args.investor_name,
        investor_short_name=args.investor_short_name,
        ownership_pct=args.ownership_pct,
        effective_date=effective_date
    )


def list_investors_command(args):
    """List investors for a loan via CLI."""
    from investors import load_investors, validate_ownership
    from datetime import datetime
    
    target_date = datetime.strptime(args.date, '%Y-%m-%d') if args.date else datetime.now()
    
    # Validate ownership
    result = validate_ownership(args.loan_id, target_date)
    
    print(f"\n👥 Investors for {args.loan_id} as of {target_date.strftime('%Y-%m-%d')}")
    print(f"{'Investor ID':<15} {'Investor Name':<30} {'Ownership %':>12}")
    print("=" * 60)
    
    for inv in result['investors']:
        print(f"{inv['investor_id']:<15} {inv['investor_name']:<30} {inv['ownership_pct']:>11.2f}%")
    
    print("=" * 60)
    print(f"Total Ownership: {result['total_pct']:.2f}%")
    
    if not result['valid']:
        print(f"⚠️  WARNING: Ownership does not sum to 100%!")


def generate_investor_reports_command(args):
    """Generate investor reports via CLI."""
    from loan import Loan
    from investors import load_investors
    from investor_allocation import allocate_period_to_investors
    from investor_reports import generate_all_investor_statements_for_loan
    from sofr_rates import load_sofr_rates
    
    # Load loan - need to reconstruct from CSV or database
    # For now, this is a limitation - we need loan details
    print("⚠️  Note: This command requires loan to be created in same session")
    print("    Future enhancement: Store loan details in CSV for retrieval")
    
    # Placeholder - would need to load loan from storage
    print(f"\n📊 To generate reports:")
    print(f"   1. Create/load loan: LOAN-{args.loan_id}")
    print(f"   2. Generate schedule")
    print(f"   3. Call generate_all_investor_statements_for_loan()")
    print(f"\n   See test script for full example.")


def add_fee_command(args):
    """Add a fee to a loan."""
    from fees import add_fee
    from datetime import datetime
    
    fee_date = datetime.strptime(args.date, '%Y-%m-%d')
    add_fee(
        loan_id=args.loan_id,
        fee_date=fee_date,
        fee_type=args.type,
        amount=args.amount,
        cash_or_pik=args.cash_or_pik,
        period_number=args.period,
        description=args.description
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

def main():
    parser = argparse.ArgumentParser(
        description='Loan Administration System - Calculate floating-rate loan schedules',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # CREATE LOAN command
    create_parser = subparsers.add_parser('create', help='Create a loan and generate schedule')
    create_parser.add_argument('--loan-id', required=True, help='Unique loan identifier')
    create_parser.add_argument('--borrower', required=True, help='Borrower name')
    create_parser.add_argument('--principal', type=float, required=True, help='Loan amount')
    create_parser.add_argument('--margin', type=float, required=True, help='Margin over SOFR (in %)')
    create_parser.add_argument('--origination-date', required=True, help='Origination date (YYYY-MM-DD)')
    create_parser.add_argument('--maturity-date', required=True, help='Maturity date (YYYY-MM-DD)')
    create_parser.add_argument('--floor', type=float, help='SOFR floor (in %)')
    create_parser.add_argument('--ceiling', type=float, help='SOFR ceiling (in %)')
    create_parser.add_argument('--convention', default='last_business_day',
                              choices=['last_business_day', 'calendar_month_end'],
                              help='Period end convention')
    create_parser.add_argument('--pik-rate', type=float, default=0.0, 
                               help='PIK rate (in %), for PIK Loans (optional)')
    create_parser.set_defaults(func=create_loan_command)
    create_parser.add_argument('--interest-prepayment', type=float, default=0.0, help='Interest prepaid at loan close (in dollars,optional)')
    create_parser.add_argument('--loan-name', help='Display name for loan (defaults to borrower name)')

    # ADD RATE command
    rate_parser = subparsers.add_parser('add-rate', help='Add a SOFR rate')
    rate_parser.add_argument('date', help='Reset date (YYYY-MM-DD)')
    rate_parser.add_argument('rate', type=float, help='SOFR rate (in %)')
    rate_parser.set_defaults(func=add_rate_command)

    # ADD PIK ELECTION command
    pik_parser = subparsers.add_parser('add-pik', help='Add a PIK election')
    pik_parser.add_argument('loan_id', help='Loan ID')
    pik_parser.add_argument('period_number', type=int, help='Period number')
    pik_parser.add_argument('pik_elected', help='PIK elected (True/False)')
    pik_parser.set_defaults(func=add_pik_command)   
    
    # LIST RATES command
    list_parser = subparsers.add_parser('list-rates', help='List all SOFR rates')
    list_parser.set_defaults(func=list_rates_command)

    # Add payment command
    payment_parser = subparsers.add_parser('add-payment', help='Record a payment')
    payment_parser.add_argument('--loan-id', required=True, help='Loan ID')
    payment_parser.add_argument('--date', required=True, help='Payment date (YYYY-MM-DD)')
    payment_parser.add_argument('--amount', type=float, required=True, help='Payment amount')
    payment_parser.add_argument('--type', required=True, choices=['interest', 'principal_prepayment'], 
                                help='Payment type')
    payment_parser.add_argument('--period', type=int, help='Period number (for interest payments)')
    payment_parser.add_argument('--notes', default='', help='Payment notes')
    payment_parser.set_defaults(func=add_payment_command)

    # List payments command
    list_payments_parser = subparsers.add_parser('list-payments', help='List payments for a loan')
    list_payments_parser.add_argument('loan_id', help='Loan ID')
    list_payments_parser.set_defaults(func=list_payments_command)

    # Add investor
    add_investor_parser = subparsers.add_parser('add-investor', help='Add investor to loan')
    add_investor_parser.add_argument('--loan-id', required=True, help='Loan ID')
    add_investor_parser.add_argument('--investor-id', required=True, help='Unique investor identifier')
    add_investor_parser.add_argument('--investor-name', required=True, help='Investor name')
    add_investor_parser.add_argument('--investor-short-name', required=True, help='Short name for investor (for reports)')
    add_investor_parser.add_argument('--ownership-pct', type=float, required=True, help='Ownership percentage (e.g., 40.0 for 40%)')
    add_investor_parser.add_argument('--effective-date', required=True, help='Effective date (YYYY-MM-DD)')
    add_investor_parser.set_defaults(func=add_investor_command)

    # List investors
    list_investors_parser = subparsers.add_parser('list-investors', help='List investors for a loan')
    list_investors_parser.add_argument('loan_id', help='Loan ID')
    list_investors_parser.add_argument('--date', help='Show ownership as of date (YYYY-MM-DD, defaults to today)')
    list_investors_parser.set_defaults(func=list_investors_command)

    # Generate investor reports
    generate_reports_parser = subparsers.add_parser('generate-investor-reports', help='Generate investor distribution statements')
    generate_reports_parser.add_argument('--loan-id', required=True, help='Loan ID')
    generate_reports_parser.add_argument('--period', type=int, required=True, help='Period number')
    generate_reports_parser.add_argument('--company-name', default=config.COMPANY_NAME, help='Company name for header')
    generate_reports_parser.set_defaults(func=generate_investor_reports_command)

    # Add fee command
    add_fee_parser = subparsers.add_parser('add-fee', help='Add a fee to a loan')
    add_fee_parser.add_argument('--loan-id', required=True, help='Loan ID')
    add_fee_parser.add_argument('--date', required=True, help='Fee date (YYYY-MM-DD)')
    add_fee_parser.add_argument('--type', required=True, 
                            choices=['prepayment_fee', 'prepayment_interest', 
                                    'amendment_fee', 'exit_fee', 'waiver_fee',
                                    'default_interest', 'other'],
                            help='Type of fee')
    add_fee_parser.add_argument('--amount', required=True, type=float, help='Fee amount')
    add_fee_parser.add_argument('--cash-or-pik', default='cash', choices=['cash', 'pik'],
                            help='Cash or PIK fee (default: cash)')
    add_fee_parser.add_argument('--period', type=int, help='Period number')
    add_fee_parser.add_argument('--description', default='', help='Fee description')
    add_fee_parser.set_defaults(func=add_fee_command)  

    # List fees command
    list_fees_parser = subparsers.add_parser('list-fees', help='List all fees for a loan')
    list_fees_parser.add_argument('loan_id', help='Loan ID')
    list_fees_parser.set_defaults(func=list_fees_command)  

    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    # Call the appropriate command function
    args.func(args)


if __name__ == '__main__':
    main()