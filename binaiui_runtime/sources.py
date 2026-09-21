"""Source ingestion from local repository trees or GitHub's API."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .canon import SOURCE_PRIORITY_NAME
from .store import MemoryStore

TEXT_EXTENSIONS = {
    ".md", ".txt", ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx",
    ".json", ".jsonl", ".toml", ".yaml", ".yml", ".html", ".css", ".sql",
    ".sh", ".ini", ".cfg", ".csv", ".xml",
}
SKIP_DIRS = {".git", "node_modules", ".venv", "dist", "build", ".next", "coverage", "__pycache__"}


def _priority(repo: str) -> int:
    return 100 if repo.split("/")[-1].lower() == SOURCE_PRIORITY_NAME.lower() else 10


def ingest_local(store: MemoryStore, roots: Iterable[str | Path], *, max_bytes: int = 1_000_000) -> int:
    count = 0
    for root_value in roots:
        root = Path(root_value).expanduser().resolve()
        repo = root.name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.suffix.lower() not in TEXT_EXTENSIONS or path.stat().st_size > max_bytes:
                continue
            try:
                content = path.read_text("utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            store.upsert_source(repo=repo, path=str(path.relative_to(root)), content=content, priority=_priority(repo))
            count += 1
    return count


class GitHubReader:
    def __init__(self, token: str | None = None, api_base: str = "https://api.github.com") -> None:
        self.token = token or os.getenv("BINAIUI_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN")
        self.api_base = api_base.rstrip("/")

    def _get(self, path: str) -> object:
        req = Request(self.api_base + path)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", "binaiui-runtime")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise RuntimeError(f"GitHub API {exc.code}: {detail[:400]}") from exc

    def owned_repositories(self, owner: str) -> list[dict]:
        page = 1
        repos: list[dict] = []
        while True:
            data = self._get(f"/user/repos?per_page=100&page={page}&affiliation=owner&sort=full_name")
            if not isinstance(data, list):
                break
            matches = [r for r in data if str(r.get("owner", {}).get("login", "")).lower() == owner.lower()]
            repos.extend(matches)
            if len(data) < 100:
                break
            page += 1
        return repos

    def repository(self, full_name: str) -> dict:
        return dict(self._get(f"/repos/{full_name}"))

    def tree(self, full_name: str, branch: str) -> list[dict]:
        branch_data = dict(self._get(f"/repos/{full_name}/branches/{quote(branch, safe='')}"))
        commit_sha = branch_data["commit"]["sha"]
        commit = dict(self._get(f"/repos/{full_name}/git/commits/{commit_sha}"))
        tree_sha = commit["tree"]["sha"]
        tree = dict(self._get(f"/repos/{full_name}/git/trees/{tree_sha}?recursive=1"))
        return list(tree.get("tree", []))

    def blob_text(self, full_name: str, sha: str) -> str | None:
        blob = dict(self._get(f"/repos/{full_name}/git/blobs/{sha}"))
        if blob.get("encoding") != "base64":
            return None
        raw = base64.b64decode(str(blob.get("content", "")).replace("\n", ""))
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return None


def ingest_github(
    store: MemoryStore, *, owner: str, repos: Iterable[str] | None = None,
    token: str | None = None, max_bytes: int = 1_000_000,
) -> int:
    reader = GitHubReader(token=token)
    if repos:
        metadata = [reader.repository(r if "/" in r else f"{owner}/{r}") for r in repos]
    else:
        if not reader.token:
            raise RuntimeError("BINAIUI_GITHUB_TOKEN is required to enumerate all owned repositories")
        metadata = reader.owned_repositories(owner)

    metadata.sort(key=lambda r: (str(r.get("name", "")).lower() != SOURCE_PRIORITY_NAME.lower(), str(r.get("full_name", ""))))

    count = 0
    for repo in metadata:
        # GitHub reports an empty repository with size 0 and no usable branch/tree.
        if int(repo.get("size") or 0) == 0:
            continue
        full_name = str(repo["full_name"])
        branch = str(repo.get("default_branch") or "main")
        try:
            tree = reader.tree(full_name, branch)
        except RuntimeError:
            # A repo can exist without a commit, have a transiently unavailable
            # default branch, or be visible in metadata without readable contents.
            # One such repo must not abort the rest of the snapshot.
            continue
        for item in tree:
            if item.get("type") != "blob":
                continue
            path = str(item.get("path", ""))
            suffix = Path(path).suffix.lower()
            if suffix not in TEXT_EXTENSIONS or int(item.get("size") or 0) > max_bytes:
                continue
            if any(part in SKIP_DIRS for part in Path(path).parts):
                continue
            try:
                content = reader.blob_text(full_name, str(item["sha"]))
            except RuntimeError:
                continue
            if content is None:
                continue
            store.upsert_source(repo=full_name, path=path, content=content, priority=_priority(full_name))
            count += 1
    return count
