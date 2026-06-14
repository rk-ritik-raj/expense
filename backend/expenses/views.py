import datetime
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import Group, GroupMembership, Expense, ExpenseSplit, Payment, ImportReport
from .importer import process_csv_stream
from .balances import calculate_group_balances, simplify_debts, get_detailed_ledger

class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username', '').strip()
        if not username:
            return Response({'error': 'Username is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure user exists
        user, created = User.objects.get_or_create(
            username=username.lower(),
            defaults={'email': f"{username.lower()}@flatmates.com"}
        )
        return Response({
            'id': user.id,
            'username': user.username,
            'is_new': created
        })

class UserListView(APIView):
    def get(self, request):
        users = User.objects.all().values('id', 'username', 'email')
        return Response(users)

class GroupListCreateView(APIView):
    def get(self, request):
        groups = Group.objects.all().values('id', 'name', 'created_at')
        return Response(groups)

    def post(self, request):
        name = request.data.get('name', '').strip()
        if not name:
            return Response({'error': 'Group name is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        group = Group.objects.create(name=name)
        
        # Auto-seed the 6 flatmates as members of the group
        # Meera left end of March 2026. Sam joined mid-April 2026. Others are long-term members.
        memberships_data = [
            {'username': 'aisha', 'joined': '2026-02-01', 'left': None},
            {'username': 'rohan', 'joined': '2026-02-01', 'left': None},
            {'username': 'priya', 'joined': '2026-02-01', 'left': None},
            {'username': 'meera', 'joined': '2026-02-01', 'left': '2026-03-31'},
            {'username': 'sam', 'joined': '2026-04-15', 'left': None},
            {'username': 'dev', 'joined': '2026-02-01', 'left': None},
        ]
        
        for m in memberships_data:
            user, _ = User.objects.get_or_create(username=m['username'], defaults={'email': f"{m['username']}@flatmates.com"})
            joined_date = datetime.datetime.strptime(m['joined'], '%Y-%m-%d').date()
            left_date = datetime.datetime.strptime(m['left'], '%Y-%m-%d').date() if m['left'] else None
            GroupMembership.objects.create(
                group=group,
                user=user,
                joined_at=joined_date,
                left_at=left_date
            )
            
        return Response({
            'id': group.id,
            'name': group.name,
            'message': 'Group created and standard members (Aisha, Rohan, Priya, Meera, Sam, Dev) auto-enrolled.'
        }, status=status.HTTP_201_CREATED)

class GroupDetailView(APIView):
    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        members = []
        for gm in group.memberships.all().select_related('user'):
            members.append({
                'id': gm.user.id,
                'username': gm.user.username,
                'joined_at': gm.joined_at.strftime('%Y-%m-%d'),
                'left_at': gm.left_at.strftime('%Y-%m-%d') if gm.left_at else None
            })
        return Response({
            'id': group.id,
            'name': group.name,
            'members': members,
            'created_at': group.created_at
        })

class GroupBalancesView(APIView):
    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        balances_dec = calculate_group_balances(group)
        
        # Convert decimal values to float for JSON response
        balances = {user: float(bal) for user, bal in balances_dec.items()}
        simplified_payments = simplify_debts(balances_dec)
        
        return Response({
            'balances': balances,
            'simplified_payments': simplified_payments
        })

class LedgerView(APIView):
    def get(self, request, group_id, username):
        group = get_object_or_404(Group, id=group_id)
        ledger = get_detailed_ledger(group, username)
        if not ledger:
            return Response({'error': f"User '{username}' is not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(ledger)

class ExpenseCreateView(APIView):
    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        expenses = Expense.objects.filter(group=group).order_by('-date', '-id')
        # Simple serialization
        data = []
        for exp in expenses:
            data.append({
                'id': exp.id,
                'description': exp.description,
                'amount': float(exp.amount),
                'paid_by': exp.paid_by.username,
                'date': exp.date.strftime('%Y-%m-%d'),
                'original_currency': exp.original_currency,
                'original_amount': float(exp.original_amount),
                'exchange_rate': float(exp.exchange_rate),
                'splits': [{'username': s.user.username, 'amount': float(s.amount_owed)} for s in exp.splits.all()]
            })
        return Response(data)

    @transaction.atomic
    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        data = request.data
        
        desc = data.get('description', '').strip()
        raw_amount = data.get('amount')
        paid_by_username = data.get('paid_by')
        raw_date = data.get('date')
        
        if not desc or not raw_amount or not paid_by_username or not raw_date:
            return Response({'error': 'Missing required fields: description, amount, paid_by, date'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            amount = Decimal(str(raw_amount))
            date = datetime.datetime.strptime(str(raw_date), '%Y-%m-%d').date()
        except Exception:
            return Response({'error': 'Invalid amount or date format (use YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)
        
        payer = get_object_or_404(User, username=paid_by_username.lower())
        
        # Verify payer is a group member on this date
        gm_payer = GroupMembership.objects.filter(group=group, user=payer).first()
        if not gm_payer or (gm_payer.left_at and date > gm_payer.left_at) or (date < gm_payer.joined_at):
            return Response({'error': f"{payer.username} is not an active member on {date}."}, status=status.HTTP_400_BAD_REQUEST)
            
        currency = data.get('original_currency', 'INR')
        orig_amount = Decimal(str(data.get('original_amount', amount)))
        exch_rate = Decimal(str(data.get('exchange_rate', 1.0)))

        expense = Expense.objects.create(
            group=group,
            paid_by=payer,
            description=desc,
            amount=amount,
            original_currency=currency,
            original_amount=orig_amount,
            exchange_rate=exch_rate,
            date=date
        )

        # Create splits
        raw_splits = data.get('splits', [])  # list of dict: {username: 'aisha', share: 1.0} or {username: 'aisha', percentage: 25.0} or just username: amount
        split_type = data.get('split_type', 'EQUAL')
        
        for s in raw_splits:
            split_user = get_object_or_404(User, username=s['username'].lower())
            
            # Enforce timeline checks
            gm_split = GroupMembership.objects.filter(group=group, user=split_user).first()
            if not gm_split or (gm_split.left_at and date > gm_split.left_at) or (date < gm_split.joined_at):
                # Ignore inactive split members or fail
                return Response({'error': f"{split_user.username} is not an active member on {date}."}, status=status.HTTP_400_BAD_REQUEST)
            
            split_amt = Decimal(str(s['amount']))
            ExpenseSplit.objects.create(
                expense=expense,
                user=split_user,
                amount_owed=split_amt,
                split_type=split_type,
                split_value=Decimal(str(s.get('value', 0))) if s.get('value') else None
            )

        return Response({'id': expense.id, 'message': 'Expense created successfully.'}, status=status.HTTP_201_CREATED)

class PaymentCreateView(APIView):
    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        payments = Payment.objects.filter(group=group).order_by('-date', '-id')
        data = []
        for p in payments:
            data.append({
                'id': p.id,
                'from_user': p.from_user.username,
                'to_user': p.to_user.username,
                'amount': float(p.amount),
                'date': p.date.strftime('%Y-%m-%d')
            })
        return Response(data)

    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        data = request.data
        
        from_username = data.get('from_user')
        to_username = data.get('to_user')
        raw_amount = data.get('amount')
        raw_date = data.get('date')
        
        if not from_username or not to_username or not raw_amount or not raw_date:
            return Response({'error': 'Missing required fields: from_user, to_user, amount, date'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            amount = Decimal(str(raw_amount))
            date = datetime.datetime.strptime(str(raw_date), '%Y-%m-%d').date()
        except Exception:
            return Response({'error': 'Invalid amount or date format (use YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)
            
        from_user = get_object_or_404(User, username=from_username.lower())
        to_user = get_object_or_404(User, username=to_username.lower())
        
        payment = Payment.objects.create(
            group=group,
            from_user=from_user,
            to_user=to_user,
            amount=amount,
            date=date
        )
        return Response({
            'id': payment.id,
            'message': f"Settlement payment of ₹{payment.amount} from {from_user.username} to {to_user.username} recorded successfully."
        }, status=status.HTTP_201_CREATED)

class ImportDryRunView(APIView):
    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            results = process_csv_stream(csv_file)
            return Response(results)
        except Exception as e:
            return Response({'error': f"Failed to parse CSV: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

class ImportConfirmView(APIView):
    @transaction.atomic
    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        filename = request.data.get('filename', 'expenses_export.csv')
        final_rows = request.data.get('rows', [])  # Approved rows from frontend review screen
        
        anomalies_logged = []
        inserted_expenses_count = 0
        inserted_payments_count = 0
        skipped_count = 0
        
        for row_data in final_rows:
            # Check if row was excluded
            if row_data.get('exclude', False):
                skipped_count += 1
                continue
                
            original = row_data.get('original_row', {})
            suggested = row_data.get('suggested_row', {})
            anomalies = row_data.get('anomalies', [])
            
            # Add anomalies to the report log
            for anom in anomalies:
                anom['row_index'] = row_data.get('row_index')
                anom['description'] = original.get('Description')
                anom['action_taken'] = "Excluded" if row_data.get('exclude') else "Fixed (Policy Applied)"
                anomalies_logged.append(anom)
                
            # Perform DB insertions
            try:
                date = datetime.datetime.strptime(suggested['Date'], '%Y-%m-%d').date()
                amount = Decimal(suggested['Amount'])
                paid_by = User.objects.get(username=suggested['Paid By'].lower())
                description = suggested['Description']
                
                is_settlement = suggested.get('is_settlement', False)
                is_personal = suggested.get('is_personal', False)
                
                if is_settlement:
                    # Resolve settle payment between rooms
                    # For a settlement logged as an expense: e.g. "Rohan paid Aisha".
                    # Find receiver from splits (the one marked in splits)
                    receiver_username = None
                    for name, split_val in suggested['splits'].items():
                        if name.lower() != paid_by.username.lower() and Decimal(split_val) > 0:
                            receiver_username = name.lower()
                            break
                    
                    if not receiver_username:
                        # Fallback if splits were cleared
                        receiver_username = 'aisha' # Default fallback
                        
                    receiver = User.objects.get(username=receiver_username)
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
                    
                    # If EQUAL split, split_amt = amount / number of splits
                    # If PERCENT split, split_amt = amount * split_pct
                    # If SHARE split, split_amt = amount * split_share / total_shares
                    total_shares = sum(Decimal(val) for val in raw_splits.values())
                    
                    for username, val_str in raw_splits.items():
                        split_user = User.objects.get(username=username.lower())
                        val_dec = Decimal(val_str)
                        
                        if split_type == 'PERCENT':
                            split_amt = amount * val_dec
                        elif split_type == 'SHARE':
                            split_amt = amount * val_dec / total_shares if total_shares > 0 else Decimal('0.00')
                        else:  # EQUAL
                            split_amt = amount / Decimal(len(raw_splits)) if len(raw_splits) > 0 else Decimal('0.00')
                            
                        # Round split amount to 2 decimals
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
                # Log parsing failure inside confirm loop
                anomalies_logged.append({
                    'row_index': row_data.get('row_index'),
                    'type': 'IMPORT_FAIL',
                    'severity': 'ERROR',
                    'message': f"DB insert error: {str(e)}",
                    'action_taken': "Skipped row"
                })
                skipped_count += 1

        # Save Import Report
        summary = {
            'inserted_expenses': inserted_expenses_count,
            'inserted_payments': inserted_payments_count,
            'skipped_rows': skipped_count,
            'total_anomalies_resolved': len(anomalies_logged)
        }
        
        report = ImportReport.objects.create(
            filename=filename,
            anomalies_detected=anomalies_logged,
            summary=summary
        )

        return Response({
            'report_id': report.id,
            'summary': summary,
            'anomalies': anomalies_logged
        }, status=status.HTTP_201_CREATED)

class ImportReportListView(APIView):
    def get(self, request, group_id):
        reports = ImportReport.objects.all().order_by('-imported_at')
        data = []
        for r in reports:
            data.append({
                'id': r.id,
                'imported_at': r.imported_at.strftime('%Y-%m-%d %H:%M:%S'),
                'filename': r.filename,
                'summary': r.summary,
                'anomalies': r.anomalies_detected
            })
        return Response(data)
