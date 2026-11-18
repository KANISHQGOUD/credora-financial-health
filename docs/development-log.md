# Development log

## 2026-11-18 — Initial foundation

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
