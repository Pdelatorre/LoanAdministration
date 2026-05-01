# Loan Administration System — Process Guide
### For Non-Technical Users | PowerShell on Windows

---

## First-Time Setup (Do This Once)

This section only needs to be completed once when setting up the program on a new machine.

**Step 1 — Confirm Python is installed:**
```powershell
python --version
```
You should see something like `Python 3.11.x`. If you see an error, Python is not installed — contact your system administrator.

**Step 2 — Navigate to the program folder:**
```powershell
cd C:\Path\To\LoanAdministration
```
Replace the path above with wherever the program folder is stored on your machine.

**Step 3 — Install required packages:**
```powershell
python -m pip install -r requirements.txt
```
This installs all the libraries the program needs. You only need to run this once (or again if the program is updated). You should see a list of packages being installed, ending with `Successfully installed ...`.

> **Why `python -m pip` instead of just `pip`?** On Windows, using `python -m pip` ensures the packages are installed for the exact same Python version the program will use. Either form works, but this one is safer.

---

## Before You Start

**Opening PowerShell:**
1. Press `Windows + R`, type `powershell`, press Enter
2. Navigate to the program folder:
```powershell
cd C:\Path\To\LoanAdministration
```
Replace the path above with wherever the program folder is stored on your machine.

**Every command starts with:**
```powershell
python cli.py
```

**Dates are always entered as:** `YYYY-MM-DD` (e.g. `2025-02-01` for February 1, 2025)

**Percentages are always entered as numbers** (e.g. `2.5` for 2.5%, not `0.025`)

**Dollar amounts are always entered without commas or dollar signs** (e.g. `1000000` for $1,000,000)

**Descriptions with dollar amounts:** Use single quotes around descriptions that contain a `$` sign to avoid PowerShell treating it as a variable:
```powershell
--description 'Prepayment fee on $100,000 balance'
```

---

## SECTION 1 — Setting Up a New Loan

### Step 1 — Create the Loan (Draft)

Creates the loan in the system. It starts as a **Draft** — you can fix mistakes freely before activating it.

```powershell
python cli.py create `
  --loan-id LOAN-001 `
  --loan-name "Acme Credit Facility" `
  --borrower "Acme Industries LLC" `
  --principal 1000000 `
  --margin 2.5 `
  --origination-date 2025-02-01 `
  --maturity-date 2025-09-30 `
  --floor 0.5 `
  --pik-rate 2.0 `
  --interest-prepayment 14000
```

| Field | What to enter | Example |
|---|---|---|
| `--loan-id` | Your internal loan code — no spaces | `LOAN-001` |
| `--loan-name` | Full display name for reports | `"Acme Credit Facility"` |
| `--borrower` | Borrower's legal name | `"Acme Industries LLC"` |
| `--principal` | Loan amount, no commas | `1000000` |
| `--margin` | Spread over SOFR in % | `2.5` |
| `--origination-date` | First day of loan | `2025-02-01` |
| `--maturity-date` | Last day of loan | `2025-09-30` |
| `--floor` | *(optional)* Minimum SOFR rate in % | `0.5` |
| `--ceiling` | *(optional)* Maximum SOFR rate in % | `8.0` |
| `--pik-rate` | *(optional)* PIK rate in % if loan allows PIK | `2.0` |
| `--interest-prepayment` | *(optional)* Interest collected at closing | `14000` |

> **What you'll see:** Confirmation the loan was saved as DRAFT and how many interest periods were created.

---

### Step 2 — Add Investors

Add each investor's ownership percentage. All investors must be added before you can generate reports. Ownership percentages across all investors must total exactly **100%**.

```powershell
python cli.py add-investor `
  --loan-id LOAN-001 `
  --investor-id INV-001 `
  --investor-name "Apex Capital Fund" `
  --investor-short-name Apex `
  --ownership-pct 60 `
  --effective-date 2025-02-01
```

| Field | What to enter | Example |
|---|---|---|
| `--loan-id` | Same loan ID used in Step 1 | `LOAN-001` |
| `--investor-id` | Your internal investor code — no spaces | `INV-001` |
| `--investor-name` | Investor's full legal name | `"Apex Capital Fund"` |
| `--investor-short-name` | Short name used on reports — no spaces | `Apex` |
| `--ownership-pct` | Their ownership percentage | `60` |
| `--effective-date` | Date ownership begins — usually origination date | `2025-02-01` |

