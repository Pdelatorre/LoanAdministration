# Loan Administration System — Complete Walkthrough

All commands are run from the `LoanAdministration_claude/` folder in your terminal.

This walkthrough demonstrates a complete 8-period floating-rate loan life cycle, including:
- Interest prepayment at close
- PIK election (interest capitalization)
- Mid-period principal prepayment with fee
- Mid-period investor ownership change (investor exit)
- Second mid-period prepayment (different period)
- Final principal repayment at maturity
- Business-day period end convention

---

## Loan Terms (WALKTHRU-001)

| Field | Value |
|---|---|
| Loan ID | WALKTHRU-001 |
| Borrower | Acme Industries LLC |
| Loan Name | Acme Credit Facility |
| Principal | $1,000,000.00 |
| Margin | 2.50% |
| Origination | Feb 1, 2025 |
| Maturity | Sep 30, 2025 |
| SOFR Floor | 0.50% |
| PIK Rate | 2.00% |
| Interest Prepaid | $14,000.00 |
| Convention | Last Business Day |
| Periods | 8 |

**Investors (from Feb 1):** Apex Capital Fund 60%, Bluewater Credit LP 25%, Crestline Partners 15%
**Investor Change (Jul 15):** Crestline exits (0%), Apex increases to 75%, Bluewater stays 25%

---

## Part 1 — Set Up the Loan

### Step 1a — Create the Loan (Draft)

```bash
python cli.py create \
  --loan-id WALKTHRU-001 \
  --loan-name "Acme Credit Facility" \
  --borrower "Acme Industries LLC" \
  --principal 1000000 \
  --margin 2.5 \
  --origination-date 2025-02-01 \
  --maturity-date 2025-09-30 \
  --floor 0.5 \
  --pik-rate 2.0 \
  --interest-prepayment 14000
```

**What you'll see:**
```
[DRAFT] Loan saved: WALKTHRU-001
   Borrower : Acme Industries LLC
   Principal: $1,000,000.00
   Periods  : 8
   Status   : DRAFT  (terms may still be corrected freely)
   Prepaid interest: $14,000.00
   PIK Rate: 2.00%

   Missing 7 SOFR rates — schedule not generated yet.
```

> The loan is created as a **Draft**. Terms can still be corrected freely before activation.
> Period count is 8 because Feb 1–Sep 30 spans 8 calendar months using last-business-day convention.

---

### Step 1b — Add Investors

```bash
python cli.py add-investor \
  --loan-id WALKTHRU-001 \
  --investor-id INV-APEX \
  --investor-name "Apex Capital Fund" \
  --investor-short-name Apex \
  --ownership-pct 60 \
  --effective-date 2025-02-01

python cli.py add-investor \
  --loan-id WALKTHRU-001 \
  --investor-id INV-BLUE \
  --investor-name "Bluewater Credit LP" \
  --investor-short-name Bluewater \
  --ownership-pct 25 \
  --effective-date 2025-02-01

python cli.py add-investor \
  --loan-id WALKTHRU-001 \
  --investor-id INV-CREST \
  --investor-name "Crestline Partners" \
  --investor-short-name Crestline \
  --ownership-pct 15 \
  --effective-date 2025-02-01
```

> Ownership percentages must sum to exactly 100% before any period report can be generated.

---

### Step 1c — Add SOFR Rates

SOFR reset dates are T-2 business days before the first day of each period.

| Period | Start | SOFR Reset Date | Rate |
|---|---|---|---|
| 1 | Feb 1 | Jan 30 | 5.00% |
| 2 | Mar 1 | Feb 27 | 5.00% |
| 3 | Apr 1 | Mar 28 | 4.75% |
| 4 | May 1 | Apr 29 | 5.33% |
| 5 | Jun 1 | May 29 | 5.31% |
| 6 | Jul 1 | Jun 27 | 5.28% |
| 7 | Aug 1 | Jul 30 | 5.25% |
| 8 | Sep 1 | Aug 28 | 5.20% |

```bash
python cli.py add-rate 2025-01-30 5.00
python cli.py add-rate 2025-02-27 5.00
python cli.py add-rate 2025-03-28 4.75
python cli.py add-rate 2025-04-29 5.33
python cli.py add-rate 2025-05-29 5.31
python cli.py add-rate 2025-06-27 5.28
python cli.py add-rate 2025-07-30 5.25
python cli.py add-rate 2025-08-28 5.20
```

