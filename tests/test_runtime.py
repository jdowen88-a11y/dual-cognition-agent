from pathlib import Path

from binaiui_runtime.loop import BinaiuiLoop
from binaiui_runtime.model import DeterministicModel
from binaiui_runtime.sources import ingest_local
from binaiui_runtime.store import MemoryStore
from binaiui_runtime.stream import LiveStream


def test_ingest_priority_resume_and_live_stream(tmp_path: Path):
    root = tmp_path / "BINAIUI"
    root.mkdir()
    (root / "CORE.md").write_text(
        "observe measure encode hash reproduce falsify continue RAM OPAL",
        encoding="utf-8",
    )
    store = MemoryStore(tmp_path / "state.sqlite3")
    try:
        assert ingest_local(store, [root]) == 1
        hits = store.search("reproduce falsify")
        assert hits and hits[0].priority == 100

        stream = LiveStream(tmp_path / "live")
        loop = BinaiuiLoop(store, DeterministicModel(), stream=stream)

        first = loop.run("seed", cycles=1, run_id="r1")
        assert first.cycles_completed == 1
        assert len(store.turns("r1")) == 2
        assert {t["agent"] for t in store.turns("r1")} == {"ram", "opal"}
        assert (tmp_path / "live/current.txt").exists()
        assert (tmp_path / "live/ram.txt").exists()
        assert (tmp_path / "live/opal.txt").exists()

        second = loop.run("ignored-new-seed", cycles=1, run_id="r1")
        assert second.cycles_completed == 1
        turns = store.turns("r1")
        assert len(turns) == 4
        assert turns[-1]["cycle"] == 2
    finally:
        store.close()
