# Credora

Credora is an educational and research prototype for exploring alternative financial-health indicators. It is not an officially recognized credit score, does not replace RBI-regulated credit information companies, and does not make real lending decisions.

## Current implementation

- React, TypeScript, and Vite borrower account interface.
- FastAPI API with borrower registration, login, JWT authentication, and `/auth/me`.
- Passwords hashed with Argon2 via `pwdlib`; successful registration and login events are recorded in the audit table.
- Borrower-only monthly entry for income, expenses, savings contributions, debt balances/payments, and month-end liquid reserves. Records can be listed and deleted.
- An authenticated borrower dashboard with monthly charts, financial-health indicators, recommendations, and saved assessment history.
- A separate financial-intelligence module computes descriptive indicators and persists versioned assessment snapshots. Missing data stays unavailable rather than being treated as zero.
- SQLAlchemy 2 models and Alembic migrations for users, profiles, financial records, access grants, assessments, indicators, synthetic runs, and audit logs.
- PostgreSQL and local Docker Compose development setup.
- Public registration can create borrower accounts only. Lender provisioning and borrower consent flows are not implemented yet, so no lender access endpoint is exposed.
- Portfolio screens, statement uploads, synthetic demo-data loading, and machine-learning models are not implemented yet.

## Run locally with Docker

1. Copy `.env.example` to `.env` and set `POSTGRES_PASSWORD` and a unique `JWT_SECRET_KEY` (at least 32 random bytes).
2. Run `docker compose up --build` from this directory. If the containers are already running, this rebuilds them with current code and applies the new database migration.
3. Open the frontend at `http://localhost:5173` and API documentation at `http://localhost:8000/docs`.

The backend applies Alembic migrations before starting. PostgreSQL data is kept in the `postgres_data` named volume.

## Run services separately

Backend: from `backend/`, create and activate a virtual environment, install with `pip install -e .`, configure `DATABASE_URL` and `JWT_SECRET_KEY`, run `alembic upgrade head`, then `uvicorn app.main:app --reload`.

Frontend: from `frontend/`, run `npm install` and `npm run dev`. Set `VITE_API_URL` if the API is not at `http://localhost:8000/api/v1`.

## Architecture

See [`docs/architecture.md`](docs/architecture.md) and [`docs/development-log.md`](docs/development-log.md) for the initial design and decisions.

Financial indicator definitions and limits are in [`docs/financial-methodology.md`](docs/financial-methodology.md).