> SOFR rates are stored globally (not per-loan). A rate only needs to be entered once even if multiple loans share a reset date.

---

### Step 1d — Activate the Loan

```bash
python cli.py activate-loan --loan-id WALKTHRU-001
```

**What you'll see:**
```
[ACTIVE] Loan 'WALKTHRU-001' is now active.
   Terms are locked. Use 'amend-loan' to make documented changes.
```

> After activation, terms are locked. Use `amend-loan` for any documented changes (creates a new version).

---

### Step 1e — Verify All Periods

```bash
python cli.py check-periods WALKTHRU-001
```

**Expected output:**
```
Period Status — WALKTHRU-001  (Acme Industries LLC)
Status: ACTIVE   Version: 2   Total Periods: 8

Period   Start Date   End Date     SOFR Rate    Status
1        2025-02-01   2025-02-28   5.0000%      Ready
2        2025-03-01   2025-03-31   5.0000%      Ready
3        2025-04-01   2025-04-30   4.7500%      Ready
4        2025-05-01   2025-05-30   5.3300%      Ready
5        2025-06-01   2025-06-30   5.3100%      Ready
6        2025-07-01   2025-07-31   5.2800%      Ready
7        2025-08-01   2025-08-29   5.2500%      Ready
8        2025-09-01   2025-09-30   5.2000%      Ready

8 of 8 periods ready for reporting.
```

> All periods show **Ready** — all SOFR rates present, all investor ownership records in place.
> Note Period 7 ends **Aug 29** (last business day of August — Aug 30 is Saturday, Aug 31 is Sunday).

---

### Step 1f — Generate Full Interest Schedule

```bash
python cli.py generate-schedule --loan-id WALKTHRU-001
```

**Expected schedule (base, before any payments or PIK):**
```
Per  Start        End          SOFR  Eff Rate     Interest    Prepaid    PIK   Cash Due    Prin End
1    2025-02-01   2025-02-28   5.00%  7.50%  $  5,833.33 $5,833.33   —  $    0.00  $1,000,000.00
2    2025-03-01   2025-03-31   5.00%  7.50%  $  6,458.33 $6,458.33   —  $    0.00  $1,000,000.00
3    2025-04-01   2025-04-30   4.75%  7.25%  $  6,041.67 $1,708.34   —  $4,333.33  $1,000,000.00
4    2025-05-01   2025-05-30   5.33%  7.83%  $  6,525.00 $    0.00   —  $6,525.00  $1,000,000.00
5    2025-06-01   2025-06-30   5.31%  7.81%  $  6,508.33 $    0.00   —  $6,508.33  $1,000,000.00
6    2025-07-01   2025-07-31   5.28%  7.78%  $  6,710.61 $    0.00   —  $6,710.61  $1,000,000.00
7    2025-08-01   2025-08-29   5.25%  7.75%  $  6,243.06 $    0.00   —  $6,243.06  $1,000,000.00
8    2025-09-01   2025-09-30   5.20%  7.70%  $  6,416.67 $    0.00   —  $6,416.67  $1,000,000.00
```

> Interest = Principal × Effective Rate / 360 × Days.
> The prepaid interest column shows how much of each period's interest is covered by the $14,000 prepayment.
> P1 and P2 fully covered; P3 partially covered (remaining $1,708.34 applied, $4,333.33 cash due).

---

## Part 2 — Period-by-Period Processing

### Period 1 — February 2025 (Feb 1–Feb 28)

**Interest:** $5,833.33 = $1,000,000 × 7.50% / 360 × 28 days
**Covered by prepaid interest:** $5,833.33 (remaining prepaid: $8,166.67)
**Cash due from borrower:** $0.00
**No payment to record.**

```bash
python cli.py generate-period-reports --loan-id WALKTHRU-001 --period 1
```

**Output:** 3 text + 3 PDF investor statements (Apex, Bluewater, Crestline)

---

### Period 2 — March 2025 (Mar 1–Mar 31)

