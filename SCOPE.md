# SCOPE.md - Anomaly Log & Database Schema

## 📋 CSV Anomaly Log

Below is the log of the deliberate data problems found in the `expenses_export.csv` file, along with the detection rules and resolution policies implemented in our importer engine (`backend/expenses/importer.py`):

| # | Anomaly Type | Detection Method | Resolution Policy / Action Taken | Flatmate Request Satisfied |
|---|---|---|---|---|
| **1** | **Exact Duplicate Row** | Check if a row has the exact same date, description, payee, and amounts as a previously parsed row. | **Ignore/Exclude**: Auto-exclude the duplicate row by default during import to prevent double-charging. | Meera (approval) |
| **2** | **Conflicting Duplicate Row** | Same date, payer, and description, but different amount. | **Flag & Prompt**: Highlight the conflict in the UI, letting the user toggle which row wins before writing to the DB. | Meera (approval) |
| **3** | **Inconsistent Date Format** | Check if dates are in formats other than `YYYY-MM-DD` (e.g. `DD/MM/YYYY`, `MM-DD-YYYY`). | **Standardize**: Standardize date using datetime parsers and convert to `YYYY-MM-DD` before database write. | *Data Cleanliness* |
| **4** | **Malformed Amount** | Match non-numeric characters (like currency symbols `₹`, `$`, or commas `,`) in the amount field. | **Sanitize**: Strip symbols and commas, and cast the remaining characters to a Decimal number. | *Data Cleanliness* |
| **5** | **Negative Amount (Refund)** | Verify if the sanitized amount value is less than 0. | **Reversed Splits**: Parse as a refund. The split allocation reverses the debt (recipient gets credit, payer gets debited). | *Data Cleanliness* |
| **6** | **Settlement Logged as Expense** | Description matches keyword `settle`, `payment`, `payback`, or `paid back` (case-insensitive). | **Record Conversion**: Convert the database record type from an `Expense` to a `Payment` model instance so it does not skew shared expense averages. | Aisha & Rohan |
| **7** | **US Dollar pretending to be Rupee** | Check if the currency column contains `USD`, description contains `USD`, or amount has a `$` symbol. | **Convert & Log**: Multiply the USD amount by a fixed rate of `83.00`. Record both the original currency/amount and exchange rate in the DB. | Priya & Rohan |
| **8** | **Typoed Payer Name** | String matching on payer column with standard usernames (case-insensitive + common typos mapping). | **Normalize**: Trim whitespace, correct typos (e.g., "Priyaa" to "priya"), and associate the row with the correct User model. | *Data Cleanliness* |
| **9** | **Inactive split member (Sam)** | Sam has splits on an expense dated before Sam's join date (`2026-04-15`). | **Auto-exclude & Reallocate**: Remove Sam from the splits array and divide the remaining balance equally among the active members on that date. | Sam |
| **10** | **Inactive split member (Meera)** | Meera has splits on an expense dated after Meera's move-out date (`2026-03-31`). | **Auto-exclude & Reallocate**: Remove Meera from the splits array and divide the remaining balance among active members. | Meera & Sam |
| **11** | **Split Sum Mismatch** | Total split values do not sum to 1.0 (for percentages) or are otherwise malformed. | **Normalize**: Re-normalize individual splits proportionally so they sum to exactly 100% (preventing rounding leaks). | *Calculations Integrity* |
| **12** | **Self-only Split** | Payer is the only member included in the splits array. | **Personal Expense**: Flag as personal expense in metadata and skip from group shared balances. | Rohan (ledger clarity) |

---

## 🗄️ Relational Database Schema

We use SQLite for local development. The database contains 6 tables:

### 1. `auth_user`
Django's built-in User table to represent roommates.
- `id` (INTEGER, PK)
- `username` (VARCHAR)
- `email` (VARCHAR)

### 2. `expenses_group`
Represents expense sharing groups.
- `id` (INTEGER, PK)
- `name` (VARCHAR)
- `created_at` (DATETIME)

### 3. `expenses_groupmembership`
Tracks joining/leaving timelines.
- `id` (INTEGER, PK)
- `group_id` (INTEGER, FK -> `expenses_group.id`)
- `user_id` (INTEGER, FK -> `auth_user.id`)
- `joined_at` (DATE)
- `left_at` (DATE, Nullable)

### 4. `expenses_expense`
Details the expense items, including original currency records.
- `id` (INTEGER, PK)
- `group_id` (INTEGER, FK -> `expenses_group.id`)
- `paid_by_id` (INTEGER, FK -> `auth_user.id`)
- `description` (VARCHAR)
- `amount` (DECIMAL, base currency normalized to INR)
- `original_currency` (VARCHAR, e.g. `USD`, `INR`)
- `original_amount` (DECIMAL)
- `exchange_rate` (DECIMAL, default 1.0)
- `date` (DATE)
- `created_at` (DATETIME)

### 5. `expenses_expensesplit`
Owed allocations for each roommate on an expense.
- `id` (INTEGER, PK)
- `expense_id` (INTEGER, FK -> `expenses_expense.id`)
- `user_id` (INTEGER, FK -> `auth_user.id`)
- `amount_owed` (DECIMAL)
- `split_type` (VARCHAR, e.g. `EQUAL`, `EXACT`, `PERCENT`, `SHARE`)
- `split_value` (DECIMAL, Nullable)

### 6. `expenses_payment`
Tracks settlements/direct payments.
- `id` (INTEGER, PK)
- `group_id` (INTEGER, FK -> `expenses_group.id`)
- `from_user_id` (INTEGER, FK -> `auth_user.id`)
- `to_user_id` (INTEGER, FK -> `auth_user.id`)
- `amount` (DECIMAL)
- `date` (DATE)
- `created_at` (DATETIME)

### 7. `expenses_importreport`
Logs generated import audit details.
- `id` (INTEGER, PK)
- `imported_at` (DATETIME)
- `filename` (VARCHAR)
- `anomalies_detected` (JSON)
- `summary` (JSON)
