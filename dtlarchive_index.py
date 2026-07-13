"""Persistent SQLite index used by DTLarchive."""

from __future__ import annotations

import datetime as dt
import hashlib
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence


@dataclass
class StoredMessage:
    id: str
    role: str
    text: str
    create_time: float | None = None


@dataclass
class StoredConversation:
    source_file: str
    id: str
    title: str
    create_time: float | None
    update_time: float | None
    messages: list[StoredMessage] = field(default_factory=list)


@dataclass
class IndexUpdate:
    imported_files: int = 0
    unchanged_files: int = 0
    imported_conversations: int = 0


def _fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _fallback_conversation_id(path: Path, conversation: Any) -> str:
    identity = (
        f"{path.resolve()}|{getattr(conversation, 'title', '')}|"
        f"{getattr(conversation, 'create_time', '')}|{getattr(conversation, 'update_time', '')}"
    )
    return "local-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _fts_prefix(term: str) -> str:
    value = unicodedata.normalize("NFKD", term or "")
    value = "".join(character for character in value if not unicodedata.combining(character)).lower()
    tokens = re.findall(r"[a-z0-9_]+", value)
    if not tokens:
        return '"__dtlarchive_no_token__"'
    token = tokens[0].replace('"', '""')
    return f'"{token}"*'