**Interest:** $6,458.33 = $1,000,000 × 7.50% / 360 × 31 days
**Covered by prepaid interest:** $6,458.33 (remaining prepaid: $1,708.34)
**Cash due from borrower:** $0.00
**No payment to record.**

```bash
python cli.py generate-period-reports --loan-id WALKTHRU-001 --period 2
```

---

### Period 3 — April 2025 (Apr 1–Apr 30)

**Interest:** $6,041.67 = $1,000,000 × 7.25% / 360 × 30 days
**Covered by remaining prepaid:** $1,708.34 (prepaid fully exhausted)
**Cash due from borrower:** $4,333.33

```bash
python cli.py add-payment \
  --loan-id WALKTHRU-001 \
  --date 2025-04-30 \
  --amount 4333.33 \
  --type interest \
  --period 3 \
  --notes "Cash interest after prepaid interest exhausted"
```

```bash
python cli.py generate-period-reports --loan-id WALKTHRU-001 --period 3
```

---

### Period 4 — May 2025 (May 1–May 30) — **SOFR Floor + Amendment Fee**

> Note: Period 4 ends May 30 — last business day of May (May 30 is a Friday; May 31 is Saturday).

Two events this period:
1. SOFR drops to **0.25%** — below the 0.50% floor, so the floor rate applies
2. A **$2,500 amendment fee** is collected on May 15 (maturity extension / covenant modification)

**Interest calculation (floor applied):**
- SOFR reset date Apr 29: 0.25% — below 0.50% floor → floor rate used
- Effective rate: 0.50% (floor) + 2.50% (margin) = **3.00%**
- Interest: $1,000,000 × 3.00% / 360 × 30 days = **$2,500.00**
- Without floor it would have been: 0.25% + 2.50% = 2.75% → $2,291.67 (floor saves $208.33)

**Step 4a — Update SOFR rate to 0.25% (below floor):**

```bash
python cli.py add-rate 2025-04-29 0.25
```

**Step 4b — Record amendment fee (May 15):**

```bash
python cli.py add-fee \
  --loan-id WALKTHRU-001 \
  --date 2025-05-15 \
  --type amendment_fee \
  --amount 2500 \
  --period 4 \
  --description "Amendment fee — maturity extension and covenant modification"
```

**Step 4c — Record PIK opt-out** (borrower elects cash, not PIK):

```bash
python cli.py add-pik WALKTHRU-001 4 False
```

**Step 4d — Record interest payment:**

```bash
python cli.py add-payment \
  --loan-id WALKTHRU-001 \
  --date 2025-05-30 \
  --amount 2500.00 \
  --type interest \
  --period 4 \
  --notes "Period 4 cash interest (SOFR floor applied at 0.50%)"
```

**Step 4e — Generate reports:**

```bash
python cli.py generate-period-reports --loan-id WALKTHRU-001 --period 4
```

**What the investor report shows:**
- SOFR: 0.25% → **Effective Rate: 3.00%** (floor applied, margin added)
- Interest income at 60% (Apex): $1,500.00
- Amendment Fee (May 15) at 60%: $1,500.00
- **Total Income Earned: $3,000.00**

> The amendment fee is allocated to investors based on their ownership percentage **on the fee date** (May 15 → same ownership as period start: Apex 60%, Bluewater 25%, Crestline 15%). The fee appears inline in the Income Summary section of each investor's report.

---

### Period 5 — June 2025 (Jun 1–Jun 30) — **PIK Election**

**Interest (full period):** $6,508.33 = $1,000,000 × 7.81% / 360 × 30 days
**PIK portion (2.00%):** $1,666.67 = $1,000,000 × 2.00% / 360 × 30 days
**Cash portion (5.81%):** $4,841.66
**Principal after PIK:** $1,001,666.67 (PIK capitalizes to balance)

Elect PIK for Period 5:

```bash
python cli.py add-pik WALKTHRU-001 5 True
```

Record cash interest payment:

```bash
python cli.py add-payment \
  --loan-id WALKTHRU-001 \
  --date 2025-06-30 \
  --amount 4841.66 \
  --type interest \
  --period 5 \
  --notes "Period 5 cash interest (PIK elected, $1,666.67 capitalized)"
```

```bash
python cli.py generate-period-reports --loan-id WALKTHRU-001 --period 5
```