Repeat this command for each investor, changing the investor details and percentage each time.

---

### Step 3 — Add SOFR Rates

The system needs the 1-Month Term SOFR rate for each interest period. Rates are set **2 business days before** the start of each period (this is the standard reset date convention).

```powershell
python cli.py add-rate 2025-01-30 5.00
```

| Field | What to enter | Example |
|---|---|---|
| First value (date) | Reset date in YYYY-MM-DD | `2025-01-30` |
| Second value (rate) | SOFR rate as a percentage | `5.00` |

Run this command once for each period. If you need to correct a rate you already entered, run the same command again with the correct rate — it will replace the old one.

> **Where to find reset dates:** Run `python cli.py check-periods LOAN-001` after creating the loan — it will show you exactly which dates need rates.

---

### Step 4 — Activate the Loan

Once the loan terms and investors are confirmed, activate it. **This locks the terms.** After activation, any changes require a formal amendment (see Section 3).

```powershell
python cli.py activate-loan --loan-id LOAN-001
```

---

### Step 5 — Verify Everything is Ready

Check that all periods have SOFR rates and are ready for reporting:

```powershell
python cli.py check-periods LOAN-001
```

> **What you'll see:** A table of all periods. Each row should show **Ready** in the Status column. If any show **Missing SOFR**, go back and add the rate for that reset date using Step 3.

---

### Step 6 — Generate the Interest Schedule

Produces a full schedule showing interest amounts, cash due, and principal balance for every period. Also exports to a CSV file and text file in the `output/` folder.

```powershell
python cli.py generate-schedule --loan-id LOAN-001
```

Review the schedule carefully before proceeding to ensure all figures match the loan agreement.

---

## SECTION 2 — Monthly Period Processing

At the end of each interest period, follow these steps in order.

---

### Step A — Record Any PIK Election *(if loan has PIK feature)*

If the borrower has a PIK option, you must record whether they elected PIK or cash **before** generating reports.

**Borrower elected PIK** (interest capitalizes to balance):
```powershell
python cli.py add-pik LOAN-001 3 True
```

**Borrower elected cash** (normal interest payment):
```powershell
python cli.py add-pik LOAN-001 3 False
```

Replace `3` with the period number you are processing.

> **Note:** PIK cannot be elected if the loan still has a prepaid interest balance remaining.

---

### Step B — Record Any Principal Prepayment *(if applicable)*

If the borrower made a partial principal payment during the period, record it. Use the actual date the funds were received.

```powershell
python cli.py add-payment `
  --loan-id LOAN-001 `
  --date 2025-07-15 `
  --amount 100000 `
  --type principal_prepayment `
  --notes "Partial prepayment July 2025"
```

> **Important:** After recording a prepayment, run `generate-schedule` again (Step 6 above) to see the updated interest figures for remaining periods before recording the interest payment.

---

### Step C — Record Any Fees *(if applicable)*

If any fees were charged during the period, record each one separately.

```powershell
python cli.py add-fee `
  --loan-id LOAN-001 `
  --date 2025-07-15 `
  --type prepayment_fee `
  --amount 1000 `
  --period 6 `
  --description 'Prepayment fee on $100,000 partial prepayment'
```

| Field | What to enter | Example |
|---|---|---|
| `--date` | Date the fee was incurred | `2025-07-15` |
| `--type` | Fee type — see table below | `prepayment_fee` |
| `--amount` | Fee amount, no commas | `1000` |
| `--period` | *(optional)* Period number this fee belongs to | `6` |
| `--description` | *(optional)* Brief description | `'Prepayment fee...'` |

**Available fee types:**

| Fee Type | When to Use |
|---|---|
| `prepayment_fee` | Flat penalty fee charged on a principal prepayment |
| `prepayment_interest` | Makewhole / yield-maintenance interest calculated outside the system |
| `amendment_fee` | Fee charged when loan terms are amended |
| `exit_fee` | Fee charged when an investor exits their position |
| `waiver_fee` | Fee charged when a covenant waiver is granted |
| `default_interest` | Additional penalty interest above the contract rate |
| `other` | Any other fee not covered above |

> **Fees and PIK:** By default all fees are collected in cash. If a fee is to be capitalized (added to the balance), add `--cash-or-pik pik` to the command.

---

### Step D — Record the Interest Payment

Once you know the final cash interest amount due (from the schedule), record the payment when funds are received.

```powershell
python cli.py add-payment `
  --loan-id LOAN-001 `
  --date 2025-04-30 `
  --amount 4333.33 `
  --type interest `
  --period 3 `
  --notes "Period 3 cash interest"
