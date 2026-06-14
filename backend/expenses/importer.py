import csv
import re
import datetime
from decimal import Decimal, InvalidOperation
from django.contrib.auth.models import User

# Constants
DEFAULT_EXCHANGE_RATE = Decimal('83.00')

def clean_amount(val):
    """Remove currency symbols, commas and return a clean decimal string or None."""
    if not val:
        return None
    cleaned = re.sub(r'[^\d\.\-]', '', str(val))
    return cleaned

def parse_date(date_str):
    """Try various date formats and return a date object or None."""
    if not date_str:
        return None
    date_str = date_str.strip()
    formats = [
        '%Y-%m-%d',
        '%d/%m/%Y',
        '%m/%d/%Y',
        '%d-%m-%Y',
        '%m-%d-%Y',
    ]
    for fmt in formats:
        try:
            return datetime.datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None

def find_user_match(name):
    """Find a matching user, ignoring casing and spaces."""
    if not name:
        return None
    name_clean = name.strip().lower()
    
    # Common typo maps
    typo_map = {
        'priyaa': 'priya',
        'rohann': 'rohan',
        'aesha': 'aisha',
        'mera': 'meera',
    }
    if name_clean in typo_map:
        name_clean = typo_map[name_clean]
        
    try:
        return User.objects.get(username__iexact=name_clean)
    except User.DoesNotExist:
        return None

