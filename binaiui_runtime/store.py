"""SQLite-backed source memory, corpus identity, and continuing journal."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha512
import json
from pathlib import Path
import re
import sqlite3
from typing import Iterable


SNAPSHOT_SCHEMA = 1


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(text: str) -> str:
    return sha512(text.encode("utf-8")).hexdigest()


def tokens(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[A-Za-z0-9_∞•→]+", text) if len(t) > 1}


@dataclass(frozen=True)
class SourceHit:
    source_id: str
    repo: str
    path: str
    sha512: str
    priority: int
    score: float
    excerpt: str


class MemoryStore:
    def __init__(self, path: str | Path = ".binaiui/state.sqlite3") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self.db.close()

    def _init_schema(self) -> None:
        self.db.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS sources (
              source_id TEXT PRIMARY KEY,
              repo TEXT NOT NULL,
              path TEXT NOT NULL,
              sha512 TEXT NOT NULL,
              content TEXT NOT NULL,
              priority INTEGER NOT NULL DEFAULT 10,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sources_repo ON sources(repo);
            CREATE TABLE IF NOT EXISTS runs (
              run_id TEXT PRIMARY KEY,
              seed TEXT NOT NULL,
              status TEXT NOT NULL,
              cycle INTEGER NOT NULL DEFAULT 0,
              last_output TEXT,
              last_hash TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS turns (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              run_id TEXT NOT NULL,
              cycle INTEGER NOT NULL,
              phase TEXT NOT NULL,
              agent TEXT NOT NULL,
              input_hash TEXT NOT NULL,
              output_hash TEXT NOT NULL,
              content TEXT NOT NULL,
              refs_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_turns_run_cycle ON turns(run_id, cycle, id);
            """
        )
        self.db.commit()

    def upsert_source(self, *, repo: str, path: str, content: str, priority: int = 10) -> str:
        source_id = f"{repo}:{path}"
        h = digest(content)
        self.db.execute(
            """INSERT INTO sources(source_id,repo,path,sha512,content,priority,updated_at)
               VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(source_id) DO UPDATE SET
                 sha512=excluded.sha512, content=excluded.content,
                 priority=excluded.priority, updated_at=excluded.updated_at""",
            (source_id, repo, path, h, content, priority, utcnow()),
        )
        self.db.commit()
        return source_id

    def source_count(self) -> int:
        return int(self.db.execute("SELECT COUNT(*) FROM sources").fetchone()[0])

    def repo_counts(self) -> dict[str, int]:
        rows = self.db.execute(
            "SELECT repo, COUNT(*) AS n FROM sources GROUP BY repo ORDER BY repo"
        ).fetchall()
        return {str(row["repo"]): int(row["n"]) for row in rows}

    def corpus_hash(self) -> str:
        rows = self.db.execute(
            "SELECT source_id,sha512,priority FROM sources ORDER BY source_id"
        ).fetchall()
        manifest = [
            {"source_id": row["source_id"], "sha512": row["sha512"], "priority": row["priority"]}
            for row in rows
        ]
        canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return digest(canonical)

    def integrity_check(self) -> str:
        row = self.db.execute("PRAGMA integrity_check").fetchone()
        return str(row[0]) if row else "unknown"

    def search(self, query: str, *, limit: int = 8) -> list[SourceHit]:
        q = tokens(query)
        rows = self.db.execute(
            "SELECT source_id,repo,path,sha512,content,priority FROM sources"
        ).fetchall()
        scored: list[SourceHit] = []
        for row in rows:
            body = row["content"]
            body_tokens = tokens(body)
            overlap = len(q & body_tokens)
            phrase = 2 if query.strip() and query.lower() in body.lower() else 0
            priority_bonus = row["priority"] / 100.0
            score = overlap + phrase + priority_bonus
            excerpt = self._excerpt(body, q)
            scored.append(
                SourceHit(
                    source_id=row["source_id"],
                    repo=row["repo"],
                    path=row["path"],
                    sha512=row["sha512"],
                    priority=row["priority"],
                    score=score,
                    excerpt=excerpt,
                )
            )
        scored.sort(key=lambda x: (x.score, x.priority, x.source_id), reverse=True)
        return scored[:limit]

    @staticmethod
    def _excerpt(content: str, q: set[str], *, max_chars: int = 1200) -> str:
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines:
            return ""
        ranked = sorted(lines, key=lambda line: len(tokens(line) & q), reverse=True)
        selected: list[str] = []
        size = 0
        for line in ranked:
            if line in selected:
                continue
            if size + len(line) + 1 > max_chars:
                continue
            selected.append(line)
            size += len(line) + 1
            if size >= max_chars * 0.75:
                break
        return "\n".join(selected)[:max_chars]

    def start_or_resume(self, run_id: str, seed: str) -> dict:
        row = self.db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if row:
            return dict(row)
        now = utcnow()
        self.db.execute(
            "INSERT INTO runs(run_id,seed,status,cycle,created_at,updated_at) VALUES(?,?,?,?,?,?)",
            (run_id, seed, "running", 0, now, now),
        )
        self.db.commit()
        return dict(self.db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone())

    def record_turn(
        self,
        *,
        run_id: str,
        cycle: int,
        phase: str,
        agent: str,
        input_text: str,
        output_text: str,
        refs: Iterable[str],
    ) -> None:
        self.db.execute(
            """INSERT INTO turns(run_id,cycle,phase,agent,input_hash,output_hash,content,refs_json,created_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                run_id,
                cycle,
                phase,
                agent,
                digest(input_text),
                digest(output_text),
                output_text,
                json.dumps(list(refs), ensure_ascii=False),
                utcnow(),
            ),
        )
        self.db.commit()

    def set_current(self, *, run_id: str, cycle: int, output: str) -> None:
        self.db.execute(
            """UPDATE runs SET cycle=?, last_output=?, last_hash=?, updated_at=?, status='running'
               WHERE run_id=?""",
            (cycle, output, digest(output), utcnow(), run_id),
        )
        self.db.commit()

    def finish(self, run_id: str) -> None:
        self.db.execute(
            "UPDATE runs SET status='idle', updated_at=? WHERE run_id=?",
            (utcnow(), run_id),
        )
        self.db.commit()

    def status(self, run_id: str | None = None) -> list[dict]:
        if run_id:
            rows = self.db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchall()
        else:
            rows = self.db.execute("SELECT * FROM runs ORDER BY updated_at DESC").fetchall()
        return [dict(r) for r in rows]

    def turns(self, run_id: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM turns WHERE run_id=? ORDER BY id",
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def snapshot_payload(self) -> dict:
        sources = [dict(r) for r in self.db.execute("SELECT * FROM sources ORDER BY source_id").fetchall()]
        runs = [dict(r) for r in self.db.execute("SELECT * FROM runs ORDER BY run_id").fetchall()]
        turns = [dict(r) for r in self.db.execute("SELECT * FROM turns ORDER BY id").fetchall()]
        return {
            "schema": SNAPSHOT_SCHEMA,
            "created_at": utcnow(),
            "corpus_hash": self.corpus_hash(),
            "sources": sources,
            "runs": runs,
            "turns": turns,
        }

    def restore_payload(self, payload: dict, *, replace: bool = False) -> None:
        if int(payload.get("schema", 0)) != SNAPSHOT_SCHEMA:
            raise ValueError("unsupported snapshot schema")
        sources = list(payload.get("sources", []))
        runs = list(payload.get("runs", []))
        turns = list(payload.get("turns", []))
        with self.db:
            if replace:
                self.db.execute("DELETE FROM turns")
                self.db.execute("DELETE FROM runs")
                self.db.execute("DELETE FROM sources")
            for row in sources:
                self.db.execute(
                    """INSERT OR REPLACE INTO sources(source_id,repo,path,sha512,content,priority,updated_at)
                       VALUES(?,?,?,?,?,?,?)""",
                    (
                        row["source_id"],
                        row["repo"],
                        row["path"],
                        row["sha512"],
                        row["content"],
                        row["priority"],
                        row["updated_at"],
                    ),
                )
            for row in runs:
                self.db.execute(
                    """INSERT OR REPLACE INTO runs(run_id,seed,status,cycle,last_output,last_hash,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (
                        row["run_id"],
                        row["seed"],
                        row["status"],
                        row["cycle"],
                        row.get("last_output"),
                        row.get("last_hash"),
                        row["created_at"],
                        row["updated_at"],
                    ),
                )
            for row in turns:
                self.db.execute(
                    """INSERT OR REPLACE INTO turns(id,run_id,cycle,phase,agent,input_hash,output_hash,content,refs_json,created_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (
                        row["id"],
                        row["run_id"],
                        row["cycle"],
                        row["phase"],
                        row["agent"],
                        row["input_hash"],
                        row["output_hash"],
                        row["content"],
                        row["refs_json"],
                        row["created_at"],
                    ),
                )
