#!/bin/bash

echo "============================================"
echo "Loan Administration System Setup"
echo "============================================"

# Check Python version
echo ""
echo "🐍 Checking Python version..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "   Found Python $python_version"

# Check if Python version is 3.8+
major=$(echo $python_version | cut -d. -f1)
minor=$(echo $python_version | cut -d. -f2)

if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 8 ]); then
    echo "❌ Python 3.8+ required. Found Python $python_version"
    exit 1
fi

echo "✅ Python version compatible"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Create directory structure
echo ""
echo "📁 Creating directory structure..."
mkdir -p data
mkdir -p output/investor_reports
mkdir -p output/investor_reports_pdf
mkdir -p output/audit_reports

echo "✅ Directories created"

# Create SOFR rates file if it doesn't exist
if [ ! -f "data/sofr_rates.csv" ]; then
    echo ""
    echo "📊 Creating SOFR rates template..."
    echo "date,rate" > data/sofr_rates.csv
    echo "✅ Created data/sofr_rates.csv (add your rates here)"
else
    echo ""
    echo "✅ SOFR rates file already exists"
fi

# Verify critical files exist
echo ""
echo "🔍 Verifying installation..."

required_files=("config.py" "loan.py" "investors.py" "investor_reports.py" "investor_reports_pdf.py" "cli.py")
all_present=true

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file (missing)"
        all_present=false
    fi
done

if [ "$all_present" = false ]; then
    echo ""
    echo "❌ Some required files are missing"
    exit 1
fi

echo ""
echo "============================================"
echo "✅ Setup Complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Update company name in config.py:"
echo "     COMPANY_NAME = \"Your Company Name\""
echo ""
echo "  2. Add SOFR rates to data/sofr_rates.csv:"
echo "     date,rate"
echo "     2025-01-30,0.0455"
echo ""
echo "  3. Test the installation:"
echo "     python test_config.py"
echo ""
echo "  4. Try the demo workflow:"
echo "     bash demo_investor_workflow.sh"
echo ""
echo "For complete documentation, see README.md"
echo ""