def analyze_csv_row(row, idx, seen_rows, member_names):
    """Analyze a single CSV row and detect all anomalies."""
    anomalies = []
    
    raw_date = row.get('Date', '')
    raw_desc = row.get('Description', '')
    raw_amount = row.get('Amount', '')
    raw_paid_by = row.get('Paid By', '')
    raw_currency = row.get('Currency', 'INR')

    # 1. Date Format check
    parsed_date = parse_date(raw_date)
    is_date_anomaly = False
    if not parsed_date:
        anomalies.append({
            'type': 'INVALID_DATE',
            'severity': 'ERROR',
            'message': f"Date '{raw_date}' could not be parsed.",
            'column': 'Date',
            'suggested': 'Skip row or manually set date'
        })
    elif raw_date.strip() != parsed_date.strftime('%Y-%m-%d'):
        # If it parsed but the format is not YYYY-MM-DD
        anomalies.append({
            'type': 'INCONSISTENT_DATE_FORMAT',
            'severity': 'WARNING',
            'message': f"Date '{raw_date}' is not in YYYY-MM-DD format.",
            'column': 'Date',
            'suggested': f"Standardize to '{parsed_date.strftime('%Y-%m-%d')}'"
        })
        is_date_anomaly = True

    # 2. Amount Cleaning check
    cleaned_amount_str = clean_amount(raw_amount)
    amount_decimal = None
    if not cleaned_amount_str:
        anomalies.append({
            'type': 'INVALID_AMOUNT',
            'severity': 'ERROR',
            'message': f"Amount '{raw_amount}' is missing or invalid.",
            'column': 'Amount',
            'suggested': 'Skip row or set amount'
        })
    else:
        try:
            amount_decimal = Decimal(cleaned_amount_str)
            if re.search(r'[^\d\.\-]', str(raw_amount)):
                anomalies.append({
                    'type': 'MALFORMED_AMOUNT_TEXT',
                    'severity': 'WARNING',
                    'message': f"Amount '{raw_amount}' contains non-numeric characters.",
                    'column': 'Amount',
                    'suggested': f"Clean to {amount_decimal}"
                })
        except (InvalidOperation, ValueError):
            anomalies.append({
                'type': 'INVALID_AMOUNT',
                'severity': 'ERROR',
                'message': f"Amount '{raw_amount}' is not a valid number.",
                'column': 'Amount',
                'suggested': 'Skip row or set amount'
            })

    # 3. Negative Amount (Refund) check
    if amount_decimal is not None and amount_decimal < 0:
        anomalies.append({
            'type': 'NEGATIVE_AMOUNT',
            'severity': 'WARNING',
            'message': f"Amount {amount_decimal} is negative. This will be treated as a Refund (reversing debt).",
            'column': 'Amount',
            'suggested': 'Convert to refund splits'
        })

    # 4. Paid By User validation
    paid_by_user = find_user_match(raw_paid_by)
    if not paid_by_user:
        anomalies.append({
            'type': 'INVALID_PAYER',
            'severity': 'ERROR',
            'message': f"Payer '{raw_paid_by}' does not match any known user.",
            'column': 'Paid By',
            'suggested': 'Assign to a registered user'
        })
    elif raw_paid_by.strip() != paid_by_user.username:
        anomalies.append({
            'type': 'TYPO_IN_PAYER_NAME',
            'severity': 'WARNING',
            'message': f"Payer name '{raw_paid_by}' contains spelling/casing inconsistency.",
            'column': 'Paid By',
            'suggested': f"Correct spelling to '{paid_by_user.username}'"
        })

    # 5. Currency & USD check
    currency_code = raw_currency.strip().upper() if raw_currency else 'INR'
    if currency_code == 'USD' or '$' in str(raw_amount) or 'USD' in raw_desc.upper():
        currency_code = 'USD'
        anomalies.append({
            'type': 'FOREIGN_CURRENCY_USD',
            'severity': 'INFO',
            'message': "Expense in USD detected. Needs conversion to INR.",
            'column': 'Currency',
            'suggested': f"Multiply by standard exchange rate of {DEFAULT_EXCHANGE_RATE} INR/USD"
        })

    # 6. Settlement logic
    is_settlement = False
    desc_upper = raw_desc.upper()
    if 'SETTLE' in desc_upper or 'PAYBACK' in desc_upper or 'PAID BACK' in desc_upper or 'PAYMENT' in desc_upper:
        is_settlement = True
        anomalies.append({
            'type': 'SETTLEMENT_LOGGED_AS_EXPENSE',
            'severity': 'WARNING',
            'message': "This description indicates a settlement between roommates, not a shared expense.",
            'column': 'Description',
            'suggested': "Convert this record from an 'Expense' into a direct 'Payment' settlement"
        })

    # 7. Member Splits parsing
    splits = {}
    total_split_percentage = Decimal('0.00')
    split_type = 'EQUAL'
    has_percentage = False
    has_shares = False
    
    for member in member_names:
        val = row.get(member, '').strip()
        if not val or val == '0':
            continue
        
        # Check if percentage split
        if '%' in val:
            has_percentage = True
            try:
                pct = Decimal(val.replace('%', '')) / Decimal('100.00')
                splits[member] = pct
                total_split_percentage += pct
            except (InvalidOperation, ValueError):
                pass
        else:
            try:
                num = Decimal(val)
                if num > 0:
                    splits[member] = num
                    if num != 1:
                        has_shares = True
            except (InvalidOperation, ValueError):
                pass

    if has_percentage:
        split_type = 'PERCENT'
    elif has_shares:
        split_type = 'SHARE'
    else:
        split_type = 'EQUAL'

    # Validate split counts
    if amount_decimal is not None and not is_settlement:
        if not splits:
            anomalies.append({
                'type': 'EMPTY_SPLITS',
                'severity': 'ERROR',
                'message': "No roommates are selected in the split columns.",
                'column': 'Splits',
                'suggested': 'Select at least one roommate to share this expense'
            })
        elif len(splits) == 1 and paid_by_user and list(splits.keys())[0].lower() == paid_by_user.username.lower():
            anomalies.append({
                'type': 'SELF_ONLY_EXPENSE',
                'severity': 'WARNING',
                'message': "Only the payer is included in the split. This is a personal expense.",
                'column': 'Splits',
                'suggested': 'Flag as personal expense (ignore from group balances)'
            })

    # 8. Split Sum Mismatch
    if split_type == 'PERCENT' and total_split_percentage != Decimal('1.00') and splits:
        anomalies.append({
            'type': 'PERCENTAGE_SUM_MISMATCH',
            'severity': 'WARNING',
            'message': f"Split percentages sum to {total_split_percentage * 100}%, not 100%.",
            'column': 'Splits',
            'suggested': f"Normalize percentages to equal 100%"
        })

    # 9. Inactive members timing checks
    # Meera moved out March 31, 2026. Sam moved in April 15, 2026.
    if parsed_date:
        # Sam join checks
        sam_join_date = datetime.date(2026, 4, 15)
        if parsed_date < sam_join_date and 'sam' in [s.lower() for s in splits.keys()]:
            anomalies.append({
                'type': 'INACTIVE_MEMBER_SAM_MARCH',
                'severity': 'WARNING',
                'message': f"Sam is included in splits for date {parsed_date}, but he only moved in on April 15, 2026.",
                'column': 'Sam',
                'suggested': "Remove Sam from split and re-allocate share to other roommates"
            })
            
        # Meera leave checks
        meera_leave_date = datetime.date(2026, 3, 31)
        if parsed_date > meera_leave_date and 'meera' in [s.lower() for s in splits.keys()]:
            anomalies.append({
                'type': 'INACTIVE_MEMBER_MEERA_POST_MARCH',
                'severity': 'WARNING',
                'message': f"Meera is included in splits for date {parsed_date}, but she moved out on March 31, 2026.",
                'column': 'Meera',
                'suggested': "Remove Meera from split and re-allocate share to other roommates"
            })

    # 10. Exact Duplicate check
    row_signature = (parsed_date, raw_desc.strip(), amount_decimal, paid_by_user.username if paid_by_user else None)
    is_exact_dup = False
    if parsed_date and amount_decimal is not None and paid_by_user:
        if row_signature in seen_rows:
            is_exact_dup = True
            anomalies.append({
                'type': 'EXACT_DUPLICATE_ROW',
                'severity': 'WARNING',
                'message': "This row is an exact duplicate of a previous row.",
                'column': 'Row',
                'suggested': "Exclude this row from import"
            })
        else:
            seen_rows.add(row_signature)

    # 11. Conflicting Duplicate (same date, description, paid_by but different amount)
    is_conflict_dup = False
    if parsed_date and paid_by_user and not is_exact_dup:
        for prev in seen_rows:
            if prev[0] == parsed_date and prev[1] == raw_desc.strip() and prev[3] == paid_by_user.username and prev[2] != amount_decimal:
                is_conflict_dup = True
                anomalies.append({
                    'type': 'CONFLICTING_DUPLICATE_ROW',
                    'severity': 'WARNING',
                    'message': f"Conflicting record found: same date, payee, description, but amount is {prev[2]} in one and {amount_decimal} here.",
                    'column': 'Amount',
                    'suggested': "Keep original or override with this row"
                })
                break

    # Calculate default suggested values
    suggested_date = parsed_date.strftime('%Y-%m-%d') if parsed_date else raw_date
    
    suggested_amount = amount_decimal if amount_decimal is not None else Decimal('0.00')
    if currency_code == 'USD' and suggested_amount > 0:
        suggested_amount = suggested_amount * DEFAULT_EXCHANGE_RATE
        
    suggested_paid_by = paid_by_user.username if paid_by_user else raw_paid_by
    
    # Apply inactive member rules to suggested splits
    suggested_splits = {}
    for m in splits:
        m_lower = m.lower()
        if parsed_date:
            if m_lower == 'sam' and parsed_date < datetime.date(2026, 4, 15):
                continue
            if m_lower == 'meera' and parsed_date > datetime.date(2026, 3, 31):
                continue
        suggested_splits[m] = splits[m]

    # Suggest resolving split type percentages
    if split_type == 'PERCENT' and total_split_percentage != Decimal('1.00') and suggested_splits:
        # Re-normalize splits to sum to 100%
        sub_sum = sum(suggested_splits.values())
        if sub_sum > 0:
            suggested_splits = {m: (val / sub_sum).quantize(Decimal('0.0001')) for m, val in suggested_splits.items()}

    # Check if exact duplicate should be ignored by default
    default_exclude = is_exact_dup

    return {
        'row_index': idx,
        'original_row': {
            'Date': raw_date,
            'Description': raw_desc,
            'Amount': raw_amount,
            'Paid By': raw_paid_by,
            'Currency': raw_currency,
            'splits': {m: row.get(m, '') for m in member_names}
        },
        'anomalies': anomalies,
        'suggested_row': {
            'Date': suggested_date,
            'Description': raw_desc,
            'Amount': str(suggested_amount),
            'Paid By': suggested_paid_by,
            'Currency': 'INR',  # Converted to base
            'original_currency': currency_code,
            'original_amount': str(amount_decimal if amount_decimal is not None else Decimal('0.00')),
            'exchange_rate': str(DEFAULT_EXCHANGE_RATE) if currency_code == 'USD' else '1.00',
            'splits': {m: str(val) for m, val in suggested_splits.items()},
            'split_type': split_type,
            'is_settlement': is_settlement,
            'is_personal': len(suggested_splits) == 1 and paid_by_user and list(suggested_splits.keys())[0].lower() == paid_by_user.username.lower()
        },
        'exclude_by_default': default_exclude
    }

def process_csv_stream(file_stream):
    """Read a CSV file stream and return the full dry-run analysis."""
    # Ensure standard users exist so we can map them
    flatmates = ['aisha', 'rohan', 'priya', 'meera', 'sam', 'dev']
    for username in flatmates:
        User.objects.get_or_create(username=username, defaults={'email': f"{username}@flatmates.com"})

    decoded_file = file_stream.read().decode('utf-8').splitlines()
    reader = csv.DictReader(decoded_file)
    
    # Clean headers
    reader.fieldnames = [f.strip() for f in reader.fieldnames]
    
    member_names = ['Aisha', 'Rohan', 'Priya', 'Meera', 'Sam', 'Dev']
    
    results = []
    seen_rows = set()
    
    for idx, row in enumerate(reader):
        row_cleaned = {k.strip(): v.strip() for k, v in row.items() if k is not None}
        analysis = analyze_csv_row(row_cleaned, idx + 1, seen_rows, member_names)
        results.append(analysis)
        
    return results
