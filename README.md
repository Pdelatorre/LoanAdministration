# Loan Administration System

A comprehensive Python-based loan administration system for calculating interest, tracking payments, managing investor allocations, and generating professional distribution reports for floating-rate, interest-only loans with SOFR-based pricing.

## Features

### Core Loan Management
- **Floating Rate Calculations**: Supports 1-month Term SOFR with configurable margin, floor, and ceiling
- **Flexible Period Generation**: Handles non-standard interest periods with proper business day conventions
- **Interest Prepayment Tracking**: Manages upfront interest prepayments with automatic application to future periods
- **Principal Prepayment Handling**: Mid-period principal prepayments with segmented interest calculation
- **Payment Tracking**: Record and track interest payments and principal prepayments with status monitoring
- **PIK (Payment-In-Kind) Interest**: Support for capitalizing interest with configurable PIK rates

### Investor Management (v1.4)
- **Multi-Investor Support**: Track ownership percentages with unlimited investors per loan
- **Time-Based Ownership Changes**: Handle investor transfers with effective dates
- **Pro-Rata Allocation**: Automatically allocate interest, prepayments, and fees by ownership percentage
- **Day-Weighted Calculations**: When ownership changes mid-period, allocations are prorated by days owned
- **Ownership Validation**: Ensures ownership percentages always sum to 100%

### Professional Reporting (v1.4)
- **Investor Distribution Statements**: Generate professional statements for each investor
- **Multiple Output Formats**: 
  - Text reports for quick review
  - PDF reports for investor distribution
  - Excel audit reports (coming soon)
- **Customizable Branding**: Configure company name and styling via central config
- **Clean Formatting**: Professional layout with loan activity, investor allocation, and distribution summary

### Data Management
- **CSV-Based Storage**: Simple, auditable data storage for SOFR rates, investors, and payments
- **Rate Management**: Track CME Term SOFR rates with historical data
- **Multiple Export Formats**: Generate schedules in CSV (main + segment details) and formatted text
- **Actual/360 Day Count**: Industry-standard interest calculation methodology

### Developer Features
- **Command-Line Interface**: Comprehensive CLI for all operations
- **Modular Architecture**: Clean separation of concerns with well-defined modules
- **Configuration Management**: Central config file for all system settings
- **Comprehensive Testing**: Full test suite for loan calculations and investor allocations
- **Easy Setup**: Automated installation script with dependency management

## Project Structure
```
LoanAdministration/
├── config.py                      # Central configuration (company name, paths, etc.)
├── requirements.txt               # Python dependencies
├── setup.sh                       # Automated setup script
├── README.md                      # This file

# Core Loan System
├── loan.py                        # Main Loan class with calculations
├── business_days.py               # Holiday calendar and business day calculations
├── loan_periods.py                # Interest period generation logic
├── interest_calculations.py       # Rate and interest calculation functions
├── sofr_rates.py                  # SOFR rate data management
├── pik_elections.py               # PIK election management
├── payments.py                    # Payment recording and tracking
├── loan_export.py                 # Export functionality (CSV, text)

# Investor System (v1.4)
├── investors.py                   # Investor ownership tracking
├── investor_allocation.py         # Pro-rata allocation engine
├── investor_reports.py            # Text report generation
├── investor_reports_pdf.py        # PDF report generation

# Fee System (v1.5)
├── fees.py                        # Fee storage and management
├── fee_allocation.py              # Pro-rata fee allocation

# Interface & Testing
├── cli.py                         # Command-line interface
├── test_loan_system.py            # Loan calculation tests
├── test_investor_system.py        # Investor allocation tests
├── test_config.py                 # Configuration integration tests
├── demo_investor_workflow.sh      # Complete workflow demonstration

# Data Storage
├── data/
│   ├── sofr_rates.csv             # SOFR rate storage
│   ├── pik_elections.csv          # PIK election storage
│   ├── investors.csv              # Investor ownership records (auto-generated)
│   └── payments.csv               # Payment history (auto-generated)

# Generated Reports
└── output/
    ├── investor_reports/          # Text investor statements
    ├── investor_reports_pdf/      # PDF investor statements
    └── audit_reports/             # Excel audit reports (coming soon)
```

## Installation

### Quick Start (Recommended)
```bash
# Clone the repository
git clone https://github.com/Pdelatorre/LoanAdministration
cd LoanAdministration

# Run automated setup
bash setup.sh
```