> Investor reports for Period 5 show both Cash Interest and PIK Interest (capitalized to balance) separately in the Income Summary section.

---

### Period 6 — July 2025 (Jul 1–Jul 31) — **Ownership Change + Prepayment + Fee**

Three events occur mid-period on **July 15, 2025**:
1. Crestline Partners exits (ownership → 0%)
2. Apex Capital Fund increases to 75%
3. $100,000 principal prepayment
4. $1,000 prepayment fee

**Interest calculation (two segments):**
- Seg 1 (Jul 1–14, 14 days): $1,001,666.67 × 7.78% / 360 × 14 = $3,012.47
- Seg 2 (Jul 15–31, 17 days): $901,666.67 × 7.78% / 360 × 17 = $3,352.36
- **Total P6 interest: $6,364.83**
- **Ending principal: $901,666.67**

**Step 6a — Record investor ownership change:**

```bash
python cli.py add-investor \
  --loan-id WALKTHRU-001 \
  --investor-id INV-APEX \
  --investor-name "Apex Capital Fund" \
  --investor-short-name Apex \
  --ownership-pct 75 \
  --effective-date 2025-07-15

python cli.py add-investor \
  --loan-id WALKTHRU-001 \
  --investor-id INV-BLUE \
  --investor-name "Bluewater Credit LP" \
  --investor-short-name Bluewater \
  --ownership-pct 25 \
  --effective-date 2025-07-15

python cli.py add-investor \
  --loan-id WALKTHRU-001 \
  --investor-id INV-CREST \
  --investor-name "Crestline Partners" \
  --investor-short-name Crestline \
  --ownership-pct 0 \
  --effective-date 2025-07-15
```

**Step 6b — Record $100,000 principal prepayment:**

```bash
python cli.py add-payment \
  --loan-id WALKTHRU-001 \
  --date 2025-07-15 \
  --amount 100000 \
  --type principal_prepayment \
  --notes "Partial prepayment Jul 2025"
```

**Step 6c — Record $1,000 prepayment fee:**

```bash
python cli.py add-fee \
  --loan-id WALKTHRU-001 \
  --date 2025-07-15 \
  --type prepayment_fee \
  --amount 1000 \
  --period 6 \
  --description "Prepayment fee on $100,000 partial prepayment"
```

**Step 6d — Regenerate schedule** (to see updated interest reflecting mid-period prepayment):

```bash
python cli.py generate-schedule --loan-id WALKTHRU-001
```

**Step 6e — Record Period 6 interest payment:**

```bash
python cli.py add-payment \
  --loan-id WALKTHRU-001 \
  --date 2025-07-31 \
  --amount 6364.83 \
  --type interest \
  --period 6 \
  --notes "Period 6 cash interest"
```

**Step 6f — Generate reports:**

```bash
python cli.py generate-period-reports --loan-id WALKTHRU-001 --period 6
```

**Output:** 3 investor statements (Apex, Bluewater, Crestline)

**Crestline report shows:**
- Single segment: Jul 1–14 @ 15% → $431.17 interest
- Principal balance: $0 (Crestline holds no allocated principal)
- Exit statement — final report for Crestline

**Apex report shows:**
- Two segments: Jul 1–14 @ 60% ($1,724.66) and Jul 15–31 @ 75% ($2,617.79)
- Total interest: $4,342.45
- Principal prepayment: ($75,000.00) — Apex's 75% share of $100K prepayment (ownership on Jul 15)
- Prepayment fee allocation: $750.00 (75% of $1,000 — allocated at ownership on Jul 15)

---

### Period 7 — August 2025 (Aug 1–Aug 29) — **Second Mid-Period Prepayment**

> Period 7 ends **Aug 29** (Friday), not Aug 31 (Sunday). The system correctly applies the last-business-day convention.

Mid-period event on **August 15**: $200,000 principal prepayment.

**Interest calculation (two segments):**
- Seg 1 (Aug 1–14, 14 days): $901,666.67 × 7.75% / 360 × 14 = $2,717.59
- Seg 2 (Aug 15–29, 15 days): $701,666.67 × 7.75% / 360 × 15 = $2,308.79
- **Total P7 interest: $5,026.38**
- **Ending principal: $701,666.67**

