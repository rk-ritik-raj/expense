# Settled.io - Shared Expenses Management System

A modern expense-sharing platform that helps roommates and groups track expenses, manage settlements, import CSV records, handle currency conversions, and simplify debt reconciliation.

## 🚀 Overview

Settled.io is designed to solve common shared-expense problems such as:

* Tracking group expenses
* Managing settlements between members
* Importing expense data from CSV files
* Detecting and correcting data anomalies
* Handling multi-currency transactions
* Simplifying debt settlements using balance minimization
* Enforcing membership timelines for fair expense distribution

---

## ✨ Features

### 👥 Group Expense Management

* Create and manage expense groups
* Track group memberships
* Support joining and leaving dates
* Fair expense allocation based on active membership periods

### 💰 Expense Tracking

* Record expenses with descriptions and dates
* Support multiple currencies
* Automatic currency normalization
* Store original and converted amounts

### 🔄 Settlement Management

* Direct payment tracking
* Balance calculations
* Debt minimization algorithm
* Clear "Who pays whom" summaries

### 📊 Interactive Ledger

* Detailed breakdown of balances
* Transparent calculations
* Expense contribution tracking
* Settlement history

### 📁 CSV Import System

* Upload expense exports
* Detect data anomalies automatically
* Interactive correction workflow
* Import audit reporting

### ⚠️ Anomaly Detection

The importer automatically handles:

* Duplicate records
* Conflicting duplicate entries
* Invalid date formats
* Malformed amounts
* Negative refund transactions
* Settlement records logged as expenses
* Currency conversion issues
* Username typos
* Inactive members in splits
* Split calculation mismatches
* Personal expenses

---

## 🛠 Tech Stack

### Backend

* Python 3.11
* Django 5.2
* Django REST Framework
* SQLite

### Frontend

* React 18
* TypeScript
* Vite
* Vanilla CSS

### AI Assistance

* Google DeepMind Antigravity

---

## 📂 Project Structure

```text
project-root/
│
├── backend/
│   ├── expenses/
│   ├── manage.py
│   └── db.sqlite3
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── README.md
├── SCOPE.md
├── DECISIONS.md
└── AI_USAGE.md
```

---

## ⚙️ Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd settled-io
```

---

## Backend Setup

Navigate to backend:

```bash
cd backend
```

Create virtual environment:

```bash
python -m venv venv
```

Activate environment:

### Windows

```powershell
.\venv\Scripts\Activate.ps1
```

### Linux/macOS

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Apply migrations:

```bash
python manage.py migrate
```

Run server:

```bash
python manage.py runserver
```

Backend URL:

```text
http://localhost:8000
```

---

## Frontend Setup

Navigate to frontend:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start development server:

```bash
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

---

## 🧪 Running Tests

Backend test suite:

```bash
python manage.py test expenses.tests
```

Tests cover:

* Balance calculations
* Debt minimization
* Membership restrictions
* Currency handling
* CSV anomaly detection
* Settlement workflows

---

## 🗄 Database Schema

### Main Tables

| Table                    | Purpose                      |
| ------------------------ | ---------------------------- |
| auth_user                | User accounts                |
| expenses_group           | Expense groups               |
| expenses_groupmembership | Membership timeline tracking |
| expenses_expense         | Expense records              |
| expenses_expensesplit    | Split allocations            |
| expenses_payment         | Settlement payments          |
| expenses_importreport    | Import audit logs            |

---

## 🧠 Key Design Decisions

### Django REST + React

Chosen to provide:

* Clean frontend/backend separation
* Scalable architecture
* Better user experience
* Easier testing

### SQLite Database

Selected because:

* Zero configuration
* Relational database compliance
* Easy local setup
* Portable development environment

### Debt Minimization

Implemented Splitwise-style settlement optimization to reduce the number of required transactions.

### Interactive CSV Review

Instead of silently modifying data, users review and approve corrections before import.

---

## 📈 User Personas

### Aisha

* Simplified settlement view
* Minimal transactions
* Easy payment instructions

### Rohan

* Detailed ledger visibility
* Transparent calculations
* Balance explanations

### Meera

* Interactive CSV correction workflow
* Approval-based imports

### Sam

* Membership timeline enforcement
* Fair expense allocation

---

## 🤖 AI Usage

AI assistance was used for:

* Architecture planning
* Model generation
* Test creation
* Development acceleration

All AI-generated outputs were manually reviewed, tested, and corrected where necessary.

Documented correction examples include:

* Balance calculation bug fixes
* Import validation improvements
* Search performance optimization

---

## 🔒 Future Improvements

* JWT Authentication
* PostgreSQL Support
* Real-time notifications
* Mobile application
* OCR receipt scanning
* Exchange-rate API integration
* Export to Excel/PDF
* Advanced analytics dashboard

---

## 📄 License

This project was developed as part of a Software Engineering technical assignment and is intended for educational and evaluation purposes.

---

## 👨‍💻 Author

**Ritik Kumar**

B.Tech Computer Science Engineering

Built with Django, React, TypeScript, and SQLite.
