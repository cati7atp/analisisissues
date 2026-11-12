"""Read-only loader for the miner.db SQLite dataset."""

import sqlite3
import json
from typing import Any, Iterator, List

from .config import InputConfig
from .models import RawComment, RawIssue

ITEM_QUERY = "SELECT * FROM items ORDER BY repo, number"
COMMENT_QUERY = (
    "SELECT kind, author, author_type, created_at, body FROM comments "
    "WHERE repo = ? AND item_number = ? AND kind IN ({kinds}) ORDER BY created_at, id"
)


def _json_list(raw: Any) -> List[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return [str(v) for v in value] if isinstance(value, list) else []


def _connect_readonly(db_path) -> sqlite3.Connection:
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def load_items_sqlite(cfg: InputConfig) -> Iterator[RawIssue]:
    """Yield one RawIssue per item row, streaming from a read-only connection."""
    conn = _connect_readonly(cfg.db_path)
    comment_sql = COMMENT_QUERY.format(kinds=",".join("?" * len(cfg.include_comment_kinds)))
    try:
        for row in conn.execute(ITEM_QUERY):
            comments = [
                RawComment(**dict(c))
                for c in conn.execute(
                    comment_sql, [row["repo"], row["number"], *cfg.include_comment_kinds]
                )
            ]
            yield RawIssue(
                repo=row["repo"],
                issue_number=row["number"],
                title=row["title"] or "",
                body=row["body"],
                state=row["state"],
                author=row["author"],
                created_at=row["created_at"],
                closed_at=row["closed_at"],
                labels=_json_list(row["labels"]),
                assignees=_json_list(row["assignees"]),
                milestone=row["milestone"],
                comments=comments,
                item_type=row["type"],
                state_reason=row["state_reason"],
                author_type=row["author_type"],
                merged_at=row["merged_at"],
                comment_count=row["comment_count"],
                complete=row["complete"],
                draft=row["draft"],
                category=row["category"],
            )
    finally:
        conn.close()
