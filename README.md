# Loan Administration System

A Python-based loan administration system for calculating interest on floating-rate, interest-only loans with SOFR-based pricing.

## Features

- **Floating Rate Calculations**: Supports 1-month Term SOFR with configurable margin, floor, and ceiling
- **Flexible Period Generation**: Handles non-standard interest periods with proper business day conventions
- **Interest Prepayment Tracking**: Manages upfront interest prepayments with automatic application to future periods
- **Principal Prepayment Handling**: Mid-period principal prepayments with segmented interest calculation
- **Payment Tracking**: Record and track interest payments and principal prepayments with status monitoring
- **Rate Management**: CSV-based storage for CME Term SOFR rates
- **Multiple Export Formats**: Generate schedules in CSV (main + segment details) and formatted text
- **Command-Line Interface**: Easy-to-use CLI for all operations
- **Actual/360 Day Count**: Industry-standard interest calculation methodology
- **PIK (Payment-In-Kind) Interest**: Support for capitalizing interest with configurable PIK rates

## Project Structure
```
LoanAdministration/
├── business_days.py          # Holiday calendar and business day calculations
├── loan_periods.py           # Interest period generation logic
├── interest_calculations.py  # Rate and interest calculation functions
├── sofr_rates.py             # SOFR rate data management
├── pik_elections.py          # PIK election management
├── loan.py                   # Main Loan class
├── loan_export.py            # Export functionality (CSV, text)
├── cli.py                    # Command-line interface
├── payments.py               # Payment recording and tracking
├── data/
│   └── sofr_rates.csv        # SOFR rate storage
│   └── pik_elections.csv     # PIK election storage
└── output/                   # Generated schedules
```

## Installation

### Requirements
- Python 3.8+
- No external dependencies (uses only standard library)

### Setup
```bash
# Clone the repository
git clone https://github.com/Pdelatorre/LoanAdministration
cd LoanAdministration

# Create necessary directories
mkdir -p data output

# The system is ready to use!
```

## Usage

### Managing SOFR Rates

List all available rates:
```bash
python cli.py list-rates
```

Add a new SOFR rate:
```bash
python cli.py add-rate 2025-01-30 4.55
```

### Creating a Loan and Generating Schedule

**Basic loan (interest-only, no PIK):**
```bash
python cli.py create \
  --loan-id LOAN-001 \
  --borrower "ABC Company" \
  --principal 1000000 \
  --margin 2.5 \
  --origination-date 2025-01-15 \
  --maturity-date 2025-04-30 \
  --floor 0.0 \
  --ceiling 8.0
```

**PIK loan (with interest capitalization):**

First, add PIK elections:
```bash
python cli.py add-pik LOAN-002 1 true   # Elect PIK for period 1
python cli.py add-pik LOAN-002 2 false  # Cash payment for period 2
```

Then create the loan with PIK rate:
```bash
python cli.py create \
  --loan-id LOAN-002 \
  --borrower "XYZ Company" \
  --principal 20000000 \
  --margin 2.5 \
  --pik-rate 5.0 \
  --origination-date 2025-01-15 \
  --maturity-date 2025-04-30
```

Both commands will:
1. Create the loan with specified terms
2. Identify required SOFR reset dates
3. Calculate interest for each period (with PIK if applicable)
4. Export schedule to `output/LOAN-ID_schedule.csv` and `.txt`

### PIK (Payment-In-Kind) Mechanics

When PIK is elected for a period:
- **PIK Amount** = Principal × PIK Rate × (Days / 360)
- **Cash Payment** = Interest Owed - PIK Amount  
- **New Principal** = Old Principal + PIK Amount

The capitalized PIK amount compounds in subsequent periods.

### Interest Prepayment

Many loans require interest to be prepaid at closing. The system tracks this balance and automatically applies it to future periods:
```bash
python cli.py create \
  --loan-id LOAN-003 \
  --borrower "ABC Company" \
  --principal 50000000 \
  --margin 2.5 \
  --interest-prepayment 2000000 \
  --origination-date 2025-01-15 \
  --maturity-date 2027-12-31
```

**How it works:**
- Prepaid balance is set at loan origination
- Automatically applied to each period's interest until exhausted
- PIK elections are blocked while prepaid balance exists
- Cash payments only required once prepaid is exhausted
- Full transparency with start/end balance tracking each period


### Payment Tracking and Principal Prepayments

