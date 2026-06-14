from decimal import Decimal
from django.contrib.auth.models import User
from .models import Expense, ExpenseSplit, Payment

def calculate_group_balances(group):
    """
    Calculate the net balances for each member in the group.
    Net Balance = Total Paid + Payments Received - Total Owed - Payments Sent.
    """
    members = [m.user for m in group.memberships.all()]
    balances = {m.username: Decimal('0.00') for m in members}

    # 1. Add total paid for expenses
    expenses = Expense.objects.filter(group=group)
    for exp in expenses:
        payer = exp.paid_by.username
        if payer in balances:
            balances[payer] += exp.amount
            
        # 2. Subtract what each member owes
        splits = exp.splits.all()
        for split in splits:
            username = split.user.username
            if username in balances:
                balances[username] -= split.amount_owed

    # 3. Adjust for manual payments/settlements
    payments = Payment.objects.filter(group=group)
    for pay in payments:
        sender = pay.from_user.username
        receiver = pay.to_user.username
        if sender in balances:
            balances[sender] += pay.amount
        if receiver in balances:
            balances[receiver] -= pay.amount

    return balances

def simplify_debts(balances):
    """
    Aisha's View: Debt-minimization algorithm.
    Takes a dict of username: net_balance and returns a list of transactions:
    { 'from_user': 'Rohan', 'to_user': 'Aisha', 'amount': 1200.00 }
    """
    # Filter out near-zero balances (rounding issues)
    debtors = []   # (username, negative balance)
    creditors = []  # (username, positive balance)

    for user, bal in balances.items():
        # Clean rounding errors to 2 decimal places
        bal_rounded = bal.quantize(Decimal('0.01'))
        if bal_rounded < 0:
            debtors.append([user, abs(bal_rounded)])
        elif bal_rounded > 0:
            creditors.append([user, bal_rounded])

    transactions = []

    # Sort so we match largest debtor with largest creditor
    debtors.sort(key=lambda x: x[1], reverse=True)
    creditors.sort(key=lambda x: x[1], reverse=True)

    d_idx = 0
    c_idx = 0

    while d_idx < len(debtors) and c_idx < len(creditors):
        debtor_name, debt_amt = debtors[d_idx]
        creditor_name, credit_amt = creditors[c_idx]

        if debt_amt == 0:
            d_idx += 1
            continue
        if credit_amt == 0:
            c_idx += 1
            continue

        # Settle the minimum of the two
        settle_amt = min(debt_amt, credit_amt)
        transactions.append({
            'from_user': debtor_name,
            'to_user': creditor_name,
            'amount': float(settle_amt)
        })

        debtors[d_idx][1] -= settle_amt
        creditors[c_idx][1] -= settle_amt

        if debtors[d_idx][1] < Decimal('0.01'):
            d_idx += 1
        if creditors[c_idx][1] < Decimal('0.01'):
            c_idx += 1

    return transactions

def get_detailed_ledger(group, username):
    """
    Rohan's View: Returns list of detailed transactions that make up a member's balance.
    Includes:
    - Expenses paid by this user: detail what others owe them
    - Expenses split with this user: detail what they owe to others
    - Payments sent by this user
    - Payments received by this user
    """
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return {}

    items = []
    
    # 1. Expenses where they participated (they owe money)
    splits = ExpenseSplit.objects.filter(expense__group=group, user=user).select_related('expense', 'expense__paid_by')
    for split in splits:
        exp = split.expense
        if exp.paid_by != user:
            items.append({
                'type': 'EXPENSE_OWED',
                'date': exp.date.strftime('%Y-%m-%d'),
                'description': exp.description,
                'total_amount': float(exp.amount),
                'your_share': float(split.amount_owed),
                'paid_by': exp.paid_by.username,
                'details': f"Your split of {exp.description} (Total: ₹{exp.amount}, paid by {exp.paid_by.username})"
            })

    # 2. Expenses paid by this user (others owe them money)
    paid_expenses = Expense.objects.filter(group=group, paid_by=user).prefetch_related('splits', 'splits__user')
    for exp in paid_expenses:
        # Calculate how much others owe
        other_splits = exp.splits.exclude(user=user)
        total_owed_by_others = sum(s.amount_owed for s in other_splits)
        if total_owed_by_others > 0:
            breakdown = [f"{s.user.username}: ₹{s.amount_owed}" for s in other_splits]
            items.append({
                'type': 'EXPENSE_PAID',
                'date': exp.date.strftime('%Y-%m-%d'),
                'description': exp.description,
                'total_amount': float(exp.amount),
                'your_share': float(exp.amount - total_owed_by_others),
                'owed_by_others': float(total_owed_by_others),
                'paid_by': username,
                'details': f"You paid for {exp.description}. Roommates owe you: {', '.join(breakdown)}"
            })

    # 3. Payments sent by this user
    sent_payments = Payment.objects.filter(group=group, from_user=user).select_related('to_user')
    for pay in sent_payments:
        items.append({
            'type': 'PAYMENT_SENT',
            'date': pay.date.strftime('%Y-%m-%d'),
            'description': f"Settle payment to {pay.to_user.username}",
            'total_amount': float(pay.amount),
            'your_share': float(pay.amount),
            'paid_by': username,
            'details': f"You paid ₹{pay.amount} directly to {pay.to_user.username} to settle debt"
        })

    # 4. Payments received by this user
    received_payments = Payment.objects.filter(group=group, to_user=user).select_related('from_user')
    for pay in received_payments:
        items.append({
            'type': 'PAYMENT_RECEIVED',
            'date': pay.date.strftime('%Y-%m-%d'),
            'description': f"Settle payment from {pay.from_user.username}",
            'total_amount': float(pay.amount),
            'your_share': float(pay.amount),
            'paid_by': pay.from_user.username,
            'details': f"{pay.from_user.username} paid you ₹{pay.amount} directly to settle debt"
        })

    # Sort ledger items by date
    items.sort(key=lambda x: x['date'])
    
    # Calculate net balance
    # Net = Sum(Owed to you) - Sum(You owe)
    # For EXPENSE_PAID: user gets back `owed_by_others`
    # For EXPENSE_OWED: user owes `your_share`
    # For PAYMENT_SENT: user sent `total_amount` (reduces their debt, acting like credit/return)
    # For PAYMENT_RECEIVED: user received `total_amount` (reduces credit, acting like debit)
    net_balance = Decimal('0.00')
    for item in items:
        if item['type'] == 'EXPENSE_OWED':
            net_balance -= Decimal(str(item['your_share']))
        elif item['type'] == 'EXPENSE_PAID':
            net_balance += Decimal(str(item['owed_by_others']))
        elif item['type'] == 'PAYMENT_SENT':
            net_balance += Decimal(str(item['total_amount']))
        elif item['type'] == 'PAYMENT_RECEIVED':
            net_balance -= Decimal(str(item['total_amount']))

    return {
        'username': username,
        'ledger_items': items,
        'calculated_balance': float(net_balance)
    }
