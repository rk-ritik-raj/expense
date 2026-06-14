# DECISIONS.md - Decision Log

Below are the significant engineering and design decisions made while building the Shared Expenses App, along with options considered and rationales.

---

### 1. Technology Stack Selection (Django REST Framework + React SPA)
- **Options Considered**:
  1. *Full Python (Django + templates + HTMX)*: Quick setup, but harder to build highly interactive UIs (like Meera's CSV editor or Rohan's ledger modals) with smooth micro-animations.
  2. *Next.js + Prisma + PostgreSQL*: Great modern stack, but the job profile specifically highlighted Python/Django REST API backend skills as the primary need.
  3. *Django REST Framework (DRF) + React (Vite + TS)*: Clean split between services. Satisfies the Python/React profile requirements and provides robust REST endpoints.
- **Decision**: **Option 3 (DRF + React)**. It aligns perfectly with the target profile and ensures clean separation of concerns, allowing modular unit testing on the python side and beautiful styling on the frontend.

---

### 2. Database Engine (SQLite)
- **Options Considered**:
  1. *PostgreSQL/MySQL*: Powerful, but requires setting up local credentials, installing additional software, or running Docker containers on the evaluation system.
  2. *SQLite*: Standard relational DB that comes pre-packaged with Python, storing database state in a single local file (`db.sqlite3`).
- **Decision**: **Option 2 (SQLite)**. As the guidelines emphasize relational databases ("Use relational DBs only"), SQLite fully complies while offering zero-config local run capability, which is ideal for placement reviewers.

---

### 3. User Authentication design (Interactive Persona Selector)
- **Options Considered**:
  1. *Complete JWT Auth (passwords, emails, token refreshes)*: Highly secure, but requires reviewers to create 6 different accounts or remember dummy passwords to test different roommate perspectives.
  2. *Simple Persona Switcher (select who you are)*: A top banner allowing users to switch who they are viewing as (Aisha, Rohan, Priya, Meera, Sam, Dev) with one click.
- **Decision**: **Option 2 (Persona Switcher)**. For a flatmate app demo, ease of evaluation is critical. Switchers let the placement drives instantly see the different balances and ledger breakdowns from Rohan's, Sam's, or Meera's perspective without tedious login/logout loops.

---

### 4. Aisha's simplified balance algorithm (Debt Minimization)
- **Options Considered**:
  1. *Direct Ledger matching (All owes kept direct)*: Roommates make dozens of small payments to settle up.
  2. *Splitwise-style Debt Minimization (Greedy matching)*: Re-routing debt pathways. By separating debtors and creditors, sorting them, and settling the maximum possible matching balance, we reduce the total transaction count to a minimum.
- **Decision**: **Option 2 (Greedy matching)**. It satisfies Aisha's request ("just one number per person. Who pays whom, how much, done") perfectly and makes final settlements simple.

---

### 5. CSV Anomaly Handling flow (Meera's Interactive Review Screen)
- **Options Considered**:
  1. *Silent Guessing (Auto-fix on upload)*: Clean data, but leaves no control. Meera requested: "I want to approve anything the app deletes or changes."
  2. *Crash Import (Reject on error)*: High data safety, but prevents importing files with minor typos or different date formats.
  3. *Dry-run + Interactive Review Board*: The backend reads the file and returns a list of suggested corrections. The frontend displays this list with color-coded warnings, allowing Meera to edit splits, accept defaults, or exclude duplicate rows before the final DB write.
- **Decision**: **Option 3 (Interactive Review Board)**. This satisfies Meera's request, prevents silent assumptions, and provides a polished experience.
