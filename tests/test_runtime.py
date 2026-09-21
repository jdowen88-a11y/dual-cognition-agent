from pathlib import Path

from binaiui_runtime.loop import BinaiuiLoop
from binaiui_runtime.model import DeterministicModel
from binaiui_runtime.sources import ingest_local
from binaiui_runtime.store import MemoryStore


def test_ingest_priority_and_resume(tmp_path: Path):
    root = tmp_path / "BINAIUI"
    root.mkdir()
    (root / "CORE.md").write_text("observe measure encode hash reproduce falsify RAM OPAL", encoding="utf-8")
    store = MemoryStore(tmp_path / "state.sqlite3")
    try:
        assert ingest_local(store, [root]) == 1
        hits = store.search("reproduce falsify")
        assert hits and hits[0].priority == 100

        loop = BinaiuiLoop(store, DeterministicModel())
        first = loop.run("seed", cycles=1, run_id="r1")
        assert first.cycles_completed == 1
        assert len(store.turns("r1")) == 2

        second = loop.run("ignored-new-seed", cycles=1, run_id="r1")
        assert second.cycles_completed == 1
        turns = store.turns("r1")
        assert len(turns) == 4
        assert turns[-1]["cycle"] == 2
    finally:
        store.close()


def test_no_external_action_path(tmp_path: Path):
    store = MemoryStore(tmp_path / "state.sqlite3")
    try:
        loop = BinaiuiLoop(store, DeterministicModel())
        result = loop.run("propose a deployment", cycles=1, run_id="safe")
        assert result.last_output
        assert store.status("safe")[0]["status"] == "idle"
    finally:
        store.close()