This will:
- Install all dependencies (reportlab, openpyxl, etc.)
- Create necessary directories
- Set up SOFR rates template
- Verify system requirements

### Manual Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Create directory structure
mkdir -p data output/investor_reports output/investor_reports_pdf output/audit_reports
```

**No additional system dependencies required!**

### Requirements
- **Python 3.8+** required
- **reportlab** for PDF generation
- **openpyxl** for Excel exports
- **xlsxwriter** for advanced Excel formatting

See `requirements.txt` for complete dependency list.

## Configuration

### Initial Setup

1. Edit `config.py` and update company information:
```python
COMPANY_NAME = "Your Company Name"  # ⚠️ Change this!
COMPANY_ADDRESS_LINE1 = "123 Main Street"
COMPANY_CITY_STATE_ZIP = "New York, NY 10001"
```

2. Add SOFR rates to `data/sofr_rates.csv`:
```csv
date,rate
2025-01-30,0.0455
2025-02-27,0.0460
2025-03-28,0.0465
```

3. Test the installation:
```bash
python test_config.py
```

## Usage Guide

### 1. Managing SOFR Rates

**List all available rates:**
```bash
python cli.py list-rates
```

**Add a new SOFR rate:**
```bash
python cli.py add-rate 2025-01-30 4.55
```

**SOFR rate sources:**
- Federal Reserve: https://www.newyorkfed.org/markets/reference-rates/sofr
- Bloomberg Terminal: SOFR Index
- Treasury Direct: Daily SOFR rates

### 2. Creating a Loan

**Basic loan (interest-only):**
```bash
python cli.py create \
  --loan-id LOAN-001 \
  --borrower "ABC Company LLC" \
  --loan-name "ABC" \
  --principal 5000000 \
  --margin 2.5 \
  --origination-date 2025-01-15 \
  --maturity-date 2025-12-31
```

**Parameters:**
- `--loan-id`: Unique identifier (e.g., LOAN-001)
- `--borrower`: Legal entity name
- `--loan-name`: Short display name for reports (defaults to borrower)
- `--principal`: Loan amount in dollars
- `--margin`: Spread over SOFR in basis points (e.g., 2.5 for 2.50%)
- `--origination-date`: Loan start date (YYYY-MM-DD)
- `--maturity-date`: Loan end date (YYYY-MM-DD)

**Optional parameters:**
- `--floor`: SOFR floor (default: 0)
- `--ceiling`: SOFR ceiling (default: none)
- `--pik-rate`: PIK interest rate
- `--interest-prepayment`: Upfront interest prepayment amount

### 3. Adding Investors

**Add initial investors:**
```bash
python cli.py add-investor \
  --loan-id LOAN-001 \
  --investor-id INV-A \
  --investor-name "Investor A LLC" \
  --ownership-pct 40.0 \
  --effective-date 2025-01-15

python cli.py add-investor \
  --loan-id LOAN-001 \
  --investor-id INV-B \
  --investor-name "Investor B Fund" \
  --ownership-pct 60.0 \
  --effective-date 2025-01-15
```

**Record ownership changes:**
```bash
# Investor A sells 10% to new Investor C
python cli.py add-investor \
  --loan-id LOAN-001 \
  --investor-id INV-A \
  --investor-name "Investor A LLC" \
  --ownership-pct 30.0 \
  --effective-date 2025-06-15

python cli.py add-investor \
  --loan-id LOAN-001 \
  --investor-id INV-C \
  --investor-name "Investor C Capital" \
  --ownership-pct 10.0 \
  --effective-date 2025-06-15
```

**View current investors:**
```bash
python cli.py list-investors LOAN-001
python cli.py list-investors LOAN-001 --date 2025-06-30  # As of specific date
```

### 4. Recording Payments

**Interest payment:**
```bash
python cli.py add-payment \
  --loan-id LOAN-001 \
  --date 2025-01-31 \
  --amount 16250.00 \
  --type interest_payment \
  --notes "Period 1 interest"
```

**Principal prepayment:**
```bash
python cli.py add-payment \
  --loan-id LOAN-001 \
  --date 2025-06-15 \
  --amount 500000.00 \
  --type principal_prepayment \
  --notes "Voluntary prepayment"
```

**View payment history:**
```bash
python cli.py list-payments LOAN-001
```

### 5. Managing Fees

**Add a fee:**
```bash
python cli.py add-fee \
  --loan-id LOAN-001 \
  --date 2025-02-15 \
  --type prepayment_fee \
  --amount 10000.00 \
  --period 2 \
  --description "Early payoff penalty - 2% of prepayment"