```

| Field | What to enter | Example |
|---|---|---|
| `--date` | Date funds were received | `2025-04-30` |
| `--amount` | Exact amount received | `4333.33` |
| `--type` | Always `interest` for interest payments | `interest` |
| `--period` | Period number this payment covers | `3` |
| `--notes` | *(optional)* Brief note | `"Period 3 cash interest"` |

> **Periods fully covered by prepaid interest:** If the schedule shows $0.00 cash due (prepaid interest covers it), skip this step — no payment record is needed.

---

### Step E — Generate Investor Reports

Generates a text statement and PDF for every investor. Run this after all payments and fees for the period are recorded.

```powershell
python cli.py generate-period-reports --loan-id LOAN-001 --period 3
```

Reports are saved to:
- `output\investor_reports\` — text files
- `output\investor_reports_pdf\` — PDF files

> **If reports already exist** for this period and you need to regenerate them after a correction, add `--force`:
```powershell
python cli.py generate-period-reports --loan-id LOAN-001 --period 3 --force
```

> **Investors with 0% ownership** for the entire period are automatically skipped — no report generated.

---

## SECTION 3 — Investor Ownership Changes

When an investor's ownership percentage changes mid-loan (new investor joins, existing investor exits, or percentages are redistributed), record the new ownership for **every investor** with the new effective date — even those whose percentage did not change.

```powershell
python cli.py add-investor `
  --loan-id LOAN-001 `
  --investor-id INV-001 `
  --investor-name "Apex Capital Fund" `
  --investor-short-name Apex `
  --ownership-pct 75 `
  --effective-date 2025-07-15
```

Repeat for every investor with their updated (or unchanged) percentage and the same effective date. All percentages must still total 100%.

> **Exiting investor:** Set their `--ownership-pct` to `0`. They will still receive a final statement for the portion of the period they held ownership.

---

## SECTION 4 — Amending Loan Terms

After a loan is activated, any change to the terms (margin, maturity date, etc.) must be formally recorded as an amendment. This creates a new version and permanently logs the change.

```powershell
python cli.py amend-loan `
  --loan-id LOAN-001 `
  --maturity-date 2025-12-31 `
  --reason "Amendment No. 1 - Maturity extension per agreement dated 2025-06-01" `
  --changed-by "Jane Smith"
```

| Field | What to enter |
|---|---|
| `--loan-id` | Loan ID |
| *(changed fields only)* | Only include the fields that are actually changing |
| `--reason` | **Required** — brief description of what changed and why |
| `--changed-by` | *(optional)* Your name or initials for the audit trail |

> After amending, run `generate-schedule` again to see the updated schedule with the new terms.

---

## SECTION 5 — Final Loan Payoff

### Step 1 — Record Final Interest Payment

```powershell
python cli.py add-payment `
  --loan-id LOAN-001 `
  --date 2025-09-30 `
  --amount 4502.36 `
  --type interest `
  --period 8 `
  --notes "Final period interest payment"
```

### Step 2 — Record Final Principal Repayment

```powershell
python cli.py add-payment `
  --loan-id LOAN-001 `
  --date 2025-09-30 `
  --amount 701666.67 `
  --type principal_prepayment `
  --notes "Final principal repayment at maturity"
```

### Step 3 — Generate Final Period Reports

```powershell
python cli.py generate-period-reports --loan-id LOAN-001 --period 8
```

### Step 4 — Close the Loan

```powershell
python cli.py close-loan --loan-id LOAN-001
```

### Step 5 — Generate Audit Report

Produces a comprehensive Excel workbook covering the full loan life cycle.

```powershell
python cli.py generate-audit-report --loan-id LOAN-001
```

