# Credora initial architecture

## System shape

Credora starts as a modular monolith: React/TypeScript/Vite calls a FastAPI JSON API; SQLAlchemy persists to PostgreSQL; Alembic versions the schema. Financial calculations live in `app/intelligence/financial_health.py`, separate from route handlers. A separate `research/` package is reserved for reproducible experiments and future labelled-data modelling.

## Roles and access

Roles are borrower, lender, and admin. Public registration always creates a borrower. Lender accounts require controlled provisioning. A lender may read a borrower's assessment or financial information only through an active borrower-authorized `lender_access_grants` row. Every data endpoint must scope queries to the authenticated identity or an active grant. The grant table is foundation schema only; consent workflows and lender APIs are not yet implemented.

## Data model

Financial records use complete calendar-month reporting dates, currency, source/category, amount, and audit timestamps. Money uses PostgreSQL `NUMERIC`, not floating point. Savings contributions and month-end liquid reserve balances are stored separately. Assessments store a reporting window and methodology version; indicators store value, unit, availability, and explanation. Assessment rows preserve recommendation and label snapshots. Synthetic-data provenance is represented separately.

## Information flow

The frontend sends validated form data to the API. The API authenticates and authorizes the actor, validates inputs, then reads/writes records under borrower ownership. The assessment service calls the independent financial-intelligence module and persists a versioned result with indicator explanations and recommendations. Borrowers see their own records and results; lender endpoints are not implemented yet.

## Security baseline

Passwords are Argon2-hashed. API access uses short-lived signed JWT bearer tokens; token storage in the initial browser is local storage and should be revisited before production. Secrets come from environment configuration. Public registration does not accept a role. No government identifiers, bank credentials, or financial statement uploads are collected. Audit records are designed to record actions without copying sensitive payloads.

## Explicit limitations

Authentication is implemented, but email verification, password reset, refresh-token rotation, rate limiting, and administrative lender provisioning are not. Financial entry and descriptive assessment are implemented; lender workflows, synthetic demo-data loading, statement upload, and ML are not. The Docker setup is for development, not production deployment.
