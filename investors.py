import csv
from datetime import datetime
from typing import List, Dict, Optional


def load_investors(loan_id: str, filepath: str = "data/investors.csv") -> List[Dict]:
    """
    Load all investor ownership records for a loan.
    
    Returns list of ownership records sorted by effective_date.
    Multiple records per investor represent ownership changes over time.
    
    Args:
        loan_id: The loan identifier
        filepath: Path to investors CSV file
    
    Returns:
        List of investor ownership records with effective dates
    """
    investors = []
    
    try:
        with open(filepath, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['loan_id'] == loan_id:
                    investors.append({
                        'loan_id': row['loan_id'],
                        'investor_id': row['investor_id'],
                        'investor_name': row['investor_name'],
                        'ownership_pct': float(row['ownership_pct']),
                        'effective_date': datetime.strptime(row['effective_date'], '%Y-%m-%d')
                    })
    except FileNotFoundError:
        return []
    
    # Sort by effective date
    investors.sort(key=lambda x: x['effective_date'])
    
    return investors


def get_ownership_for_period(
    loan_id: str,
    period_start: datetime,
    period_end: datetime,
    filepath: str = "data/investors.csv"
) -> List[Dict]:
    """
    Get ownership structure for a specific period, accounting for changes.
    
    Returns break periods if ownership changed during the period.
    
    Args:
        loan_id: The loan identifier
        period_start: Period start date
        period_end: Period end date
        filepath: Path to investors CSV
    
    Returns:
        List of ownership segments with start/end dates and investor allocations
        
    Example:
        Period: Jan 1-31
        Jan 16: Ownership change
        
        Returns:
        [
            {
                'start_date': Jan 1,
                'end_date': Jan 15,
                'days': 15,
                'investors': [
                    {'investor_id': 'INV-A', 'name': 'Investor A', 'ownership_pct': 40.0},
                    {'investor_id': 'INV-B', 'name': 'Investor B', 'ownership_pct': 60.0}
                ]
            },
            {
                'start_date': Jan 16,
                'end_date': Jan 31,
                'days': 16,
                'investors': [
                    {'investor_id': 'INV-A', 'name': 'Investor A', 'ownership_pct': 35.0},
                    {'investor_id': 'INV-B', 'name': 'Investor B', 'ownership_pct': 45.0},
                    {'investor_id': 'INV-C', 'name': 'Investor C', 'ownership_pct': 20.0}
                ]
            }
        ]
    """
    from datetime import timedelta
    
    all_investors = load_investors(loan_id, filepath)
    
    # Find all ownership changes within or affecting this period
    ownership_changes = []
    for inv in all_investors:
        if period_start <= inv['effective_date'] <= period_end:
            if inv['effective_date'] not in ownership_changes:
                ownership_changes.append(inv['effective_date'])
    
    ownership_changes.sort()
    
    # Build segments
    segments = []
    
    if not ownership_changes:
        # No changes during period - single segment
        investors_at_start = _get_investors_at_date(all_investors, period_start)
        segments.append({
            'start_date': period_start,
            'end_date': period_end,
            'days': (period_end - period_start).days + 1,
            'investors': investors_at_start
        })
    else:
        # Multiple segments due to ownership changes
        current_date = period_start
        
        for change_date in ownership_changes:
            # Segment from current_date to day before change
            if current_date < change_date:
                investors = _get_investors_at_date(all_investors, current_date)
                segments.append({
                    'start_date': current_date,
                    'end_date': change_date - timedelta(days=1),
                    'days': (change_date - current_date).days,
                    'investors': investors
                })
            
            current_date = change_date
        
        # Final segment from last change to period end
        investors = _get_investors_at_date(all_investors, current_date)
        segments.append({
            'start_date': current_date,
            'end_date': period_end,
            'days': (period_end - current_date).days + 1,
            'investors': investors
        })
    
    return segments


def _get_investors_at_date(all_investors: List[Dict], target_date: datetime) -> List[Dict]:
    """
    Get the ownership structure as of a specific date.
    
    Returns the most recent ownership record for each investor as of target_date.
    """
    # Group by investor_id
    investor_groups = {}
    for inv in all_investors:
        if inv['effective_date'] <= target_date:
            investor_id = inv['investor_id']
            if investor_id not in investor_groups:
                investor_groups[investor_id] = inv
            else:
                # Keep most recent
                if inv['effective_date'] > investor_groups[investor_id]['effective_date']:
                    investor_groups[investor_id] = inv
    
    # Return as list
    return [
        {
            'investor_id': inv['investor_id'],
            'investor_name': inv['investor_name'],
            'ownership_pct': inv['ownership_pct']
        }
        for inv in investor_groups.values()
    ]


def add_investor(
    loan_id: str,
    investor_id: str,
    investor_name: str,
    ownership_pct: float,
    effective_date: datetime,
    filepath: str = "data/investors.csv"
) -> None:
    """
    Add or update investor ownership record.
    
    Args:
        loan_id: The loan identifier
        investor_id: Unique investor identifier
        investor_name: Investor name
        ownership_pct: Ownership percentage (e.g., 40.0 for 40%)
        effective_date: When this ownership takes effect
        filepath: Path to investors CSV
    """
    import os
    
    # Create file with headers if doesn't exist
    if not os.path.exists(filepath):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['loan_id', 'investor_id', 'investor_name', 'ownership_pct', 'effective_date'])
    
    # Append new record
    with open(filepath, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            loan_id,
            investor_id,
            investor_name,
            f"{ownership_pct:.2f}",
            effective_date.strftime('%Y-%m-%d')
        ])
    
    print(f"✅ Investor ownership recorded: {investor_name} - {ownership_pct}% effective {effective_date.strftime('%Y-%m-%d')}")


def validate_ownership(
    loan_id: str,
    target_date: datetime,
    filepath: str = "data/investors.csv"
) -> Dict:
    """
    Validate that ownership percentages sum to 100% as of a date.
    
    Returns:
        {
            'valid': True/False,
            'total_pct': float,
            'investors': List[Dict]
        }
    """
    all_investors = load_investors(loan_id, filepath)
    investors_at_date = _get_investors_at_date(all_investors, target_date)
    
    total_pct = sum(inv['ownership_pct'] for inv in investors_at_date)
    
    return {
        'valid': abs(total_pct - 100.0) < 0.01,  # Allow small floating point difference
        'total_pct': total_pct,
        'investors': investors_at_date
    }