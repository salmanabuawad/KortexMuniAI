"""Small management CLI: ``python -m app.cli <command>``.

Commands:
  bootstrap   Seed RBAC, agents and the bootstrap admin (idempotent).
  health      Print AI provider + DB health.
"""

from __future__ import annotations

import asyncio
import sys

from app.core.logging import configure_logging, get_logger

logger = get_logger("muniai.cli")


def _bootstrap() -> None:
    from app.db.seed import seed_all
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        seed_all(db)
    logger.info("Bootstrap complete.")


def _health() -> None:
    from sqlalchemy import text

    from app.ai.registry import get_provider
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
        logger.info("Database: OK")
    h = asyncio.run(get_provider().health())
    logger.info("AI provider %s: %s (%s)", h.provider, "OK" if h.healthy else "DOWN", h.detail)


COMMANDS = {"bootstrap": _bootstrap, "health": _health}


def main() -> int:
    configure_logging()
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: python -m app.cli [{'|'.join(COMMANDS)}]")
        return 1
    COMMANDS[sys.argv[1]]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
