"""Command-line interface for ingestion, running, resume, and export."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .loop import BinaiuiLoop
from .model import DeterministicModel, OpenAICompatibleModel
from .sources import ingest_github, ingest_local
from .store import MemoryStore


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="binaiui")
    p.add_argument("--db", default=".binaiui/state.sqlite3")
    sub = p.add_subparsers(dest="command", required=True)

    local = sub.add_parser("ingest-local")
    local.add_argument("paths", nargs="+")

    gh = sub.add_parser("ingest-github")
    gh.add_argument("--owner", required=True)
    gh.add_argument("--repo", action="append", dest="repos")

    run = sub.add_parser("run")
    run.add_argument("seed")
    run.add_argument("--cycles", type=int, default=1)
    run.add_argument("--run-id")
    run.add_argument("--forever", action="store_true")
    run.add_argument("--sleep", type=float, default=30.0)
    run.add_argument("--deterministic", action="store_true", help="test the loop without a remote model")

    status = sub.add_parser("status")
    status.add_argument("--run-id")

    export = sub.add_parser("export")
    export.add_argument("run_id")
    export.add_argument("--out", default="-")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    store = MemoryStore(args.db)
    try:
        if args.command == "ingest-local":
            n = ingest_local(store, args.paths)
            print(json.dumps({"imported": n, "total": store.source_count()}))
            return 0
        if args.command == "ingest-github":
            n = ingest_github(store, owner=args.owner, repos=args.repos)
            print(json.dumps({"imported": n, "total": store.source_count()}))
            return 0
        if args.command == "run":
            model = DeterministicModel() if args.deterministic else OpenAICompatibleModel.from_env()
            result = BinaiuiLoop(store, model).run(
                args.seed, cycles=args.cycles, run_id=args.run_id,
                forever=args.forever, sleep_seconds=args.sleep,
            )
            print(json.dumps(result.__dict__, ensure_ascii=False))
            return 0
        if args.command == "status":
            print(json.dumps(store.status(args.run_id), ensure_ascii=False, indent=2))
            return 0
        if args.command == "export":
            text = "\n".join(json.dumps(t, ensure_ascii=False) for t in store.turns(args.run_id)) + "\n"
            if args.out == "-":
                print(text, end="")
            else:
                Path(args.out).write_text(text, encoding="utf-8")
            return 0
        return 2
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
