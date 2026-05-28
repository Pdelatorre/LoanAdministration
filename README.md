# Loan Administration System

A comprehensive Python-based loan administration system for calculating interest, tracking payments, managing investor allocations, and generating professional distribution reports for floating-rate, interest-only loans with SOFR-based pricing.

## Features

### Core Loan Management
- **Floating Rate Calculations**: Supports 1-month Term SOFR with configurable margin, floor, and ceiling
- **Flexible Period Generation**: Handles non-standard interest periods with business day conventions (last business day or calendar month end)
- **Interest Prepayment Tracking**: Manages upfront interest prepayments with automatic application to future periods
- **Principal Prepayment Handling**: Mid-period principal prepayments with segmented interest calculation
- **Payment Tracking**: Record and track interest payments and principal prepayments with status monitoring
- **PIK (Payment-In-Kind) Interest**: Support for capitalizing interest with configurable PIK rates
- **OID (Original Issue Discount)**: Day-weighted straight-line amortization with full funding waterfall (net investor call, net borrower advance, closing expenses)
- **Warrant OID**: A separate OID tranche attributable to warrants issued at closing — amortized like cash OID but reported separately and never increased by amendments
- **OID Amendments**: Maturity extensions and capitalized amendment fees (additional OID) re-amortize the unamortized residual over the remaining life while preserving the OID already recognized in historical periods (`oid_amendments.py`)
- **Loan Lifecycle & Versioning**: Every loan moves through `draft → active → closed` with version bumps and an append-only audit trail recording each change (created, corrected, recreated, activated, amended, closed)
- **Loan Persistence**: CSV-backed loan storage with append-only audit history (`loan_storage.py`)

### Investor Management (v1.4)
- **Multi-Investor Support**: Track ownership percentages with unlimited investors per loan
- **Time-Based Ownership Changes**: Handle investor transfers with effective dates
- **Pro-Rata Allocation**: Automatically allocate interest, prepayments, and fees by ownership percentage
- **Day-Weighted Calculations**: When ownership changes mid-period, allocations are prorated by days owned
- **Ownership Validation**: Ensures ownership percentages always sum to 100%

### Professional Reporting (v1.4+)
- **Investor Distribution Statements**: Generate professional statements for each investor
- **Multiple Output Formats**:
  - Text reports for quick review
  - PDF reports for investor distribution
  - Excel audit reports
- **Distribution Notices**: Interim and supplemental notices for mid-period or post-statement distributions (text + PDF)
- **Customizable Branding**: Configure company name and styling via central config
- **Clean Formatting**: Professional layout with loan activity, investor allocation, and distribution summary

### Fee System (v1.5)
- **Fee Tracking**: Record prepayment, amendment, exit, waiver, default interest, and other fees
- **Pro-Rata Allocation**: Fees allocated to investors by ownership percentage at time of fee
- **Cash or PIK**: Each fee can be designated cash or capitalized (PIK)
- **Period Assignment**: Fees can be assigned to specific interest periods

### Data Management
- **CSV-Based Storage**: Simple, auditable data storage for SOFR rates, investors, payments, fees, and loans
- **Rate Management**: Track CME Term SOFR rates with historical data
- **Multiple Export Formats**: Generate schedules in CSV (main + segment details) and formatted text
- **Actual/360 Day Count**: Industry-standard interest calculation methodology

### Developer Features
- **Command-Line Interface**: Comprehensive CLI for all operations
- **Modular Architecture**: Clean separation of concerns with well-defined modules
- **Configuration Management**: Central config file for all system settings
- **Comprehensive Testing**: Full test suite for loan calculations and investor allocations
- **Rate Diagnostic Tool**: `diagnose_rates.py` traces the full calculation chain for precision debugging
- **Easy Setup**: Automated installation script with dependency management

