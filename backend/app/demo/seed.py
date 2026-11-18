"""Create or reset the shared demo accounts.

Run with ``python -m app.demo.seed``. Does nothing unless DEMO_MODE=true.
Safe to run repeatedly: each run replaces the demo accounts' data with fresh
sample data ending with the last complete month.
"""

from app.core.config import settings
from app.db.session import SessionLocal
from app.demo.personas import PERSONAS
from app.demo.service import seed_demo_account


def main() -> None:
    if not settings.demo_mode:
        print("DEMO_MODE is off; demo accounts not seeded.")
        return
    with SessionLocal() as db:
        for key in PERSONAS:
            seed_demo_account(db, key)
        db.commit()
    print(f"Seeded {len(PERSONAS)} demo accounts: {', '.join(PERSONAS)}")


if __name__ == "__main__":
    main()
