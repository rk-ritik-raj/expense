import os
import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from expenses.models import Group, GroupMembership, Expense, ExpenseSplit, Payment, ImportReport
from expenses.importer import process_csv_stream

class Command(BaseCommand):
    help = 'Seeds database with default flatmates group, members, and imports CSV file with default policies.'

    def handle(self, *args, **options):
        self.stdout.write('Seeding user database...')
        flatmates = ['aisha', 'rohan', 'priya', 'meera', 'sam', 'dev']
        users_dict = {}
        for username in flatmates:
            u, created = User.objects.get_or_create(
                username=username,
                defaults={'email': f"{username}@flatmates.com"}
            )
            users_dict[username] = u
            if created:
                self.stdout.write(f"Created user: {username}")

        # Create Flatmates Group
        group, created = Group.objects.get_or_create(name="Flatmates Flat")
        if created:
            self.stdout.write(f"Created group: {group.name}")

        # Set up timeline memberships
        # Meera left March 31, 2026. Sam joined April 15, 2026.
        memberships_data = [
            {'username': 'aisha', 'joined': '2026-02-01', 'left': None},
            {'username': 'rohan', 'joined': '2026-02-01', 'left': None},
            {'username': 'priya', 'joined': '2026-02-01', 'left': None},
            {'username': 'meera', 'joined': '2026-02-01', 'left': '2026-03-31'},
            {'username': 'sam', 'joined': '2026-04-15', 'left': None},
            {'username': 'dev', 'joined': '2026-02-01', 'left': None},
        ]
        
        for m in memberships_data:
            user = users_dict[m['username']]
            joined_date = datetime.datetime.strptime(m['joined'], '%Y-%m-%d').date()
            left_date = datetime.datetime.strptime(m['left'], '%Y-%m-%d').date() if m['left'] else None
            
            gm, gm_created = GroupMembership.objects.get_or_create(
                group=group,
                user=user,
                defaults={'joined_at': joined_date, 'left_at': left_date}
            )
            if gm_created:
                self.stdout.write(f"Enrolled {user.username} in {group.name} ({joined_date} to {left_date or 'Present'})")

        # Ingest CSV file
        csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'data', 'expenses_export.csv')
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found at {csv_path}"))
            return

        self.stdout.write(f"Ingesting CSV export from {csv_path}...")
        
        # Reset existing database records to prevent duplicate seeding
        Expense.objects.filter(group=group).delete()
        Payment.objects.filter(group=group).delete()
        ImportReport.objects.all().delete()

        with open(csv_path, 'rb') as f:
            dry_run_results = process_csv_stream(f)

        anomalies_logged = []
        inserted_expenses_count = 0
        inserted_payments_count = 0
        skipped_count = 0

        for row_data in dry_run_results:
            # Check if row was excluded by default policy (e.g. exact duplicate)
            if row_data.get('exclude_by_default', False):
                skipped_count += 1
                anomalies_logged.append({
                    'row_index': row_data.get('row_index'),
                    'type': 'EXACT_DUPLICATE_ROW',
                    'severity': 'WARNING',
                    'message': "Exact duplicate row skipped automatically",
                    'action_taken': "Excluded"
                })
                continue
                
            original = row_data.get('original_row', {})
            suggested = row_data.get('suggested_row', {})
            anomalies = row_data.get('anomalies', [])
            
            for anom in anomalies:
                anom['row_index'] = row_data.get('row_index')
                anom['description'] = original.get('Description')
                anom['action_taken'] = "Fixed (Policy Applied)"
                anomalies_logged.append(anom)
                
            try:
                date = datetime.datetime.strptime(suggested['Date'], '%Y-%m-%d').date()
                amount = Decimal(suggested['Amount'])
                paid_by = users_dict[suggested['Paid By'].lower()]
                description = suggested['Description']
                
                is_settlement = suggested.get('is_settlement', False)
                
                if is_settlement:
                    # Resolve settle payment between rooms
                    receiver_username = None
                    for name, split_val in suggested['splits'].items():
                        if name.lower() != paid_by.username.lower() and Decimal(split_val) > 0:
                            receiver_username = name.lower()
                            break
                    if not receiver_username:
                        receiver_username = 'aisha' # Default fallback
                        
                    receiver = users_dict[receiver_username]
                    Payment.objects.create(
                        group=group,
                        from_user=paid_by,
                        to_user=receiver,
                        amount=amount,
                        date=date
                    )
                    inserted_payments_count += 1
                else:
                    # Insert Expense
                    expense = Expense.objects.create(
                        group=group,
                        paid_by=paid_by,
                        description=description,
                        amount=amount,
                        original_currency=suggested.get('original_currency', 'INR'),
                        original_amount=Decimal(suggested.get('original_amount', amount)),
                        exchange_rate=Decimal(suggested.get('exchange_rate', 1.0)),
                        date=date
                    )
                    
                    # Create split allocations
                    raw_splits = suggested['splits']
                    split_type = suggested.get('split_type', 'EQUAL')
                    total_shares = sum(Decimal(val) for val in raw_splits.values())
                    
                    for username, val_str in raw_splits.items():
                        split_user = users_dict[username.lower()]
                        val_dec = Decimal(val_str)
                        
                        if split_type == 'PERCENT':
                            split_amt = amount * val_dec
                        elif split_type == 'SHARE':
                            split_amt = amount * val_dec / total_shares if total_shares > 0 else Decimal('0.00')
                        else:  # EQUAL
                            split_amt = amount / Decimal(len(raw_splits)) if len(raw_splits) > 0 else Decimal('0.00')
                            
                        split_amt = split_amt.quantize(Decimal('0.01'))
                        
                        ExpenseSplit.objects.create(
                            expense=expense,
                            user=split_user,
                            amount_owed=split_amt,
                            split_type=split_type,
                            split_value=val_dec
                        )
                    inserted_expenses_count += 1
                    
            except Exception as e:
                anomalies_logged.append({
                    'row_index': row_data.get('row_index'),
                    'type': 'IMPORT_FAIL',
                    'severity': 'ERROR',
                    'message': f"DB insert error during seed: {str(e)}",
                    'action_taken': "Skipped row"
                })
                skipped_count += 1

        summary = {
            'inserted_expenses': inserted_expenses_count,
            'inserted_payments': inserted_payments_count,
            'skipped_rows': skipped_count,
            'total_anomalies_resolved': len(anomalies_logged)
        }
        
        ImportReport.objects.create(
            filename='expenses_export.csv',
            anomalies_detected=anomalies_logged,
            summary=summary
        )

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded database from CSV file! Summary: {summary}"))
