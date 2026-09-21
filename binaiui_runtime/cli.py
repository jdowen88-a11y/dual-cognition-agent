"""Command-line interface for bootstrap, ingestion, running, resume, snapshots, and health checks."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .doctor import doctor_report
from .loop import BinaiuiLoop
from .model import DeterministicModel, OpenAICompatibleModel
from .portable import read_snapshot, write_snapshot
from .sources import ingest_github, ingest_local
from .store import MemoryStore


DEFAULT_OWNER = os.getenv("BINAIUI_GITHUB_OWNER", "jdowen88-a11y")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="binaiui")
    p.add_argument("--db", default=".binaiui/state.sqlite3")
    sub = p.add_subparsers(dest="command", required=True)

    bootstrap = sub.add_parser("bootstrap", help="ingest the full GitHub corpus and optionally smoke-test resume")
    bootstrap.add_argument("--owner", default=DEFAULT_OWNER)
    bootstrap.add_argument("--repo", action="append", dest="repos")
    bootstrap.add_argument("--smoke", action="store_true")
    bootstrap.add_argument("--run-id", default="bootstrap-check")
    bootstrap.add_argument("--seed", default="Continue from the BINAIUI corpus without restarting.")

    local = sub.add_parser("ingest-local")
    local.add_argument("paths", nargs="+")

    gh = sub.add_parser("ingest-github")
    gh.add_argument("--owner", default=DEFAULT_OWNER)
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

    sub.add_parser("corpus", help="show the reproducible corpus identity and per-repo counts")
    sub.add_parser("doctor", help="check local state and whether required credentials are present")

    snapshot = sub.add_parser("snapshot", help="write a compressed portable state bundle")
    snapshot.add_argument("--out", default=".binaiui/binaiui.snapshot.json.gz")

    restore = sub.add_parser("restore", help="restore a compressed portable state bundle")
    restore.add_argument("path")
    restore.add_argument("--replace", action="store_true")

    export = sub.add_parser("export")
    export.add_argument("run_id")
    export.add_argument("--out", default="-")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    store = MemoryStore(args.db)
    try:
        if args.command == "bootstrap":
            n = ingest_github(store, owner=args.owner, repos=args.repos)
            result = {
                "imported": n,
                "total": store.source_count(),
                "repos": store.repo_counts(),
                "corpus_hash": store.corpus_hash(),
            }
            if args.smoke:
                smoke = BinaiuiLoop(store, DeterministicModel()).run(
                    args.seed, cycles=1, run_id=args.run_id
                )
                result["smoke"] = smoke.__dict__
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "ingest-local":
            n = ingest_local(store, args.paths)
            print(json.dumps({"imported": n, "total": store.source_count(), "corpus_hash": store.corpus_hash()}))
            return 0
        if args.command == "ingest-github":
            n = ingest_github(store, owner=args.owner, repos=args.repos)
            print(json.dumps({"imported": n, "total": store.source_count(), "corpus_hash": store.corpus_hash()}))
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
        if args.command == "corpus":
            print(json.dumps({
                "sources": store.source_count(),
                "repos": store.repo_counts(),
                "corpus_hash": store.corpus_hash(),
            }, ensure_ascii=False, indent=2))
            return 0
        if args.command == "doctor":
            report = doctor_report(store)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["ok"] else 1
        if args.command == "snapshot":
            print(json.dumps(write_snapshot(store, args.out), ensure_ascii=False, indent=2))
            return 0
        if args.command == "restore":
            print(json.dumps(read_snapshot(store, args.path, replace=args.replace), ensure_ascii=False, indent=2))
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
