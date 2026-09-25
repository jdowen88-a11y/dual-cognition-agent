from pathlib import Path

from binaiui_runtime.portable import read_snapshot, write_snapshot
from binaiui_runtime.store import MemoryStore


def test_corpus_hash_is_stable_for_same_sources(tmp_path: Path):
    a = MemoryStore(tmp_path / "a.sqlite3")
    b = MemoryStore(tmp_path / "b.sqlite3")
    try:
        a.upsert_source(repo="other", path="b.md", content="beta", priority=10)
        a.upsert_source(repo="BINAIUI", path="a.md", content="alpha", priority=100)

        b.upsert_source(repo="BINAIUI", path="a.md", content="alpha", priority=100)
        b.upsert_source(repo="other", path="b.md", content="beta", priority=10)

        assert a.corpus_hash() == b.corpus_hash()
        assert a.repo_counts() == {"BINAIUI": 1, "other": 1}
    finally:
        a.close()
        b.close()


def test_snapshot_roundtrip_preserves_shared_current(tmp_path: Path):
    source = MemoryStore(tmp_path / "source.sqlite3")
    target = MemoryStore(tmp_path / "target.sqlite3")
    snapshot = tmp_path / "state.json.gz"
    try:
        source.upsert_source(repo="BINAIUI", path="CORE.md", content="RAM OPAL", priority=100)
        source.start_or_resume("main", "seed")
        source.record_turn(
            run_id="main",
            cycle=1,
            phase="continue",
            agent="ram",
            input_text="input",
            output_text="ram continuation",
            refs=["BINAIUI:CORE.md@abc"],
        )
        source.record_turn(
            run_id="main",
            cycle=1,
            phase="continue",
            agent="opal",
            input_text="ram continuation",
            output_text="opal continuation",
            refs=["BINAIUI:CORE.md@abc"],
        )
        shared = "RAM\nram continuation\n\nOPAL\nopal continuation"
        source.set_current(run_id="main", cycle=1, output=shared)
        source.finish("main")

        before = source.corpus_hash()
        meta = write_snapshot(source, snapshot)
        assert meta["sources"] == 1
        assert snapshot.exists()

        restored = read_snapshot(target, snapshot, replace=True)
        assert restored["integrity"] == "ok"
        assert target.corpus_hash() == before
        assert target.source_count() == 1
        assert len(target.turns("main")) == 2
        assert target.status("main")[0]["last_output"] == shared
    finally:
        source.close()
        target.close()
