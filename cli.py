"""
Command-line interface for Loan Administration System
"""
import argparse
from datetime import datetime
from loan import Loan
from sofr_rates import add_sofr_rate, load_sofr_rates
from loan_export import export_schedule_to_csv, export_schedule_to_text


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
        period_end_convention=args.convention
    )
    
    print(f"\n✅ Loan created: {loan.loan_id}")
    print(f"   Borrower: {loan.borrower}")
    print(f"   Principal: ${loan.principal:,.2f}")
    print(f"   Periods: {len(loan.periods)}")
    
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
    schedule = loan.calculate_interest_schedule_from_file()
    
    loan_info = {
        'loan_id': loan.loan_id,
        'borrower': loan.borrower,
        'principal': loan.principal,
        'margin': args.margin,
        'origination_date': args.origination_date,
        'maturity_date': args.maturity_date
    }
    
    # Export files
    csv_file = f"output/{loan.loan_id}_schedule.csv"
    txt_file = f"output/{loan.loan_id}_schedule.txt"
    
    export_schedule_to_csv(schedule, csv_file, loan_info)
    export_schedule_to_text(schedule, txt_file, loan_info)
    
    # Display summary
    total_interest = sum(entry['interest_amount'] for entry in schedule)
    print(f"\n💰 Interest Schedule Generated:")
    print(f"   Total Interest: ${total_interest:,.2f}")
    print(f"   Exported to:")
    print(f"   - {csv_file}")
    print(f"   - {txt_file}")


def add_rate_command(args):
    """Add a SOFR rate."""
    rate_date = datetime.strptime(args.date, '%Y-%m-%d')
    rate_value = args.rate / 100  # Convert from percentage
    
    add_sofr_rate(rate_date, rate_value)
    print(f"✅ Added SOFR rate: {args.date} = {args.rate}%")


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
    create_parser.set_defaults(func=create_loan_command)
    
    # ADD RATE command
    rate_parser = subparsers.add_parser('add-rate', help='Add a SOFR rate')
    rate_parser.add_argument('date', help='Reset date (YYYY-MM-DD)')
    rate_parser.add_argument('rate', type=float, help='SOFR rate (in %)')
    rate_parser.set_defaults(func=add_rate_command)
    
    # LIST RATES command
    list_parser = subparsers.add_parser('list-rates', help='List all SOFR rates')
    list_parser.set_defaults(func=list_rates_command)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    # Call the appropriate command function
    args.func(args)


if __name__ == '__main__':
    main()