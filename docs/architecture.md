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

## Sample data and demo accounts

Sample data comes from `app/demo/personas.py`, which builds six months of records for one of three personas, ending with the last complete month. Generation is deterministic, so the same month always produces the same figures. Each load creates a `synthetic_data_runs` row owned by the borrower, and every generated record points to it through `synthetic_run_id`. Clearing sample data deletes the run, which cascades to its records, and also removes assessments that were based on sample data. Records the borrower entered themselves are never touched. Any analysis that includes sample records is flagged `is_synthetic`.

When `DEMO_MODE=true`, `python -m app.demo.seed` runs on startup and creates or resets three shared accounts (`users.is_demo = true`). They have random, unrecoverable passwords and are reached only through `POST /auth/demo/{persona}`. A shared dependency, `require_writable_borrower`, blocks any endpoint that changes records for demo accounts, so public visitors can't alter what others see. Saving assessment snapshots is still allowed, and the next restart wipes them.

## Production setup

Production images are separate from development ones. The frontend is built to static files and served by nginx, with the API URL fixed at build time. The backend runs without auto-reload or test tools, as a non-root user. Sign-up, sign-in and demo login are rate-limited per client IP (slowapi, in-memory, per worker). Interactive API docs can be turned off with `DOCS_ENABLED=false`. The API refuses to start with a JWT secret shorter than 32 bytes.

## Explicit limitations

Authentication is implemented, but email verification, password reset, refresh-token rotation, and administrative lender provisioning are not. Financial entry, descriptive assessment, suggestions and sample/demo data are implemented. Lender workflows, statement upload and ML are not. Sign-up, sign-in and demo logins are rate-limited per IP (30/minute), and sign-in attempts also per IP and email (5/minute). The rate limiter is in-memory and doesn't share counts across instances.
