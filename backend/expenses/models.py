from django.db import models
from django.contrib.auth.models import User

class Group(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class GroupMembership(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_memberships')
    joined_at = models.DateField()
    left_at = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('group', 'user')

    def __str__(self):
        return f"{self.user.username} in {self.group.name} ({self.joined_at} to {self.left_at or 'Present'})"

class Expense(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='expenses')
    paid_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='paid_expenses')
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # In normalized INR
    original_currency = models.CharField(max_length=3, default='INR')  # 'INR' or 'USD'
    original_amount = models.DecimalField(max_digits=12, decimal_places=2)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, default=1.0000)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.description} ({self.amount} INR) paid by {self.paid_by.username}"

class ExpenseSplit(models.Model):
    SPLIT_TYPES = (
        ('EQUAL', 'Equal'),
        ('EXACT', 'Exact'),
        ('PERCENT', 'Percentage'),
        ('SHARE', 'Share'),
    )
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='splits')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expense_splits')
    amount_owed = models.DecimalField(max_digits=12, decimal_places=2)
    split_type = models.CharField(max_length=10, choices=SPLIT_TYPES, default='EQUAL')
    split_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Percent value, or share value

    def __str__(self):
        return f"{self.user.username} owes {self.amount_owed} INR for {self.expense.description}"

class Payment(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='payments')
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_payments')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.from_user.username} paid {self.amount} INR to {self.to_user.username}"

class ImportReport(models.Model):
    imported_at = models.DateTimeField(auto_now_add=True)
    filename = models.CharField(max_length=255)
    anomalies_detected = models.JSONField(default=list)  # List of dicts representing detected issues
    summary = models.JSONField(default=dict)  # Import summary metrics

    def __str__(self):
        return f"Import of {self.filename} at {self.imported_at}"
