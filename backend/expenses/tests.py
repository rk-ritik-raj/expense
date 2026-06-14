import datetime
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from .models import Group, GroupMembership, Expense, ExpenseSplit, Payment
from .importer import clean_amount, parse_date, find_user_match, analyze_csv_row
from .balances import calculate_group_balances, simplify_debts, get_detailed_ledger

class ImporterUtilsTestCase(TestCase):
    def test_clean_amount(self):
        self.assertEqual(clean_amount('₹1,500.50'), '1500.50')
        self.assertEqual(clean_amount('$100'), '100')
        self.assertEqual(clean_amount('-250.00'), '-250.00')
        self.assertIsNone(clean_amount(''))

    def test_parse_date(self):
        self.assertEqual(parse_date('2026-02-10'), datetime.date(2026, 2, 10))
        self.assertEqual(parse_date('15/03/2026'), datetime.date(2026, 3, 15))
        self.assertEqual(parse_date('10-04-2026'), datetime.date(2026, 4, 10))
        self.assertIsNone(parse_date('invalid-date'))

    def test_find_user_match(self):
        # Create user
        User.objects.create(username='aisha')
        self.assertIsNotNone(find_user_match('Aisha '))
        self.assertIsNotNone(find_user_match('aesha'))
        self.assertIsNone(find_user_match('unknown'))

class ImporterLogicTestCase(TestCase):
    def setUp(self):
        # Seed users
        self.flatmates = ['aisha', 'rohan', 'priya', 'meera', 'sam', 'dev']
        self.users = {}
        for username in self.flatmates:
            self.users[username] = User.objects.create(username=username)

    def test_analyze_csv_row_normal(self):
        row = {
            'Date': '2026-02-01',
            'Description': 'Rent',
            'Amount': '12000',
            'Paid By': 'aisha',
            'Aisha': '1', 'Rohan': '1', 'Priya': '1', 'Meera': '1', 'Sam': '0', 'Dev': '0',
            'Currency': 'INR'
        }
        seen = set()
        res = analyze_csv_row(row, 1, seen, ['Aisha', 'Rohan', 'Priya', 'Meera', 'Sam', 'Dev'])
        self.assertEqual(len(res['anomalies']), 0)
        self.assertFalse(res['exclude_by_default'])

    def test_analyze_csv_row_anomalies(self):
        seen = set()
        member_names = ['Aisha', 'Rohan', 'Priya', 'Meera', 'Sam', 'Dev']
        
        # 1. Inconsistent Date and Malformed Amount
        row = {
            'Date': '12/02/2026', 'Description': 'Groceries', 'Amount': '₹1500', 'Paid By': 'Rohan',
            'Aisha': '1', 'Rohan': '1', 'Priya': '1', 'Meera': '1', 'Sam': '0', 'Dev': '0', 'Currency': 'INR'
        }
        res = analyze_csv_row(row, 1, seen, member_names)
        anomaly_types = [a['type'] for a in res['anomalies']]
        self.assertIn('INCONSISTENT_DATE_FORMAT', anomaly_types)
        self.assertIn('MALFORMED_AMOUNT_TEXT', anomaly_types)
        
        # 2. Negative Amount
        row_neg = {
            'Date': '2026-02-18', 'Description': 'Refund', 'Amount': '-600', 'Paid By': 'Priya',
            'Aisha': '1', 'Rohan': '1', 'Priya': '1', 'Meera': '1', 'Sam': '0', 'Dev': '0', 'Currency': 'INR'
        }
        res_neg = analyze_csv_row(row_neg, 2, seen, member_names)
        anomaly_types = [a['type'] for a in res_neg['anomalies']]
        self.assertIn('NEGATIVE_AMOUNT', anomaly_types)
        
        # 3. Settlement
        row_set = {
            'Date': '2026-02-25', 'Description': 'Settlement Rohan to Aisha', 'Amount': '1000', 'Paid By': 'Rohan',
            'Aisha': '1', 'Rohan': '0', 'Priya': '0', 'Meera': '0', 'Sam': '0', 'Dev': '0', 'Currency': 'INR'
        }
        res_set = analyze_csv_row(row_set, 3, seen, member_names)
        self.assertTrue(res_set['suggested_row']['is_settlement'])
        
        # 4. Sam in March (Inactive split member)
        row_sam = {
            'Date': '2026-03-15', 'Description': 'March Elec', 'Amount': '2000', 'Paid By': 'Aisha',
            'Aisha': '1', 'Rohan': '1', 'Priya': '1', 'Meera': '1', 'Sam': '1', 'Dev': '0', 'Currency': 'INR'
        }
        res_sam = analyze_csv_row(row_sam, 4, seen, member_names)
        anomaly_types = [a['type'] for a in res_sam['anomalies']]
        self.assertIn('INACTIVE_MEMBER_SAM_MARCH', anomaly_types)
        # Verify Sam is excluded in suggested splits
        self.assertNotIn('Sam', res_sam['suggested_row']['splits'])

        # 5. Meera in April (Inactive split member)
        row_meera = {
            'Date': '2026-04-25', 'Description': 'April Groceries', 'Amount': '1500', 'Paid By': 'Rohan',
            'Aisha': '1', 'Rohan': '1', 'Priya': '1', 'Meera': '1', 'Sam': '1', 'Dev': '0', 'Currency': 'INR'
        }
        res_meera = analyze_csv_row(row_meera, 5, seen, member_names)
        anomaly_types = [a['type'] for a in res_meera['anomalies']]
        self.assertIn('INACTIVE_MEMBER_MEERA_POST_MARCH', anomaly_types)
        self.assertNotIn('Meera', res_meera['suggested_row']['splits'])