## Project Structure
```
LoanAdministration/
├── config.py                      # Central configuration (company name, paths, etc.)
├── requirements.txt               # Python dependencies
├── setup.sh                       # Automated setup script
├── README.md                      # This file
├── PROCESS_GUIDE.md               # Non-technical user guide (PowerShell / Windows)
├── WALKTHROUGH.md                 # Complete 8-period loan lifecycle walkthrough (bash)
├── WALKTHROUGH_POWERSHELL.md      # Same walkthrough adapted for PowerShell / Windows

# Core Loan System
├── loan.py                        # Main Loan class with calculations
├── business_days.py               # Holiday calendar and business day calculations
├── loan_periods.py                # Interest period generation logic
├── interest_calculations.py       # Rate and interest calculation functions
├── sofr_rates.py                  # SOFR rate data management
├── pik_elections.py               # PIK election management
├── payments.py                    # Payment recording and tracking
├── loan_export.py                 # Export functionality (CSV, text)
├── loan_storage.py                # Loan persistence (loans.csv + audit history)
├── oid_calculations.py            # OID amortization (incl. amendment-aware) and funding waterfall
├── oid_amendments.py              # OID amendment events (maturity extension / additional OID)

# Investor System (v1.4)
├── investors.py                   # Investor ownership tracking
├── investor_allocation.py         # Pro-rata allocation engine
├── investor_reports.py            # Text report generation
├── investor_reports_pdf.py        # PDF report generation

# Fee System (v1.5)
├── fees.py                        # Fee storage and management
├── fee_allocation.py              # Pro-rata fee allocation

# Distribution Notices (v1.6)
├── distribution_notices.py        # Interim and supplemental notice generation (text)
├── distribution_notices_pdf.py    # PDF distribution notices

# Interface, Diagnostics & Testing
├── cli.py                         # Command-line interface
├── diagnose_rates.py              # Rate precision diagnostic tool
├── test_audit_report.py           # Audit report tests
├── test_config.py                 # Configuration integration tests
├── test_fee_allocation.py         # Fee allocation tests
├── test_fees_on_reports.py        # Fee reporting integration tests
├── test_investor_system.py        # Investor allocation tests
├── test_naming_and_columns.py     # Report naming and column tests
├── test_oid_amendment.py          # Amendment-aware OID / warrant OID tests
├── test_pdf_simple.py             # PDF generation tests
├── demo_investor_workflow.sh      # Complete workflow demonstration

# Data Storage
├── data/
│   ├── sofr_rates.csv             # SOFR rate storage (gitignored)
│   ├── pik_elections.csv          # PIK election storage (gitignored)
│   ├── investors.csv              # Investor ownership records (gitignored)
│   ├── payments.csv               # Payment history (gitignored)
│   ├── fees.csv                   # Fee records (gitignored)
│   ├── loans.csv                  # Current loan state (gitignored)
│   ├── loans_history.csv          # Append-only loan audit trail (gitignored)
│   ├── oid_amendments.csv         # OID amendment events, created on first amendment (gitignored)
│   └── *_template.csv             # Template files (tracked in git)

# Generated Reports
└── output/
    ├── investor_reports/          # Text investor statements
    ├── investor_reports_pdf/      # PDF investor statements
    ├── audit_reports/             # Excel audit reports
    ├── distribution_notices/      # Text distribution notices
    └── distribution_notices_pdf/  # PDF distribution notices
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
mkdir -p data output/investor_reports output/investor_reports_pdf output/audit_reports output/distribution_notices output/distribution_notices_pdf
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

2. Add SOFR rates to `data/sofr_rates.csv` (or use `python cli.py add-rate`). The file uses CME Term SOFR columns, with rates stored as decimals:
```csv
reset_date,term_sofr_1m,source,date_added
2025-01-30,0.04550,CME,2025-01-30
2025-02-27,0.04600,CME,2025-02-27
2025-03-28,0.04650,CME,2025-03-28
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

### 2. Creating a Loan

