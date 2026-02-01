"""
Loan Administration System Configuration

SETUP INSTRUCTIONS:
1. Run: pip install -r requirements.txt
2. Or run: bash setup.sh (recommended)
3. Update COMPANY_NAME below with your company information
4. Customize other settings as needed

Central location for all system-wide settings.
Modify these values to customize your reports and system behavior.
"""

# Company Information
COMPANY_NAME = "Your Company Name"  # ⚠️ UPDATE THIS
COMPANY_ADDRESS_LINE1 = "123 Main Street"
COMPANY_CITY_STATE_ZIP = "New York, NY 10001"
COMPANY_PHONE = "(555) 123-4567"
COMPANY_EMAIL = "info@yourcompany.com"

# Report Settings
DEFAULT_OUTPUT_DIR = "output"
INVESTOR_REPORTS_DIR = "output/investor_reports"
INVESTOR_REPORTS_PDF_DIR = "output/investor_reports_pdf"
AUDIT_REPORTS_DIR = "output/audit_reports"

# Data Storage
DATA_DIR = "data"
SOFR_RATES_FILE = "data/sofr_rates.csv"
INVESTORS_FILE = "data/investors.csv"
PAYMENTS_FILE = "data/payments.csv"

# Date Formats
DATE_FORMAT_DISPLAY = "%B %d, %Y"  # January 30, 2026
DATE_FORMAT_SHORT = "%m/%d/%Y"      # 01/30/2026
DATE_FORMAT_INPUT = "%Y-%m-%d"      # 2026-01-30

# Report Styling
REPORT_FONT_FAMILY = "'Helvetica', 'Arial', sans-serif"
REPORT_FONT_SIZE = "11px"
REPORT_HEADER_COLOR = "#333333"
REPORT_BORDER_COLOR = "#333333"

# Business Logic
SOFR_RESET_BUSINESS_DAYS = 2  # Days before period start to get SOFR rate
DEFAULT_SOFR_FLOOR = 0.0
DEFAULT_SOFR_CEILING = float('inf')

# System Settings
DEBUG_MODE = False
VERBOSE_OUTPUT = True