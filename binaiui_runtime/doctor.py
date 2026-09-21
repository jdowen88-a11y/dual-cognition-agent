"""Runtime health checks that never expose secret values."""

from __future__ import annotations

import os
from pathlib import Path

from .store import MemoryStore


def doctor_report(store: MemoryStore) -> dict:
    db_parent = Path(store.path).parent
    return {
        "ok": store.integrity_check() == "ok",
        "database": str(store.path),
        "database_parent_exists": db_parent.exists(),
        "integrity": store.integrity_check(),
        "sources": store.source_count(),
        "repos": store.repo_counts(),
        "corpus_hash": store.corpus_hash(),
        "github_token_present": bool(os.getenv("BINAIUI_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN")),
        "model_key_present": bool(os.getenv("BINAIUI_API_KEY") or os.getenv("OPENAI_API_KEY")),
        "model_id_present": bool(os.getenv("BINAIUI_MODEL")),
        "api_base": os.getenv("BINAIUI_API_BASE", "https://api.openai.com/v1"),
    }