**Step 7a — Record $200,000 prepayment:**

```bash
python cli.py add-payment \
  --loan-id WALKTHRU-001 \
  --date 2025-08-15 \
  --amount 200000 \
  --type principal_prepayment \
  --notes "Partial prepayment Aug 2025"
```

**Step 7b — Regenerate schedule** (to verify updated P7 and P8 interest):

```bash
python cli.py generate-schedule --loan-id WALKTHRU-001
```

Expected P7: Interest $5,026.38, Prin End $701,666.67
Expected P8: Interest $4,502.36, Prin End $701,666.67 (no further prepayment until maturity)

**Step 7c — Record Period 7 interest payment:**

```bash
python cli.py add-payment \
  --loan-id WALKTHRU-001 \
  --date 2025-08-29 \
  --amount 5026.38 \
  --type interest \
  --period 7 \
  --notes "Period 7 cash interest"
```

**Step 7d — Generate reports:**

```bash
python cli.py generate-period-reports --loan-id WALKTHRU-001 --period 7
```

**Output:** 2 investor statements only (Apex and Bluewater — Crestline skipped, 0% all period)

> The system automatically skips generating reports for investors with 0% ownership across all segments of the period.

---

### Period 8 — September 2025 (Sep 1–Sep 30) — **Final Payoff at Maturity**

**Interest:** $4,502.36 = $701,666.67 × 7.70% / 360 × 30 days
**Final principal repayment:** $701,666.67
**Total cash due at maturity:** $5,204.72 (interest $4,502.36 + principal $701,666.67)

**Step 8a — Record final interest payment:**

```bash
python cli.py add-payment \
  --loan-id WALKTHRU-001 \
  --date 2025-09-30 \
  --amount 4502.36 \
  --type interest \
  --period 8 \
  --notes "Period 8 final cash interest"
```

**Step 8b — Record final principal repayment:**

```bash
python cli.py add-payment \
  --loan-id WALKTHRU-001 \
  --date 2025-09-30 \
  --amount 701666.67 \
  --type principal_prepayment \
  --notes "Final principal repayment at maturity"
```

**Step 8c — Generate reports:**

```bash
python cli.py generate-period-reports --loan-id WALKTHRU-001 --period 8
```

**Output:** 2 investor statements (Apex and Bluewater)

---

## Part 3 — Closing the Loan

```bash
python cli.py close-loan --loan-id WALKTHRU-001
```

---

## Part 4 — Audit Report

```bash
python cli.py generate-audit-report --loan-id WALKTHRU-001
```

Generates an Excel workbook in `output/audit_reports/` with:
- Loan summary sheet
- Full interest schedule
- Payment history
- Fee detail

---

## Complete Payment Summary

| Payment ID | Date | Type | Period | Amount |
|---|---|---|---|---|
| PAY-001 | 2025-04-30 | interest | 3 | $4,333.33 |
| PAY-002 | 2025-05-30 | interest | 4 | $2,500.00 |
| PAY-003 | 2025-06-30 | interest | 5 | $4,841.66 |
| PAY-004 | 2025-07-15 | principal_prepayment | — | $100,000.00 |
| PAY-005 | 2025-07-31 | interest | 6 | $6,364.83 |
| PAY-006 | 2025-08-15 | principal_prepayment | — | $200,000.00 |
| PAY-007 | 2025-08-29 | interest | 7 | $5,026.38 |
| PAY-008 | 2025-09-30 | interest | 8 | $4,502.36 |
| PAY-009 | 2025-09-30 | principal_prepayment | — | $701,666.67 |

**Total Interest Paid:** $27,568.56
**Total Principal Repaid:** $1,001,666.67 (includes $1,666.67 PIK capitalization)

---

## Final Interest Schedule (with all prepayments and PIK)