class ArchiveIndex:
    """Incremental archive importer and indexed conversation repository."""

    SCHEMA_VERSION = "1"

    def __init__(self, path: Path):
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self._initialize()

    def __enter__(self) -> "ArchiveIndex":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    def _initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY,
                path TEXT NOT NULL UNIQUE,
                size INTEGER NOT NULL,
                mtime_ns INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                indexed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                create_time REAL,
                update_time REAL,
                content_timestamp REAL NOT NULL DEFAULT 0,
                message_count INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                ordinal INTEGER NOT NULL,
                external_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                create_time REAL,
                text TEXT NOT NULL,
                UNIQUE(conversation_id, ordinal)
            );
            CREATE TABLE IF NOT EXISTS source_conversations (
                source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
                conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                PRIMARY KEY(source_id, conversation_id)
            );
            CREATE INDEX IF NOT EXISTS ix_messages_conversation
                ON messages(conversation_id, ordinal);
            CREATE INDEX IF NOT EXISTS ix_conversations_dates
                ON conversations(create_time, update_time);
            CREATE VIRTUAL TABLE IF NOT EXISTS search_fts USING fts5(
                conversation_id UNINDEXED,
                role UNINDEXED,
                text,
                tokenize = 'unicode61 remove_diacritics 2'
            );
            """
        )
        current = self.connection.execute(
            "SELECT value FROM metadata WHERE key = 'schema_version'"
        ).fetchone()
        if current and current["value"] != self.SCHEMA_VERSION:
            raise RuntimeError(
                f"Version d'index incompatible : {current['value']} (attendue : {self.SCHEMA_VERSION})."
            )
        self.connection.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES('schema_version', ?)",
            (self.SCHEMA_VERSION,),
        )
        self.connection.commit()

    def clear(self) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM search_fts")
            self.connection.execute("DELETE FROM source_conversations")
            self.connection.execute("DELETE FROM messages")
            self.connection.execute("DELETE FROM conversations")
            self.connection.execute("DELETE FROM sources")

    def update(
        self,
        files: Sequence[Path],
        loader: Callable[[Path], Iterable[Any]],
        *,
        force: bool = False,
        progress: Callable[[Path], None] | None = None,
    ) -> IndexUpdate:
        result = IndexUpdate()
        for path in files:
            if progress:
                progress(path)
            state = path.stat()
            resolved = str(path.resolve())
            source = self.connection.execute(
                "SELECT * FROM sources WHERE path = ?", (resolved,)
            ).fetchone()
            if (
                not force
                and source
                and source["size"] == state.st_size
                and source["mtime_ns"] == state.st_mtime_ns
            ):
                result.unchanged_files += 1
                continue

            digest = _fingerprint(path)
            if not force and source and source["sha256"] == digest:
                with self.connection:
                    self.connection.execute(
                        "UPDATE sources SET size = ?, mtime_ns = ?, indexed_at = ? WHERE id = ?",
                        (state.st_size, state.st_mtime_ns, dt.datetime.now().isoformat(), source["id"]),
                    )
                result.unchanged_files += 1
                continue

            conversations = list(loader(path))
            with self.connection:
                if source:
                    source_id = int(source["id"])
                    self.connection.execute(
                        "UPDATE sources SET size = ?, mtime_ns = ?, sha256 = ?, indexed_at = ? WHERE id = ?",
                        (state.st_size, state.st_mtime_ns, digest, dt.datetime.now().isoformat(), source_id),
                    )
                    self.connection.execute(
                        "DELETE FROM source_conversations WHERE source_id = ?", (source_id,)
                    )
                else:
                    cursor = self.connection.execute(
                        "INSERT INTO sources(path, size, mtime_ns, sha256, indexed_at) VALUES(?, ?, ?, ?, ?)",
                        (resolved, state.st_size, state.st_mtime_ns, digest, dt.datetime.now().isoformat()),
                    )
                    source_id = int(cursor.lastrowid)

                for conversation in conversations:
                    conversation_id = str(getattr(conversation, "id", "") or "")
                    if not conversation_id:
                        conversation_id = _fallback_conversation_id(path, conversation)
                    messages = list(getattr(conversation, "messages", []))
                    incoming_timestamp = float(
                        getattr(conversation, "update_time", None)
                        or getattr(conversation, "create_time", None)
                        or 0
                    )
                    existing = self.connection.execute(
                        "SELECT content_timestamp, message_count FROM conversations WHERE id = ?",
                        (conversation_id,),
                    ).fetchone()
                    replace_content = not existing or (
                        incoming_timestamp,
                        len(messages),
                    ) >= (float(existing["content_timestamp"]), int(existing["message_count"]))
                    if not existing:
                        self.connection.execute(
                            """
                            INSERT INTO conversations(
                                id, title, create_time, update_time, content_timestamp, message_count
                            ) VALUES(?, ?, ?, ?, ?, ?)
                            """,
                            (
                                conversation_id,
                                str(getattr(conversation, "title", "") or "(sans titre)"),
                                getattr(conversation, "create_time", None),
                                getattr(conversation, "update_time", None),
                                incoming_timestamp,
                                len(messages),
                            ),
                        )
                    elif replace_content:
                        self.connection.execute(
                            """
                            UPDATE conversations
                            SET title = ?, create_time = ?, update_time = ?,
                                content_timestamp = ?, message_count = ?
                            WHERE id = ?
                            """,
                            (
                                str(getattr(conversation, "title", "") or "(sans titre)"),
                                getattr(conversation, "create_time", None),
                                getattr(conversation, "update_time", None),
                                incoming_timestamp,
                                len(messages),
                                conversation_id,
                            ),
                        )

                    if replace_content:
                        self.connection.execute(
                            "DELETE FROM messages WHERE conversation_id = ?", (conversation_id,)
                        )
                        self.connection.execute(
                            "DELETE FROM search_fts WHERE conversation_id = ?", (conversation_id,)
                        )
                        title = str(getattr(conversation, "title", "") or "(sans titre)")
                        self.connection.execute(
                            "INSERT INTO search_fts(conversation_id, role, text) VALUES(?, 'title', ?)",
                            (conversation_id, title),
                        )
                        for ordinal, message in enumerate(messages):
                            role = str(getattr(message, "role", ""))
                            text = str(getattr(message, "text", "") or "")
                            if role not in {"user", "assistant"} or not text:
                                continue
                            self.connection.execute(
                                """
                                INSERT INTO messages(
                                    conversation_id, ordinal, external_id, role, create_time, text
                                ) VALUES(?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    conversation_id,
                                    ordinal,
                                    str(getattr(message, "id", "") or ordinal),
                                    role,
                                    getattr(message, "create_time", None),
                                    text,
                                ),
                            )
                            self.connection.execute(
                                "INSERT INTO search_fts(conversation_id, role, text) VALUES(?, ?, ?)",
                                (conversation_id, role, text),
                            )
                    self.connection.execute(
                        "INSERT OR IGNORE INTO source_conversations(source_id, conversation_id) VALUES(?, ?)",
                        (source_id, conversation_id),
                    )

                self.connection.execute(
                    "DELETE FROM conversations WHERE id NOT IN (SELECT conversation_id FROM source_conversations)"
                )
            result.imported_files += 1
            result.imported_conversations += len(conversations)
        return result

    def source_ids(self, files: Sequence[Path]) -> list[int]:
        paths = [str(path.resolve()) for path in files]
        if not paths:
            return []
        placeholders = ",".join("?" for _ in paths)
        rows = self.connection.execute(
            f"SELECT id FROM sources WHERE path IN ({placeholders})", paths
        ).fetchall()
        return [int(row["id"]) for row in rows]

    @staticmethod
    def _source_filter(source_ids: Sequence[int], alias: str = "c") -> tuple[str, list[Any]]:
        placeholders = ",".join("?" for _ in source_ids)
        sql = (
            "EXISTS (SELECT 1 FROM source_conversations sc "
            f"WHERE sc.conversation_id = {alias}.id AND sc.source_id IN ({placeholders}))"
        )
        return sql, list(source_ids)

    def archive_bounds(self, source_ids: Sequence[int]) -> tuple[dt.datetime, dt.datetime] | None:
        if not source_ids:
            return None
        source_filter, parameters = self._source_filter(source_ids)
        row = self.connection.execute(
            f"""
            SELECT MIN(COALESCE(create_time, update_time)) AS minimum,
                   MAX(COALESCE(create_time, update_time)) AS maximum
            FROM conversations c WHERE {source_filter}
            """,
            parameters,
        ).fetchone()
        if not row or row["minimum"] is None or row["maximum"] is None:
            return None
        return (
            dt.datetime.fromtimestamp(float(row["minimum"])),
            dt.datetime.fromtimestamp(float(row["maximum"])),
        )

    def _candidate_ids_for_term(
        self,
        source_ids: Sequence[int],
        term: str,
        role_scope: str,
        start_timestamp: float | None,
        end_timestamp: float | None,
    ) -> set[str]:
        source_filter, source_parameters = self._source_filter(source_ids)
        roles = ["title", "user", "assistant"] if role_scope == "both" else ["title", role_scope]
        role_placeholders = ",".join("?" for _ in roles)
        conditions = [source_filter, f"f.role IN ({role_placeholders})", "search_fts MATCH ?"]
        parameters: list[Any] = [*source_parameters, *roles, _fts_prefix(term)]
        if start_timestamp is not None:
            conditions.append("COALESCE(c.create_time, c.update_time) >= ?")
            parameters.append(start_timestamp)
        if end_timestamp is not None:
            conditions.append("COALESCE(c.create_time, c.update_time) <= ?")
            parameters.append(end_timestamp)
        rows = self.connection.execute(
            f"""
            SELECT DISTINCT f.conversation_id
            FROM search_fts f
            JOIN conversations c ON c.id = f.conversation_id
            WHERE {' AND '.join(conditions)}
            """,
            parameters,
        ).fetchall()
        return {str(row["conversation_id"]) for row in rows}

    def candidate_ids(
        self,
        source_ids: Sequence[int],
        terms: Sequence[Any],
        role_scope: str,
        start_date: dt.datetime | None,
        end_date: dt.datetime | None,
    ) -> set[str]:
        if not source_ids:
            return set()
        start_timestamp = start_date.timestamp() if start_date else None
        end_timestamp = end_date.timestamp() if end_date else None
        groups: dict[int, list[Any]] = {}
        for term in terms:
            if getattr(term, "excluded", False):
                continue
            else:
                groups.setdefault(int(getattr(term, "group", 0)), []).append(term)

        candidates: set[str] = set()
        for group_terms in groups.values():
            group_candidates: set[str] | None = None
            for term in group_terms:
                matches = self._candidate_ids_for_term(
                    source_ids,
                    str(getattr(term, "text", "")),
                    role_scope,
                    start_timestamp,
                    end_timestamp,
                )
                group_candidates = matches if group_candidates is None else group_candidates & matches
            if group_candidates:
                candidates |= group_candidates

        return candidates

    def load_conversations(
        self, conversation_ids: Sequence[str], source_ids: Sequence[int]
    ) -> list[StoredConversation]:
        if not conversation_ids or not source_ids:
            return []
        conversation_placeholders = ",".join("?" for _ in conversation_ids)
        source_placeholders = ",".join("?" for _ in source_ids)
        rows = self.connection.execute(
            f"""
            SELECT c.*, MIN(s.path) AS source_path
            FROM conversations c
            JOIN source_conversations sc ON sc.conversation_id = c.id
            JOIN sources s ON s.id = sc.source_id
            WHERE c.id IN ({conversation_placeholders})
              AND sc.source_id IN ({source_placeholders})
            GROUP BY c.id
            """,
            [*conversation_ids, *source_ids],
        ).fetchall()
        result: list[StoredConversation] = []
        for row in rows:
            message_rows = self.connection.execute(
                """
                SELECT external_id, role, text, create_time
                FROM messages WHERE conversation_id = ? ORDER BY ordinal
                """,
                (row["id"],),
            ).fetchall()
            source_file = Path(str(row["source_path"] or "archive.json")).name
            result.append(
                StoredConversation(
                    source_file=source_file,
                    id=str(row["id"]),
                    title=str(row["title"]),
                    create_time=row["create_time"],
                    update_time=row["update_time"],
                    messages=[
                        StoredMessage(
                            id=str(message["external_id"]),
                            role=str(message["role"]),
                            text=str(message["text"]),
                            create_time=message["create_time"],
                        )
                        for message in message_rows
                    ],
                )
            )
        return result

    def conversation_count(
        self,
        source_ids: Sequence[int],
        start_date: dt.datetime | None,
        end_date: dt.datetime | None,
    ) -> int:
        if not source_ids:
            return 0
        source_filter, parameters = self._source_filter(source_ids)
        conditions = [source_filter]
        if start_date:
            conditions.append("COALESCE(c.create_time, c.update_time) >= ?")
            parameters.append(start_date.timestamp())
        if end_date:
            conditions.append("COALESCE(c.create_time, c.update_time) <= ?")
            parameters.append(end_date.timestamp())
        row = self.connection.execute(
            f"SELECT COUNT(*) AS count FROM conversations c WHERE {' AND '.join(conditions)}",
            parameters,
        ).fetchone()
        return int(row["count"])