class BalancesTestCase(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name="Flatmates")
        self.users = {}
        for username in ['aisha', 'rohan', 'priya', 'meera', 'sam', 'dev']:
            u = User.objects.create(username=username)
            self.users[username] = u
            GroupMembership.objects.create(
                group=self.group,
                user=u,
                joined_at=datetime.date(2026, 2, 1),
                left_at=datetime.date(2026, 3, 31) if username == 'meera' else None
            )

    def test_debt_calculation_and_minimization(self):
        # Rent expense: Aisha paid 12,000. Splits: Aisha, Rohan, Priya, Meera (3000 each)
        exp1 = Expense.objects.create(
            group=self.group, paid_by=self.users['aisha'], description="Rent",
            amount=Decimal('12000.00'), original_amount=Decimal('12000.00'), date=datetime.date(2026, 2, 1)
        )
        for name in ['aisha', 'rohan', 'priya', 'meera']:
            ExpenseSplit.objects.create(expense=exp1, user=self.users[name], amount_owed=Decimal('3000.00'))

        # Rohan paid 1000 to settle Aisha directly
        Payment.objects.create(
            group=self.group, from_user=self.users['rohan'], to_user=self.users['aisha'],
            amount=Decimal('1000.00'), date=datetime.date(2026, 2, 25)
        )

        balances = calculate_group_balances(self.group)
        # Aisha: Net balance = Paid (12000) - Owed (3000) - Received payment (1000) = +8000.
        # Rohan: Net balance = Paid (0) - Owed (3000) + Sent payment (1000) = -2000.
        # Priya: Net balance = Paid (0) - Owed (3000) = -3000.
        # Meera: Net balance = Paid (0) - Owed (3000) = -3000.
        self.assertEqual(balances['aisha'], Decimal('8000.00'))
        self.assertEqual(balances['rohan'], Decimal('-2000.00'))
        self.assertEqual(balances['priya'], Decimal('-3000.00'))
        self.assertEqual(balances['meera'], Decimal('-3000.00'))

        simplified = simplify_debts(balances)
        # Match simplified outputs
        # Rohan owes Aisha 2000, Priya owes Aisha 3000, Meera owes Aisha 3000.
        self.assertEqual(len(simplified), 3)
        
        # Verify Rohan's detailed ledger breakdown
        ledger = get_detailed_ledger(self.group, 'rohan')
        self.assertEqual(ledger['calculated_balance'], -2000.0)
        self.assertEqual(len(ledger['ledger_items']), 2) # 1 expense split + 1 payment sent

from django.urls import reverse

class APIViewsTestCase(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name="Test Group")
        self.user_aisha = User.objects.create(username="aisha")
        self.user_rohan = User.objects.create(username="rohan")
        GroupMembership.objects.create(group=self.group, user=self.user_aisha, joined_at=datetime.date(2026, 2, 1))
        GroupMembership.objects.create(group=self.group, user=self.user_rohan, joined_at=datetime.date(2026, 2, 1))

    def test_group_list_create(self):
        # Test GET groups
        response = self.client.get(reverse('groups'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

        # Test POST create group
        response = self.client.post(reverse('groups'), {'name': 'New Group'}, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Group.objects.count(), 2)

    def test_expense_list_create(self):
        # Create an expense
        expense = Expense.objects.create(
            group=self.group,
            paid_by=self.user_aisha,
            description="Dinner",
            amount=Decimal("100.00"),
            original_amount=Decimal("100.00"),
            date=datetime.date(2026, 2, 1)
        )
        ExpenseSplit.objects.create(
            expense=expense,
            user=self.user_aisha,
            amount_owed=Decimal("50.00")
        )
        ExpenseSplit.objects.create(
            expense=expense,
            user=self.user_rohan,
            amount_owed=Decimal("50.00")
        )

        # Test GET expenses
        response = self.client.get(reverse('expenses', args=[self.group.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['description'], "Dinner")

