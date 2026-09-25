"""Shared packet format for Ram and Opal."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re


@dataclass(frozen=True)
class CognitionPacket:
    voice: str
    text: str
    next_seed: str
    raw: str = ""


def _json_candidate(raw: str) -> str:
    stripped = raw.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else ""


def parse_packet(raw: str, voice: str) -> CognitionPacket:
    candidate = _json_candidate(raw)
    if candidate:
        try:
            payload = json.loads(candidate)
            if isinstance(payload, dict):
                text = str(payload.get("text") or payload.get("thought") or payload.get("content") or "").strip()
                next_seed = str(payload.get("next_seed") or text or raw).strip()
                return CognitionPacket(
                    voice=str(payload.get("voice") or voice).lower(),
                    text=text or raw.strip(),
                    next_seed=next_seed or raw.strip(),
                    raw=raw,
                )
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    text = raw.strip()
    return CognitionPacket(voice=voice.lower(), text=text, next_seed=text, raw=raw)
