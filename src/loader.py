"""Read-only loader for the miner.db SQLite dataset."""

import sqlite3
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, List, Optional

from .config import InputConfig
from .models import RawComment, RawIssue, RejectionCounter, parse_datetime

ITEM_QUERY = "SELECT * FROM items WHERE type IN ({types}) ORDER BY repo, number"


class RejectionRatioExceeded(RuntimeError):
    """Raised when rejected rows exceed ``input.max_reject_ratio``."""


@dataclass
class LoadStats:
    loaded: int = 0
    excluded: int = 0
    rejections: RejectionCounter = field(default_factory=RejectionCounter)


def _rejection_reason(row: sqlite3.Row) -> Optional[str]:
    if not (row["repo"] or "").strip():
        return "missing_repo"
    if row["number"] is None:
        return "missing_number"
    try:
        parse_datetime(row["created_at"] or "")
    except Exception:
        return "bad_created_at"
    return None


def _write_rejections(stats: LoadStats, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for sample in stats.rejections.samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")


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


def load_items_sqlite(
    cfg: InputConfig,
    stats: Optional[LoadStats] = None,
    rejections_path: Optional[Path] = None,
) -> Iterator[RawIssue]:
    """Yield one RawIssue per usable item row, streaming from a read-only connection.

    Rows from ``exclude_repos`` are skipped and counted; rows with an unusable
    repo, number or created_at are rejected by reason. After the last row the
    rejections are written (when a path is given) and the reject ratio checked.
    """
    stats = stats if stats is not None else LoadStats()
    conn = _connect_readonly(cfg.db_path)
    comment_sql = COMMENT_QUERY.format(kinds=",".join("?" * len(cfg.include_comment_kinds)))
    item_sql = ITEM_QUERY.format(types=",".join("?" * len(cfg.item_types)))
    excluded = set(cfg.exclude_repos)
    try:
        for row in conn.execute(item_sql, cfg.item_types):
            if row["repo"] in excluded:
                stats.excluded += 1
                continue
            reason = _rejection_reason(row)
            if reason:
                stats.rejections.add(reason, {
                    "repo": row["repo"], "number": row["number"], "created_at": row["created_at"],
                })
                continue
            comments = [
                RawComment(**dict(c))
                for c in conn.execute(
                    comment_sql, [row["repo"], row["number"], *cfg.include_comment_kinds]
                )
            ]
            stats.loaded += 1
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
    if rejections_path is not None:
        _write_rejections(stats, rejections_path)
    seen = stats.loaded + stats.rejections.total
    if seen and stats.rejections.total / seen > cfg.max_reject_ratio:
        raise RejectionRatioExceeded(
            f"{stats.rejections.total}/{seen} rows rejected "
            f"(limit {cfg.max_reject_ratio:.2%}): {dict(stats.rejections.by_reason)}"
        )
