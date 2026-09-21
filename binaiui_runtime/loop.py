"""Resumable Ram/Opal loop implementing observe→measure→encode→hash→reproduce→falsify."""

from __future__ import annotations

from dataclasses import dataclass
import json
import time
import uuid

from .agents import Opal, Ram
from .model import Model
from .store import MemoryStore, digest


@dataclass(frozen=True)
class RunResult:
    run_id: str
    cycles_completed: int
    last_output: str
    last_hash: str


class BinaiuiLoop:
    def __init__(self, store: MemoryStore, model: Model, *, top_k: int = 8) -> None:
        self.store = store
        self.ram = Ram(model)
        self.opal = Opal(model)
        self.top_k = top_k

    def run(
        self, seed: str, *, cycles: int = 1, run_id: str | None = None,
        forever: bool = False, sleep_seconds: float = 30.0,
    ) -> RunResult:
        if cycles < 1:
            raise ValueError("cycles must be >= 1")
        run_id = run_id or uuid.uuid4().hex
        state = self.store.start_or_resume(run_id, seed)
        current = state.get("last_output") or seed
        cycle = int(state.get("cycle") or 0)
        completed = 0

        try:
            while forever or completed < cycles:
                cycle += 1

                hits = self.store.search(current, limit=self.top_k)
                refs = [f"{h.source_id}@{h.sha512[:16]}" for h in hits]

                encoded = json.dumps(
                    {"run_id": run_id, "cycle": cycle, "observation": current, "refs": refs},
                    ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                )
                observed_hash = digest(encoded)

                ram_output, ram_refs = self.ram.propose(current, hits)
                self.store.record_turn(
                    run_id=run_id, cycle=cycle, phase="reproduce", agent="ram",
                    input_text=observed_hash, output_text=ram_output, refs=ram_refs,
                )

                opal_output, opal_refs = self.opal.check(current, ram_output, hits)
                self.store.record_turn(
                    run_id=run_id, cycle=cycle, phase="falsify", agent="opal",
                    input_text=ram_output, output_text=opal_output, refs=opal_refs,
                )

                current = opal_output
                completed += 1
                if forever:
                    time.sleep(max(0.0, sleep_seconds))
        finally:
            self.store.finish(run_id)

        return RunResult(run_id=run_id, cycles_completed=completed, last_output=current, last_hash=digest(current))
