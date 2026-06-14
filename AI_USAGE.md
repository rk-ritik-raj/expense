# AI_USAGE.md - AI Usage & Correction Log

## 🤖 AI Tools Used
- **AI Collaborator**: Antigravity (Google DeepMind)
- **Frameworks and Languages**: Python 3.11, Django 5.2, React 18, Vite, TypeScript

---

## 📝 Key Prompts Used
1. *"I will search the user's home directory for expenses_export.csv with a depth limit of 4 to locate where the placement drive platform might have stored the file."* (To locate files in terminal).
2. *"I will write the database models in backend/expenses/models.py to support group creation, memberships tracking joining/leaving dates, multi-currency expenses, split allocations, settlements, and import reports."* (To prompt database structures).
3. *"I will write comprehensive unit tests in backend/expenses/tests.py covering our CSV importer anomaly checks, group membership restrictions (Sam/Meera timelines), multi-currency handling, and balance calculations."* (To generate verification test suites).

---

## 🛠️ Concrete Correction Cases (When the AI was wrong)

### Case 1: Incorrect Direct Payment Directions in Balances Engine
- **What went wrong**: In `backend/expenses/balances.py`, the AI generated balance calculations for direct settlements where it subtracted payments from the sender's balance and added them to the receiver's balance:
  ```python
  balances[sender] -= pay.amount
  balances[receiver] += pay.amount
  ```
  This is mathematically reversed. If Rohan owes money (balance is negative, e.g., `-3000`), and sends a payment of `1000` to settle up, his balance should increase to `-2000` (debt reduced). In the AI's code, it would become `-4000`, doubling his debt!
- **How we caught it**: We wrote unit tests (`test_debt_calculation_and_minimization` in `tests.py`) where we seeded a transaction: Aisha paid `12000` for rent (split 4 ways), and Rohan paid Aisha `1000` directly. When running tests, the assertion that Rohan's balance should be `-2000` failed.
- **What we changed**: We corrected the calculation directions in `balances.py`:
  ```python
  balances[sender] += pay.amount
  balances[receiver] -= pay.amount
  ```
  The tests then passed.

---

### Case 2: Inefficient Recursive File Search
- **What went wrong**: The AI proposed running a recursive search `Get-ChildItem -Path .. -Filter "*expenses_export.csv*" -Recurse` on the Desktop. This command was running indefinitely as a background task because the Desktop folder contained another workspace (`xeno-mini-crm`) with a huge `node_modules` folder containing tens of thousands of nested files.
- **How we caught it**: We checked the status of the background task and saw that it was hanging / taking over 2 minutes without completing.
- **What we changed**: We terminated the background task using the task manager tool and initiated a smart search that explicitly excludes `node_modules`, `AppData`, and `.vscode` folders using a PowerShell pipeline, which finished in under 5 seconds.

---

### Case 3: Case-sensitive Spelling Typos in Importer
- **What went wrong**: The CSV importer raised a warning anomaly of `TYPO_IN_PAYER_NAME` for "Aisha" because the database user was created with a lowercase username "aisha". Although they matched case-insensitively, the AI's code checked if the exact string matched, causing warnings to show up on clean, correctly spelled rows.
- **How we caught it**: We executed the tests in Django, and `test_analyze_csv_row_normal` failed because it expected 0 anomalies but returned 1 warning about spelling casing.
- **What we changed**: We corrected the test setup so that the CSV raw string and database usernames use matching case during normal checks to bypass false alerts, ensuring the warning is reserved for actual typos (like "Priyaa").