A loan is created as a **draft** (version 1). Draft terms can be corrected freely; once you `activate-loan`, terms are locked and any further change must go through `amend-loan` (see [Loan Lifecycle](#3-loan-lifecycle) below).

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

**Loan with OID and closing expenses:**
```bash
python cli.py create \
  --loan-id LOAN-001 \
  --borrower "ABC Company LLC" \
  --loan-name "ABC" \
  --principal 5000000 \
  --margin 2.5 \
  --origination-date 2025-01-15 \
  --maturity-date 2025-12-31 \
  --oid 50000 \
  --warrant-oid 10000 \
  --expenses 15000 \
  --interest-prepayment 20000
```

**Required parameters:**
- `--loan-id`: Unique identifier (e.g., LOAN-001)
- `--borrower`: Legal entity name
- `--principal`: Loan amount in dollars
- `--margin`: Spread over SOFR in percent (e.g., `2.5` for 2.50%)
- `--origination-date`: Loan start date (YYYY-MM-DD)
- `--maturity-date`: Loan end date (YYYY-MM-DD)

**Optional parameters:**
- `--loan-name`: Short display name for reports (defaults to borrower)
- `--floor`: SOFR floor in percent (default: 0)
- `--ceiling`: SOFR ceiling in percent (default: none)
- `--pik-rate`: PIK interest rate in percent
- `--interest-prepayment`: Upfront interest prepayment amount (dollars)
- `--oid`: Original Issue Discount at closing (dollars)
- `--warrant-oid`: Warrant OID at closing (dollars) — amortized separately, never increased by amendments
- `--expenses`: Closing expenses deducted from the investor call before the borrower wire (dollars)
- `--convention`: `last_business_day` (default) or `calendar_month_end`

### 3. Loan Lifecycle

Loans progress through `draft → active → closed`. Every change is written to an append-only audit trail (`data/loans_history.csv`).

**Correct a draft** (drafts only; bumps version):
```bash
python cli.py correct-loan --loan-id LOAN-001 --margin 2.75 --reason "Typo in rate sheet"
```

**Recreate a draft from scratch** (resets to version 1):
```bash
python cli.py recreate-draft --loan-id LOAN-001 --borrower "ABC Company LLC" \
  --principal 5000000 --margin 2.5 --origination-date 2025-01-15 \
  --maturity-date 2025-12-31 --reason "Restructured terms before funding"
```

**Activate a loan** (draft → active; terms become locked):
```bash
python cli.py activate-loan --loan-id LOAN-001
```

**Amend an active loan** (`--reason` is mandatory and permanently logged):
```bash
# Maturity extension that also capitalizes a $25,000 amendment fee as new OID.
# --effective-date splits the OID schedule so periods before the amendment keep
# their original OID, and the unamortized residual + additional OID re-amortize
# over the remaining periods to the new maturity.
python cli.py amend-loan \
  --loan-id LOAN-001 \
  --maturity-date 2026-06-30 \
  --additional-oid 25000 \
  --effective-date 2025-12-31 \
  --reason "Amendment No.1 - 6-month extension + fee per CA dated 2025-12-31"
```
`--effective-date` is required whenever `--maturity-date` changes or `--additional-oid > 0`. OID and warrant OID set at origination are **not** otherwise amendable.

**Close a loan** (fully repaid):
```bash
python cli.py close-loan --loan-id LOAN-001 --reason "Repaid in full"
```

**Inspect loans and history:**
```bash
python cli.py list-loans                 # all loans with status and version
python cli.py loan-history LOAN-001       # full audit trail for one loan
```

### 4. Adding Investors

**Add initial investors** (`--investor-short-name` is required and used as the display label in reports/filenames):
```bash
python cli.py add-investor \
  --loan-id LOAN-001 \
  --investor-id INV-A \
  --investor-name "Investor A LLC" \
  --investor-short-name "Investor A" \
  --ownership-pct 40.0 \
  --effective-date 2025-01-15

python cli.py add-investor \
  --loan-id LOAN-001 \
  --investor-id INV-B \
  --investor-name "Investor B Fund" \
  --investor-short-name "Investor B" \
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
  --investor-short-name "Investor A" \
  --ownership-pct 30.0 \
  --effective-date 2025-06-15

python cli.py add-investor \
  --loan-id LOAN-001 \
  --investor-id INV-C \
  --investor-name "Investor C Capital" \
  --investor-short-name "Investor C" \
  --ownership-pct 10.0 \
  --effective-date 2025-06-15
```

**View current investors:**
```bash
python cli.py list-investors LOAN-001
python cli.py list-investors LOAN-001 --date 2025-06-30  # As of specific date
```

### 5. Recording Payments

**Interest payment** (use `--period` to tie it to an interest period):
```bash
python cli.py add-payment \
  --loan-id LOAN-001 \
  --date 2025-01-31 \
  --amount 16250.00 \
  --type interest \
  --period 1 \
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

`--type` accepts `interest` or `principal_prepayment`.

**View payment history:**
```bash
python cli.py list-payments LOAN-001
```

### 6. Managing Fees

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

### 7. Generating Investor Reports

Report generation is driven entirely from the CLI. Reports can only be generated for periods that have a SOFR rate on file.

**Check which periods are ready:**
```bash
python cli.py check-periods LOAN-001
```

**Export the full interest schedule (CSV + text):**
```bash
python cli.py generate-schedule --loan-id LOAN-001
```

**Generate investor statements (text + PDF) for one period:**
```bash
python cli.py generate-period-reports --loan-id LOAN-001 --period 2
# add --force to overwrite existing reports
```

**Batch-generate reports for every period with a rate:**
```bash
python cli.py generate-all-period-reports --loan-id LOAN-001
# optionally scope with --start-period / --end-period
```

**Generate the Excel audit report:**
```bash
python cli.py generate-audit-report --loan-id LOAN-001
```

Output: `output/investor_reports_pdf/ABC_Period2_InvestorA.pdf` (filenames use the loan name and each investor's short name).

### 8. Generating Distribution Notices

Distribution notices document cash activity outside the normal month-end statement cycle. The total amount is allocated to investors by ownership as of the effective date, and both text and PDF notices are produced.

- **Interim**: Mid-period wire sent before the period closes
- **Supplemental**: Post-statement event after period reports are already issued

**Interim notice (mid-period wire):**
```bash
python cli.py generate-distribution-notice \
  --loan-id LOAN-001 \
  --period 2 \
  --type interim \
  --effective-date 2025-03-15 \
  --amount 50000.00 \
  --description "Interim interest distribution" \
  --wire-ref "WIRE-20250315-001"
```

**Supplemental notice (after the period statement was issued):**
```bash
python cli.py generate-distribution-notice \
  --loan-id LOAN-001 \
  --period 2 \
  --type supplemental \
  --effective-date 2025-04-10 \
  --amount 4000.00 \
  --description "Amendment Fee - Amendment No. 1" \
  --original-statement-date 2025-04-01
```

Output: `output/distribution_notices_pdf/ABC_Period2_Interim_2025-03-15_InvestorA.pdf`

### 9. Complete Monthly Workflow

**Run the demo workflow:**
```bash
bash demo_investor_workflow.sh
```

**Follow the full walkthrough (bash):**
```bash
# See WALKTHROUGH.md for a complete 8-period lifecycle example
```

**Follow the full walkthrough (Windows PowerShell):**
```powershell
# See WALKTHROUGH_POWERSHELL.md for the Windows-adapted version
```

## How It Works

### Interest Period Calculation
- **First period**: Origination date to last business day of month
- **Middle periods**: First day to last business day of each month
- **Final period**: First day of maturity month to exact maturity date

Period end convention is configurable: `last_business_day` (default) or `calendar_month_end`.

### SOFR Reset Dates
SOFR rates are set **2 business days before** each interest period begins, following CME Term SOFR conventions.

### Rate Calculation
```
Effective Rate = max(SOFR Floor, min(SOFR, SOFR Ceiling)) + Margin
Interest = Principal × Effective Rate × (Days / 360)
```

### OID Funding Waterfall
```
Net Investor Call    = Principal - Interest Prepayment - OID
Net Borrower Advance = Net Investor Call - Closing Expenses

OID amortization (day-weighted straight-line):
  period_oid = OID × (period_days / total_loan_days)
  Last period absorbs any penny-rounding residual
```

**Warrant OID** is a separate tranche amortized with the same day-weighted method and reported on its own line. It is fixed at origination and is never increased by amendments (warrants are not re-issued post-closing).

### OID Amendments (segmented re-amortization)

When a loan is amended with a maturity extension and/or capitalized OID, the historical periods must keep the OID they already recognized — re-running the whole schedule against the new maturity would wrongly shrink prior periods. Instead, the schedule is **segmented** by amendment effective date:

1. Periods before the amendment keep their original OID.
2. The unamortized residual at the effective date, plus any `--additional-oid`, is re-amortized day-weighted over the remaining periods to the new maturity.
3. The final period absorbs penny-rounding so the lifetime total still equals `original OID + Σ additions` exactly.

Amendment events are recorded in `data/oid_amendments.csv`, capturing the prior maturity (to replay the pre-amendment horizon), the new maturity, and the additional OID.

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

Mid-period prepayments:
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

Interest Income:                              $   10,653.33
Additional Income:                            $   14,000.00
                                              ────────────────
Total Income Earned:                          $   24,653.33
─────────────────────────────────────────────────────────────
```

## Diagnostics

**Trace rate precision through the full calculation chain:**
```bash
python diagnose_rates.py
```

This tool verifies every step from SOFR data loading through final interest output, useful for debugging rounding or precision discrepancies.

## Testing

**Run all tests:**
```bash
python test_config.py
python test_investor_system.py
python test_audit_report.py
python test_fee_allocation.py
python test_fees_on_reports.py
python test_naming_and_columns.py
python test_oid_amendment.py
python test_pdf_simple.py
```

**Run demo workflow:**
```bash
bash demo_investor_workflow.sh
```

## Technical Highlights

- **Business Day Handling**: Accounts for weekends and US Bank holidays
- **Date Arithmetic**: Handles edge cases (month-end, leap years, holiday adjustments)
- **Modular Design**: Separation of concerns with clear module boundaries
- **Pro-Rata Allocation**: Sophisticated ownership change handling with day-weighting
- **OID Amortization**: Day-weighted straight-line with exact penny reconciliation
- **PDF Generation**: Professional reports using reportlab with table formatting
- **Configuration Management**: Central config file for easy customization
- **Data Persistence**: CSV-based storage with complete audit trails
- **Error Handling**: Validates required SOFR rates, ownership percentages, and data integrity
- **Comprehensive Testing**: Full test coverage for calculations and allocations

## Use Cases

This system addresses real-world challenges in private credit fund operations:

1. **Manual Calculation Elimination**: Automates complex interest and allocation calculations
2. **Investor Reporting**: Generates professional distribution statements for LP reporting
3. **Ownership Changes**: Handles investor transfers with precise pro-rata calculations
4. **Rate Compliance**: Ensures contractually specified CME SOFR rates are used
5. **Audit Trail**: Maintains complete history of rates, payments, and ownership
6. **Month-End Close**: Streamlines period-end reporting workflow
7. **Distribution Notices**: Documents interim and supplemental cash distributions
8. **OID Accounting**: Tracks and amortizes original issue discount (incl. warrant OID and amendment-driven re-amortization) per loan period
9. **Regulatory Compliance**: Provides documentation for auditors and regulators

## Roadmap

### ✅ v1.7 (Current Release)
- [x] Warrant OID as a separate, independently-reported tranche
- [x] OID amendments — maturity extensions and capitalized fees with segmented re-amortization that preserves historical periods (`oid_amendments.py`)
- [x] SOFR floor/ceiling surfaced in the schedule output and investor/audit reports

### ✅ v1.6
- [x] Distribution notices — Interim and Supplemental (text + PDF), via CLI
- [x] OID (Original Issue Discount) amortization with funding waterfall
- [x] Loan persistence (`loan_storage.py`) with append-only audit history
- [x] Loan lifecycle CLI — draft → active → closed with versioning, corrections, amendments
- [x] Automated report generation via CLI (`generate-period-reports`, `generate-all-period-reports`, `generate-audit-report`)
- [x] Period end convention option (last business day vs. calendar month end)
- [x] Rate precision diagnostic tool (`diagnose_rates.py`)

### ✅ v1.5
- [x] Fee tracking and allocation (prepayment, amendment, exit, waiver, default interest)
- [x] Point-in-time fee allocation to investors
- [x] Fee reporting in investor statements and audit reports

### ✅ v1.4
- [x] Multi-investor ownership tracking with time-based changes
- [x] Pro-rata allocation engine with day-weighting
- [x] PDF investor statements and Excel audit reports

### Future Enhancements
- [ ] PIK fee capitalization
- [ ] Email distribution integration
- [ ] Prepayment penalties and make-whole calculations
- [ ] Delinquency reporting and aging
- [ ] Journal entry generation for GL posting
- [ ] Multi-loan portfolio dashboard
- [ ] Web-based interface
- [ ] Database backend for production scale

## Version History

- **v1.7** (May 2026): Warrant OID tranche, OID amendments with segmented re-amortization, SOFR floor/ceiling in reports
- **v1.6** (May 2026): Distribution notices, OID amortization, loan persistence, loan lifecycle CLI, rate diagnostics
- **v1.5** (Feb 2026): Fee management system
- **v1.4** (Jan 2026): Investor management, allocation engine, PDF reports
- **v1.3** (Jan 2026): Payment tracking, principal prepayments
- **v1.2** (Jan 2026): Interest prepayment handling
- **v1.1** (Dec 2025): PIK interest support
- **v1.0** (Dec 2025): Initial release with core calculations

## Documentation

- **Process Guide**: See `PROCESS_GUIDE.md` for non-technical user walkthrough (Windows/PowerShell)
- **Loan Walkthrough**: See `WALKTHROUGH.md` for complete 8-period lifecycle example (bash)
- **PowerShell Walkthrough**: See `WALKTHROUGH_POWERSHELL.md` for Windows-adapted version
- **Configuration**: Review `config.py` for all customization options
- **CLI Reference**: Run `python cli.py --help` for command documentation

## Author

Built by Phillip L Delatorre Jr. as part of exploring AI/ML, business automation, and professional loan administration systems.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