Saved to: `output\audit_reports\`

---

## SECTION 6 — Looking Up Information

### View all loans in the system
```powershell
python cli.py list-loans
```

### View loan amendment history
```powershell
python cli.py loan-history LOAN-001
```

### View all SOFR rates entered
```powershell
python cli.py list-rates
```

### View all investors on a loan
```powershell
python cli.py list-investors LOAN-001
```

View ownership as of a specific date:
```powershell
python cli.py list-investors LOAN-001 --date 2025-07-15
```

### View all payments recorded
```powershell
python cli.py list-payments LOAN-001
```

### View all fees recorded
```powershell
python cli.py list-fees LOAN-001
```

### Regenerate all period reports at once
```powershell
python cli.py generate-all-period-reports --loan-id LOAN-001
```

---

## SECTION 7 — Correcting Mistakes

### Correcting a DRAFT loan (before activation)

If you made a mistake in the loan terms before activating, use `correct-loan`. Only include the fields you want to change:

```powershell
python cli.py correct-loan `
  --loan-id LOAN-001 `
  --margin 3.0 `
  --reason "Corrected margin from 2.5% to 3.0%"
```

### Correcting a SOFR rate

Simply re-enter the rate — the system will replace the old value:
```powershell
python cli.py add-rate 2025-04-29 5.25
```

### Correcting a payment or fee amount

Payments and fees cannot be edited once recorded. Contact your system administrator — the CSV files in the `data\` folder can be corrected directly if needed, but this should be done carefully and with a backup.

### Regenerating reports after a correction

If you corrected something and need to regenerate reports for a period that already has reports, add `--force`:
```powershell
python cli.py generate-period-reports --loan-id LOAN-001 --period 4 --force
```

---

## SECTION 8 — Output Files

| File Location | Contents |
|---|---|
| `output\investor_reports\` | Text statements (.txt) — one per investor per period |
| `output\investor_reports_pdf\` | PDF statements — one per investor per period |
| `output\audit_reports\` | Excel audit workbook — full loan life cycle |
| `output\LOAN-001_schedule.csv` | Interest schedule spreadsheet |
| `output\LOAN-001_schedule.txt` | Interest schedule plain text |

---

## SECTION 9 — Quick Reference Card

| Task | Command |
|---|---|
| Create loan | `python cli.py create --loan-id ... --borrower ... --principal ... --margin ... --origination-date ... --maturity-date ...` |
| Add investor | `python cli.py add-investor --loan-id ... --investor-id ... --investor-name ... --investor-short-name ... --ownership-pct ... --effective-date ...` |
| Add SOFR rate | `python cli.py add-rate DATE RATE` |
| List SOFR rates | `python cli.py list-rates` |
| Activate loan | `python cli.py activate-loan --loan-id ...` |
| Check periods | `python cli.py check-periods LOAN-ID` |
| Generate schedule | `python cli.py generate-schedule --loan-id ...` |
| Record PIK election | `python cli.py add-pik LOAN-ID PERIOD True` or `False` |
| Record payment | `python cli.py add-payment --loan-id ... --date ... --amount ... --type interest --period ...` |
| Record prepayment | `python cli.py add-payment --loan-id ... --date ... --amount ... --type principal_prepayment` |
| Record fee | `python cli.py add-fee --loan-id ... --date ... --type ... --amount ...` |
| Generate period reports | `python cli.py generate-period-reports --loan-id ... --period ...` |
| Amend loan | `python cli.py amend-loan --loan-id ... --reason "..." [changed fields]` |
| Close loan | `python cli.py close-loan --loan-id ...` |
| Audit report | `python cli.py generate-audit-report --loan-id ...` |
| List loans | `python cli.py list-loans` |
| Loan history | `python cli.py loan-history LOAN-ID` |
| List payments | `python cli.py list-payments LOAN-ID` |
| List fees | `python cli.py list-fees LOAN-ID` |
| List investors | `python cli.py list-investors LOAN-ID` |

---

## SECTION 10 — Common Errors and What They Mean

| Error message | What it means | What to do |
|---|---|---|
| `Loan 'LOAN-001' not found` | The loan ID doesn't exist | Check spelling — use `list-loans` to see all loan IDs |
| `Missing X SOFR rates` | Some periods don't have SOFR rates yet | Run `check-periods` to see which dates need rates, then add them |
| `Ownership percentages must sum to 100%` | Investors don't add up to 100% | Check all investor percentages and correct |
| `Use --force to overwrite` | Reports already exist for this period | Add `--force` to the generate command |
| `Terms are locked` | Trying to correct an active loan | Use `amend-loan` instead of `correct-loan` |
| `PIK election ignored due to prepaid balance` | PIK elected but prepaid interest not yet exhausted | This is expected — PIK cannot be elected while prepaid interest remains |