```

**Fee types available:**
- `prepayment_fee` - Prepayment penalty
- `prepayment_interest` - Interest on prepayment amount
- `amendment_fee` - Fee for loan modifications
- `exit_fee` - Fee at loan payoff
- `waiver_fee` - Covenant waiver fee
- `default_interest` - Default interest (after negotiation)
- `other` - Other miscellaneous fees

**Optional parameters:**
- `--cash-or-pik` - Whether fee is cash or PIK (default: cash)
- `--period` - Period number to assign fee to
- `--description` - Description of the fee

**View all fees:**
```bash
python cli.py list-fees LOAN-001
```

**Output:**
```
Fees for LOAN-001:
====================================================================================================
Date         | Type                      |         Amount | C/P  | Period | Description
====================================================================================================
2025-02-15   | Prepayment Fee            | $   10,000.00 | cash | P2     | Early payoff penalty
2025-02-20   | Amendment Fee             | $    5,000.00 | cash | P2     | Rate modification
====================================================================================================
TOTAL        |                           | $   15,000.00
```

**PIK fees (capitalize into principal):**
```bash
python cli.py add-fee \
  --loan-id LOAN-001 \
  --date 2025-03-15 \
  --type amendment_fee \
  --amount 25000.00 \
  --cash-or-pik pik \
  --period 3 \
  --description "Amendment fee - capitalized"
```

### 6. Generating Investor Reports

**Create script for report generation** (`generate_reports.py`):
```python
from datetime import datetime
from loan import Loan
from investor_allocation import allocate_period_to_investors
from investor_reports_pdf import generate_all_investor_pdfs
from sofr_rates import load_sofr_rates

# Create loan
loan = Loan(
    loan_id="LOAN-001",
    borrower="ABC Company LLC",
    loan_name="ABC",
    principal=5000000,
    margin=0.025,
    origination_date=datetime(2025, 1, 15),
    maturity_date=datetime(2025, 12, 31)
)

# Generate schedule
sofr_rates = load_sofr_rates()
schedule = loan.calculate_schedule(sofr_rates=sofr_rates)

# Generate reports for Period 2
period_number = 2
allocation = allocate_period_to_investors("LOAN-001", schedule[period_number - 1])

# Generate PDFs for all investors
pdf_files = generate_all_investor_pdfs(
    loan=loan,
    period_data=schedule[period_number - 1],
    allocation_data=allocation
)

print(f"✅ Generated {len(pdf_files)} investor reports")
```

**Reports automatically include:**
- Interest income allocation
- Fee income (if any fees exist for the period)
- Principal activity
- Income summary

**Output:** `output/investor_reports_pdf/LOAN-001_Period2_INV-A.pdf`

### 7. Complete Monthly Workflow

**Run the demo workflow:**
```bash
bash demo_investor_workflow.sh
```

This demonstrates:
1. Creating a loan
2. Adding investors
3. Recording payments
4. Adding fees
5. Generating investor distribution statements

## How It Works

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

### Investor Allocation with Ownership Changes

When ownership changes mid-period, the system automatically:
1. **Segments the period** by ownership change dates
2. **Calculates pro-rata by days**:
```
   Investor Share = (Segment Days / Total Days) × Total Interest × Ownership %
```
3. **Aggregates segments** for each investor
4. **Validates totals** match loan-level calculations

**Example:**
```
Period: Feb 1-28 (28 days)
Interest: $10,000

Feb 1-14 (14 days):  Investor A = 40%, B = 60%
Feb 15-28 (14 days): Investor A = 30%, B = 50%, C = 20%

Investor A allocation:
  Segment 1: (14/28) × $10,000 × 40% = $2,000
  Segment 2: (14/28) × $10,000 × 30% = $1,500
  Total: $3,500
```

### Principal Prepayments

**Mid-period prepayments:**
- Effective end-of-day on payment date
- Period split into segments with different principal balances
- Interest calculated separately for each segment
- All future periods recalculated with reduced principal
- Each investor receives pro-rata portion based on ownership

### PIK (Payment-In-Kind) Mechanics

When PIK is elected for a period:
- **PIK Amount** = Principal × PIK Rate × (Days / 360)
- **Cash Payment** = Interest Owed - PIK Amount  
- **New Principal** = Old Principal + PIK Amount
- PIK amount compounds in subsequent periods

## Example Output

### Investor Loan Statement
```
┌─────────────────────────────────────────────────────────────┐
│               INVESTOR LOAN STATEMENT                       │
└─────────────────────────────────────────────────────────────┘

