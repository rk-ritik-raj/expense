from django.urls import path
from .views import (
    LoginView, UserListView, GroupListCreateView, GroupDetailView,
    GroupBalancesView, LedgerView, ExpenseCreateView, PaymentCreateView,
    ImportDryRunView, ImportConfirmView, ImportReportListView
)

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='login'),
    path('users/', UserListView.as_view(), name='users'),
    path('groups/', GroupListCreateView.as_view(), name='groups'),
    path('groups/<int:group_id>/', GroupDetailView.as_view(), name='group_detail'),
    path('groups/<int:group_id>/balances/', GroupBalancesView.as_view(), name='group_balances'),
    path('groups/<int:group_id>/ledger/<str:username>/', LedgerView.as_view(), name='ledger'),
    path('groups/<int:group_id>/expenses/', ExpenseCreateView.as_view(), name='expenses'),
    path('groups/<int:group_id>/payments/', PaymentCreateView.as_view(), name='payments'),
    path('groups/<int:group_id>/import/dry-run/', ImportDryRunView.as_view(), name='import_dry_run'),
    path('groups/<int:group_id>/import/confirm/', ImportConfirmView.as_view(), name='import_confirm'),
    path('groups/<int:group_id>/import/reports/', ImportReportListView.as_view(), name='import_reports'),
]
