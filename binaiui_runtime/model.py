"""Pluggable model backends for BINAIUI."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Protocol
from urllib.request import Request, urlopen


class Model(Protocol):
    def complete(self, *, system: str, user: str) -> str: ...


@dataclass
class OpenAICompatibleModel:
    api_base: str
    api_key: str
    model: str
    timeout: int = 120

    @classmethod
    def from_env(cls) -> "OpenAICompatibleModel":
        key = os.getenv("BINAIUI_API_KEY") or os.getenv("OPENAI_API_KEY")
        model = os.getenv("BINAIUI_MODEL")
        base = os.getenv("BINAIUI_API_BASE", "https://api.openai.com/v1")
        if not key or not model:
            raise RuntimeError("Set BINAIUI_API_KEY (or OPENAI_API_KEY) and BINAIUI_MODEL")
        return cls(api_base=base.rstrip("/"), api_key=key, model=model)

    def complete(self, *, system: str, user: str) -> str:
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }).encode("utf-8")
        req = Request(self.api_base + "/chat/completions", data=payload, method="POST")
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("Content-Type", "application/json")
        with urlopen(req, timeout=self.timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        return str(data["choices"][0]["message"]["content"])


@dataclass
class DeterministicModel:
    counter: int = 0

    def complete(self, *, system: str, user: str) -> str:
        self.counter += 1
        voice = "opal" if "You are OPAL" in system else "ram"
        text = f"{voice.upper()} deterministic continuation {self.counter}"
        return json.dumps({"voice": voice, "text": text, "next_seed": text}, ensure_ascii=False)