Investor A LLC

Loan: ABC
Period: February 01, 2025 - February 28, 2025
Your Ownership: 40.00%

─────────────────────────────────────────────────────────────

TOTAL LOAN ACTIVITY
...

YOUR ALLOCATION (40.00%)
...

ADDITIONAL INCOME

Prepayment Fee (Feb 15):                      $   10,000.00
Amendment Fee (Feb 20):                       $    4,000.00
                                              ────────────────
Total Additional Income:                      $   14,000.00

─────────────────────────────────────────────────────────────

INCOME SUMMARY

Interest Income:                                  $   10,653.33
Additional Income:                              $   14,000.00
                                              ────────────────
Total Income Earned:                          $   24,653.33

─────────────────────────────────────────────────────────────
```

## Technical Highlights

- **Business Day Handling**: Accounts for weekends and US Bank holidays
- **Date Arithmetic**: Handles edge cases (month-end, leap years, holiday adjustments)
- **Modular Design**: Separation of concerns with clear module boundaries
- **Pro-Rata Allocation**: Sophisticated ownership change handling with day-weighting
- **PDF Generation**: Professional reports using reportlab with table formatting
- **Configuration Management**: Central config file for easy customization
- **Data Persistence**: CSV-based storage with complete audit trails
- **Error Handling**: Validates required SOFR rates, ownership percentages, and data integrity
- **Comprehensive Testing**: Full test coverage for calculations and allocations

## Testing

**Run all tests:**
```bash
python test_loan_system.py       # Loan calculations
python test_investor_system.py   # Investor allocations
python test_config.py            # Configuration integration
```

**Run demo workflow:**
```bash
bash demo_investor_workflow.sh
```

## Use Cases

This system addresses real-world challenges in private credit fund operations:

1. **Manual Calculation Elimination**: Automates complex interest and allocation calculations
2. **Investor Reporting**: Generates professional distribution statements for LP reporting
3. **Ownership Changes**: Handles investor transfers with precise pro-rata calculations
4. **Rate Compliance**: Ensures contractually specified CME SOFR rates are used
5. **Audit Trail**: Maintains complete history of rates, payments, and ownership
6. **Month-End Close**: Streamlines period-end reporting workflow
7. **Regulatory Compliance**: Provides documentation for auditors and regulators

## Roadmap

### ✅ v1.5 (Current Release)
- [x] Fee tracking and allocation (prepayment, amendment, exit, waiver, default interest)
- [x] Point-in-time fee allocation to investors
- [x] Default interest calculator for negotiations
- [x] Fee reporting in investor statements and audit reports

### v1.6 (Next Release)
- [ ] Automated PDF generation via CLI
- [ ] PIK fee capitalization
- [ ] Email distribution integration
- [ ] Distribution notices (separate from loan admin memos)

### Future Enhancements
- [ ] Prepayment penalties and make-whole calculations
- [ ] OID (Original Issue Discount) amortization
- [ ] Delinquency reporting and aging
- [ ] Journal entry generation for GL posting
- [ ] Multi-loan portfolio dashboard
- [ ] Web-based interface
- [ ] Database backend for production scale
- [ ] API for external system integration

## Version History

- **v1.5** (Feb 2026): Fee management system
- **v1.4** (Jan 2026): Investor management, allocation engine, PDF reports
- **v1.3** (Jan 2026): Payment tracking, principal prepayments
- **v1.2** (Jan 2026): Interest prepayment handling
- **v1.1** (Dec 2025): PIK interest support
- **v1.0** (Dec 2025): Initial release with core calculations

## Documentation

- **Process Guide**: See `PROCESS_GUIDE.md` (coming soon) for complete workflow documentation
- **Configuration**: Review `config.py` for all customization options
- **CLI Reference**: Run `python cli.py --help` for command documentation
- **API Documentation**: See individual module docstrings

## Support & Contributing

For issues, questions, or contributions:
- Review test files for usage examples
- Check demo workflow script for complete scenarios
- See troubleshooting section in process guide

## Author

Built by Phillip L Delatorre Jr. as part of exploring AI/ML, business automation, and professional loan administration systems.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

- **v1.4** (Jan 2026): Investor management, pro-rata allocation, PDF reports (reportlab), Excel audit reports