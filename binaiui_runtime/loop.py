"""Persistent Ram ↔ Opal loop."""

from __future__ import annotations

from dataclasses import dataclass
import json
import time
import uuid

from .agents import make_peers
from .model import Model
from .store import MemoryStore, digest
from .stream import LiveStream


@dataclass(frozen=True)
class RunResult:
    run_id: str
    cycles_completed: int
    last_output: str
    last_hash: str


class BinaiuiLoop:
    def __init__(self, store: MemoryStore, model: Model, *, top_k: int = 8, stream: LiveStream | None = None) -> None:
        self.store = store
        self.ram, self.opal = make_peers(model)
        self.top_k = top_k
        self.stream = stream or LiveStream()

    def run(
        self,
        seed: str,
        *,
        cycles: int | None = None,
        run_id: str | None = None,
        sleep_seconds: float = 2.0,
    ) -> RunResult:
        if cycles is not None and cycles < 1:
            raise ValueError("cycles must be >= 1 when provided")

        run_id = run_id or uuid.uuid4().hex
        state = self.store.start_or_resume(run_id, seed)
        current = str(state.get("last_output") or seed)
        cycle = int(state.get("cycle") or 0)
        completed = 0
        last_ram = ""
        last_opal = ""

        try:
            while cycles is None or completed < cycles:
                cycle += 1
                hits = self.store.search(current, limit=self.top_k)
                refs = [f"{h.source_id}@{h.sha512[:16]}" for h in hits]
                observed_hash = digest(json.dumps(
                    {"run_id": run_id, "cycle": cycle, "observation": current, "refs": refs},
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ))

                order = (
                    [(self.ram, last_opal), (self.opal, last_ram)]
                    if cycle % 2
                    else [(self.opal, last_ram), (self.ram, last_opal)]
                )
                cycle_packets: dict[str, str] = {}

                for peer, previous_other in order:
                    other_now = next(iter(cycle_packets.values()), previous_other) if cycle_packets else previous_other
                    packet, peer_refs = peer.think(current, hits, other_output=other_now)
                    self.store.record_turn(
                        run_id=run_id,
                        cycle=cycle,
                        phase="continue",
                        agent=peer.name,
                        input_text=observed_hash + "\n" + other_now,
                        output_text=packet.raw or packet.text,
                        refs=peer_refs,
                    )
                    self.stream.write_turn(
                        run_id=run_id,
                        cycle=cycle,
                        voice=peer.name,
                        text=packet.text,
                        refs=peer_refs,
                    )
                    cycle_packets[peer.name] = packet.next_seed or packet.text
                    if peer.name == "ram":
                        last_ram = packet.text
                    else:
                        last_opal = packet.text

                current = (
                    f"RAM\n{cycle_packets.get('ram', last_ram)}\n\n"
                    f"OPAL\n{cycle_packets.get('opal', last_opal)}"
                ).strip()
                self.store.set_current(run_id=run_id, cycle=cycle, output=current)
                self.stream.write_current(current)
                completed += 1

                if cycles is None:
                    time.sleep(max(0.0, sleep_seconds))
        except KeyboardInterrupt:
            pass
        finally:
            self.store.finish(run_id)

        return RunResult(
            run_id=run_id,
            cycles_completed=completed,
            last_output=current,
            last_hash=digest(current),
        )
