**# Settled.io - Shared Expenses App

An AI-native, premium shared expenses reconciliation app designed to clean up messy flatmate sheets, resolve currency conversions, and simplify settlements. Built for the Software Engineering Intern technical assignment.

---

## 🚀 Technology Stack
1. **Backend**: Python + Django REST Framework + SQLite
2. **Frontend**: React + Vite + TypeScript + Vanilla CSS
3. **AI Helper**: Antigravity (Google DeepMind)

---

## 🛠 Setup & Running Instructions

### 1. Backend (Django API)
The backend runs a Django server with SQLite.

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Activate the virtual environment:
   - On Windows (PowerShell):
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - On Linux/macOS:
     ```bash
     source venv/bin/activate
     ```
3. Run migrations and database checks:
   ```bash
   python manage.py check
   ```
4. Start the Django dev server:
   ```bash
   python manage.py runserver 8000
   ```
   *The backend will be available at `http://localhost:8000/`*

#### Running Backend Unit Tests
We have built comprehensive tests verifying CSV anomaly detection, group membership checks, and balance calculations:
```bash
python manage.py test expenses.tests
```

---

### 2. Frontend (React SPA)
The frontend is built using Vite.

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies (if not already done):
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   *The frontend will be available at `http://localhost:5173/`*

---

## 💡 Key App Features
- **Persona Switcher**: View the dashboard and balances from the perspective of Aisha, Rohan, Priya, Meera, Sam, or Dev.
- **Aisha's View**: Single-number simplified debt settlements displaying who pays whom, how much, and done.
- **Rohan's Ledger**: Clicking any member's balance displays a detailed modal detailing the exact items and formulas that make up the balance (No magic numbers!).
- **Meera's Interactive CSV Importer**: An ingestion interface highlighting all 12 CSV data anomalies, allowing approval, custom correction, or exclusion on a row-by-row level before DB write.
- **Timeline Constraints (Sam & Meera)**: Membership date bounds are enforced automatically. Sam (joined mid-April) is not charged for March electricity, and Meera (left end of March) does not split April/May items.
**
