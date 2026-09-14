# AVFU HRMS

One centralised Human Resource Management System for Assam Veterinary and
Fishery University — organisational structure, employee records,
promotions & history, reporting hierarchy, KYC/document verification, and
new-employee onboarding.

**Stack:** FastAPI + PostgreSQL (backend) · Next.js + TypeScript (frontend).

## Start here

- **[docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md)** — what the system
  does, who uses it, and why it's built the way it is. Read this first.
- **[docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)** — how to run it
  locally, the codebase map, the data model, the full API surface, and the
  conventions the code follows.

## Quick start

```powershell
# backend
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # edit DATABASE_URL / SECRET_KEY
python seed.py                 # builds schema + loads AVFU org structure
python -m uvicorn app.main:app --reload --port 8002

# frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Full details, demo login credentials, and troubleshooting are in
[docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md).
