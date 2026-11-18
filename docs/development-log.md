# Development log

## 2026-11-18 â€” Initial foundation

- Repository inspection found an empty Git repository with no existing implementation.
- Chose a modular monolith using the requested stack, with a separate research area reserved for future experiments.
- Added borrower-only public account creation to prevent self-assigned lender privileges.
- Added PostgreSQL schema foundation for normalized financial records, borrower-authorized lender access, immutable assessment snapshots, indicator explanations, synthetic-data provenance, and audit metadata.
- Implemented password hashing, JWT sign-in, and authenticated current-user lookup.
- Added local Docker Compose services, environment template, README, and this decision log.
- Added monthly borrower CRUD for income, expenses, savings contributions, debt balances/payments, and liquid reserve snapshots.
- Added an independent, transparent baseline financial-health module, dashboard charts, recommendations, and versioned saved assessment snapshots.
- Added a migration for liquid reserve snapshots and assessment details.
- Deferred consent UX, synthetic data generation, lender screens, statement uploads, and ML until their appropriate phases.

## 2026-11-18: Shareable demo

- Ran the app end to end and fixed what testing found: API validation errors shown as "[object Object]", reserve records requiring a category, and an env file with secrets shipped in the archive. Secrets were rotated and the project put under git.
- Added test suites: pytest for indicators, suggestions, API ownership and validation, demo accounts and rate limiting (against a separate test database), and vitest for the frontend helpers. `scripts/check.sh` runs everything.
- Suggestions previously fired only at "attention" thresholds, so most users saw only "keep recording". Replaced them with rules for every watch/attention band, positive notes, missing-data prompts and three-month trends (`baseline-heuristic-v2`). Trend warnings rank ahead of threshold warnings because they point to a specific month.
- Added deterministic sample-data personas linked to `synthetic_data_runs` (migration 0003), so sample data is clearly marked and removable without touching the borrower's own records.
- Chose shared read-only demo accounts behind `DEMO_MODE` for the public demo, instead of publishing demo passwords: visitors can explore without registering, and no one can change what others see.
- Added production Dockerfiles (nginx static site; backend without reload or dev packages), per-IP rate limits, a switch to hide API docs, a minimum JWT secret length, and expired-session handling in the UI.
- Pinned rollup to 4.40.2: 4.68.6 failed to bundle react-dom ("Code is nested too deeply").
- Hosting choice deferred; the README lists what any Docker host needs.
