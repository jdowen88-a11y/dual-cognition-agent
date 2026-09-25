"""Live append-only mirror of the continuing Ram ↔ Opal exchange."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path


class LiveStream:
    def __init__(self, root: str | Path = ".binaiui/live") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.events = self.root / "events.jsonl"

    def write_turn(self, *, run_id: str, cycle: int, voice: str, text: str, refs: list[str]) -> None:
        event = {
            "time": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "cycle": cycle,
            "voice": voice,
            "text": text,
            "refs": refs,
        }
        with self.events.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        (self.root / f"{voice}.txt").write_text(text, encoding="utf-8")

    def write_current(self, text: str) -> None:
        (self.root / "current.txt").write_text(text, encoding="utf-8")