The system tracks payments and handles mid-period principal prepayments with automatic segmented interest calculation:

**Record an interest payment:**
```bash
python cli.py add-payment \
  --loan-id LOAN-001 \
  --date 2025-01-31 \
  --amount 5833.33 \
  --type interest \
  --period 1 \
  --notes "Period 1 payment"
```

**Record a principal prepayment:**
```bash
python cli.py add-payment \
  --loan-id LOAN-001 \
  --date 2025-02-15 \
  --amount 100000.00 \
  --type principal_prepayment \
  --notes "Early paydown"
```

**View payment history:**
```bash
python cli.py list-payments LOAN-001
```

**How principal prepayments work:**
- Prepayment effective end-of-day on payment date
- Period is split into segments with different principal balances
- Interest calculated separately for each segment
- All future periods recalculated with reduced principal
- Segment details exported to separate CSV for transparency

### Example Output

**Regular Loan:**
```
✅ Loan created: LOAN-001
   Borrower: ABC Company
   Principal: $1,000,000.00
   Periods: 4

💰 Interest Schedule Generated:
   Total Interest: $20,856.94
   
   Exported to:
   - output/LOAN-001_schedule.csv
   - output/LOAN-001_schedule.txt
```

**PIK Loan:**
```
✅ Loan created: LOAN-002
   Borrower: XYZ Company
   Principal: $20,000,000.00
   Periods: 4
   PIK Rate: 5.00%

💰 Interest Schedule Generated:
   Total Interest Owed: $417,702.61
   Total PIK Capitalized: $133,536.65
   Total Cash Payments: $284,165.96
   Final Principal Balance: $20,133,536.65
   
   Exported to:
   - output/LOAN-002_schedule.csv
   - output/LOAN-002_schedule.txt
```

**Loan with Interest Prepayment:**
```
✅ Loan created: LOAN-003
   Borrower: ABC Company
   Principal: $50,000,000.00
   Periods: 36
   Interest Prepayment: $2,000,000.00

💰 Interest Schedule Generated:
   Total Interest Owed: $10,450,000.00
   Prepaid Coverage: First 14 periods fully covered
   Cash Payments Start: Period 15
```

**Loan with Principal Prepayment:**
```
💰 Recording $100,000 principal prepayment on Feb 15...

Period 2: Feb 1-28
  Principal: $1,000,000 → $900,000
  Interest: $5,228.75 (down from $5,483.33)
  
  Segments:
    Feb 1-15 @ $1,000,000: $2,937.50
    Feb 16-28 @ $900,000:  $2,291.25

Generated files:
- LOAN-001_schedule.csv (main schedule)
- LOAN-001_segments.csv (segment details)
- LOAN-001_schedule.txt (detailed report)
```

## Key Concepts

### Interest Period Calculation
- **First period**: Origination date to last business day of month
- **Middle periods**: First day to last business day of each month
- **Final period**: First day of maturity month to exact maturity date

### SOFR Reset Dates
SOFR rates are set **2 business days before** each interest period begins, following CME Term SOFR conventions.

### Rate Calculation
```
Effective Rate = max(SOFR Floor, min(SOFR, SOFR Ceiling)) + Margin
Interest = Principal × Effective Rate × (Days / 360)
```

## Technical Highlights

- **Business Day Handling**: Accounts for weekends and US Bank holidays
- **Date Arithmetic**: Handles edge cases (month-end, leap years, holiday adjustments)
- **Modular Design**: Separation of concerns with clear module boundaries
- **Data Persistence**: CSV-based storage with audit trails
- **Error Handling**: Validates required SOFR rates before calculation

## Use Cases

This system was built to address real-world challenges in loan operations:

1. **Manual Calculation Elimination**: Automates complex interest calculations that were previously done in Excel
2. **Rate Compliance**: Ensures contractually specified CME SOFR rates are used
3. **Audit Trail**: Maintains complete history of rates and calculations
4. **Reporting**: Generates schedules for accounting, investor reporting, and compliance

## Future Enhancements

- [ ] Prepayment penalties and fees
- [ ] Investor allocation module (pro-rata interest distribution)
- [ ] OID (Original Issue Discount) amortization
- [ ] Delinquency reporting
- [ ] Journal entry generation for GL posting
- [ ] Web-based interface
- [ ] Database backend for production scale

## Author

Built by Phillip L Delatorre Jr. as part of exploring AI/ML and business automation.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.