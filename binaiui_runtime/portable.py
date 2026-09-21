"""Portable compressed snapshots for moving BINAIUI state between environments."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from .store import MemoryStore


def write_snapshot(store: MemoryStore, path: str | Path) -> dict:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = store.snapshot_payload()
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    with gzip.open(target, "wb", compresslevel=9) as fh:
        fh.write(raw)
    return {
        "path": str(target),
        "bytes": target.stat().st_size,
        "sources": len(payload["sources"]),
        "runs": len(payload["runs"]),
        "turns": len(payload["turns"]),
        "corpus_hash": payload["corpus_hash"],
    }


def read_snapshot(store: MemoryStore, path: str | Path, *, replace: bool = False) -> dict:
    source = Path(path)
    with gzip.open(source, "rb") as fh:
        payload = json.loads(fh.read().decode("utf-8"))
    store.restore_payload(payload, replace=replace)
    return {
        "path": str(source),
        "sources": store.source_count(),
        "repos": store.repo_counts(),
        "corpus_hash": store.corpus_hash(),
        "integrity": store.integrity_check(),
    }
