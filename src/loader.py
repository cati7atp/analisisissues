"""Read-only loader for the miner.db SQLite dataset."""

import sqlite3
from typing import Iterator

from .config import InputConfig
from .models import RawIssue

ITEM_QUERY = (
    "SELECT repo, number, title, body, state, author, created_at, closed_at "
    "FROM items ORDER BY repo, number"
)


def _connect_readonly(db_path) -> sqlite3.Connection:
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def load_items_sqlite(cfg: InputConfig) -> Iterator[RawIssue]:
    """Yield one RawIssue per item row, streaming from a read-only connection."""
    conn = _connect_readonly(cfg.db_path)
    try:
        for row in conn.execute(ITEM_QUERY):
            yield RawIssue(
                repo=row["repo"],
                issue_number=row["number"],
                title=row["title"] or "",
                body=row["body"],
                state=row["state"],
                author=row["author"],
                created_at=row["created_at"],
                closed_at=row["closed_at"],
            )
    finally:
        conn.close()
