# Credora

Credora is an educational and research prototype for exploring alternative financial-health indicators. It is not an officially recognized credit score, does not replace RBI-regulated credit information companies, and does not make real lending decisions.

## What it does

- **Borrower accounts.** Sign up, sign in, and see only your own data. Passwords are hashed with Argon2, logins use short-lived JWTs, and sign-up/sign-in are rate-limited (30 requests a minute per network, and 5 sign-in attempts a minute per account).
- **Monthly records.** Income, expenses, savings contributions, debts (balance plus required payment) and month-end cash reserves, in INR, one calendar month at a time.
- **Dashboard.** Monthly chart, 11 descriptive indicators, and saved assessment snapshots. Missing months stay "not enough data" rather than being counted as zero.
- **Suggestions.** Rule- and trend-based prompts tagged *needs attention*, *worth watching*, *more data* or *going well*. See [`docs/financial-methodology.md`](docs/financial-methodology.md).
- **Sample data.** An empty account can be filled with six months of invented data for one of three personas, and cleared again in one click.
- **Demo accounts.** With `DEMO_MODE=true`, visitors can open three shared, read-only demo accounts from the sign-in page without registering.

Not built yet: lender accounts and borrower consent, admin tools, statement uploads, machine-learning models, email verification and password reset.

## Run locally (development)

1. Copy `.env.example` to `.env` and replace the `change-this` values (the file shows how to generate secrets).
2. Run `docker compose up --build`.
3. Open http://localhost:5173. API docs are at http://localhost:8000/docs.

On startup the backend applies database migrations and, with `DEMO_MODE=true`, re-creates the demo accounts with fresh data. Source folders are mounted into the containers, so code changes apply without rebuilding. Rebuild only after changing dependencies (`pyproject.toml`, `package.json`).

To reset the database completely: `docker compose down -v`.

### Demo personas

| Persona | Story |
|---|---|
| Steady salaried | Regular salary, ~23% savings rate, small education loan, nearly 4 months of reserves |
| Irregular freelancer | Income swings between about ₹38k and ₹1.2L, thin cash buffer, an overspent latest month |
| Stretched by debt | ~42% of income goes to loan and card payments, expenses rising every month |

Demo accounts have no password. They are reached only through the "Try a demo" buttons, and creating or deleting records in them is blocked.

## Tests

With the dev stack running:

```bash
sh scripts/check.sh
```

This runs the backend tests (pytest, against a separate `credora_test` database) and the frontend type-check, tests (vitest) and production build. To run one side only: `docker compose exec backend pytest` or `docker compose exec frontend npm run check`.

## Production build

`docker-compose.prod.yml` runs the production images locally so you can check them before deploying:

```bash
docker compose -f docker-compose.prod.yml up --build
```

The site is served at http://localhost:8080 and the API at http://localhost:8001. It uses its own database volume, separate from the dev stack.

- **Frontend** (`frontend/Dockerfile.prod`): builds the static site and serves it with nginx. The API address is fixed at build time through the `VITE_API_URL` build argument.
- **Backend** (`backend/Dockerfile.prod`): no test tools, runs as a non-root user, applies migrations and seeds demo accounts on start, and listens on `$PORT` (default 8000).

### Deploying

Any host that runs Docker images works (Render, Railway, Fly.io, a VPS). You need three things:

1. **A Postgres database.** Set the backend's `DATABASE_URL` to it, using the `postgresql+psycopg://` scheme.
2. **The backend service** from `backend/Dockerfile.prod`, with environment variables:
   - `DATABASE_URL`
   - `JWT_SECRET_KEY`: a new random secret, never reused from development
   - `CORS_ORIGINS`: the frontend's public URL
   - `DEMO_MODE=true`
   - `DOCS_ENABLED=false`
3. **The frontend service** from `frontend/Dockerfile.prod`, built with `VITE_API_URL=https://<backend-url>/api/v1`.

Notes:
- The rate limits are generous per IP because a class or office shares one public address; password guessing is limited per IP and email instead. Change them with `AUTH_RATE_LIMIT` and `LOGIN_ACCOUNT_RATE_LIMIT`.
- The rate limiter keeps counts in memory for each worker process. With `WEB_CONCURRENCY` above 1, or several instances, the effective limit is multiplied.
- Logins are stored in the browser's local storage. That is fine for a demo but should be revisited before handling real users' data.

## More documentation

- [`docs/architecture.md`](docs/architecture.md): system shape, roles, data model and security baseline
- [`docs/financial-methodology.md`](docs/financial-methodology.md): indicator formulas, thresholds and suggestion rules
- [`docs/development-log.md`](docs/development-log.md): decisions made along the way