```
Per  Start        End          SOFR  Eff Rate     Interest    Prepaid       PIK     Cash Due      Prin End
1    2025-02-01   2025-02-28   5.00%  7.50%  $  5,833.33 $5,833.33         —  $      0.00  $1,000,000.00
2    2025-03-01   2025-03-31   5.00%  7.50%  $  6,458.33 $6,458.33         —  $      0.00  $1,000,000.00
3    2025-04-01   2025-04-30   4.75%  7.25%  $  6,041.67 $1,708.34         —  $  4,333.33  $1,000,000.00
4    2025-05-01   2025-05-30   0.25%  3.00%  $  2,500.00 $    0.00         —  $  2,500.00  $1,000,000.00
5    2025-06-01   2025-06-30   5.31%  7.81%  $  6,508.33 $    0.00 $1,666.67  $  4,841.66  $1,001,666.67
6    2025-07-01   2025-07-31   5.28%  7.78%  $  6,364.83 $    0.00         —  $  6,364.83  $  901,666.67
7    2025-08-01   2025-08-29   5.25%  7.75%  $  5,026.38 $    0.00         —  $  5,026.38  $  701,666.67
8    2025-09-01   2025-09-30   5.20%  7.70%  $  4,502.36 $    0.00         —  $  4,502.36  $        0.00
```

---

## Key Concepts

### Interest Calculation
`Interest = Principal × (SOFR + Margin) / 360 × Days`

SOFR floor (0.50%) ensures effective SOFR never goes below 0.50% even if the benchmark falls lower.

### SOFR Reset Dates
Each period's rate is set T-2 business days before the first day of that period. If multiple loans share a reset date they use the same rate — rates are stored globally.

### PIK (Payment-in-Kind)
When PIK is elected for a period:
- The PIK portion (2.00% rate) capitalizes to the loan balance
- Only the cash portion is collected from the borrower
- All subsequent periods calculate interest on the increased balance

### Mid-Period Events (Prepayments / Ownership Changes)
When an event (prepayment or ownership change) occurs mid-period, the system automatically:
- Splits the interest period into segments at the event date
- Calculates interest on each segment separately (different principal amounts)
- Allocates interest to investors based on their ownership percentage during each segment

### Business Day Convention (`last_business_day`)
Period end dates always fall on the last business day of the calendar month. If a month end falls on a weekend or holiday, the period ends on the preceding business day. The maturity date caps the final period if it falls before that month's last business day.

### Investor Ownership Changes
- Each `add-investor` call with a new `--effective-date` adds a new ownership row
- The system uses each investor's ownership on a given date to calculate their share of interest and fees
- Investors with 0% ownership for the entire period are automatically skipped during report generation
- Investors who held ownership for part of a period (e.g., Crestline in Period 6) still receive a final exit statement

### Fee Allocation
Fees are allocated to investors based on their ownership percentage **on the fee date** (point-in-time). No pro-rating is applied for ownership changes that occurred before or after the fee date.

---

## Useful Commands Reference

| Command | Description |
|---|---|
| `python cli.py create ...` | Create new loan (Draft) |
| `python cli.py activate-loan --loan-id ID` | Activate loan (locks terms) |
| `python cli.py amend-loan --loan-id ID ...` | Amend active loan (new version) |
| `python cli.py close-loan --loan-id ID` | Close loan |
| `python cli.py check-periods LOAN_ID` | Check all period statuses and SOFR coverage |
| `python cli.py generate-schedule --loan-id ID` | Generate/export full interest schedule |
| `python cli.py add-rate DATE RATE` | Add SOFR rate (date: YYYY-MM-DD, rate: e.g. 5.25) |
| `python cli.py list-rates` | Show all SOFR rates |
| `python cli.py add-investor --loan-id ID ...` | Add/update investor ownership |
| `python cli.py list-investors LOAN_ID` | List investor records |
| `python cli.py add-pik LOAN_ID PERIOD True/False` | Record PIK election for a period |
| `python cli.py add-payment --loan-id ID ...` | Record a payment |
| `python cli.py list-payments LOAN_ID` | List all payments |
| `python cli.py add-fee --loan-id ID ...` | Record a fee |
| `python cli.py list-fees LOAN_ID` | List all fees |
| `python cli.py generate-period-reports --loan-id ID --period N` | Generate investor reports for one period |
| `python cli.py generate-all-period-reports --loan-id ID` | Regenerate all period reports |
| `python cli.py generate-audit-report --loan-id ID` | Generate Excel audit report |
| `python cli.py loan-history LOAN_ID` | Show loan version history |
| `python cli.py list-loans` | List all loans |
