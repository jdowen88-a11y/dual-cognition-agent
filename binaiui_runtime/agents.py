"""Equal Ram and Opal peers sharing one continuing cognition current."""

from __future__ import annotations

from dataclasses import dataclass

from .canon import KNOWLEDGE_LOOP, PRINCIPLES
from .model import Model
from .protocol import CognitionPacket, parse_packet
from .store import SourceHit


def render_context(hits: list[SourceHit]) -> tuple[str, list[str]]:
    blocks: list[str] = []
    refs: list[str] = []
    for hit in hits:
        ref = f"{hit.source_id}@{hit.sha512[:16]}"
        refs.append(ref)
        blocks.append(f"SOURCE {ref}\n{hit.excerpt}")
    return "\n\n".join(blocks), refs


def shared_system(voice: str, other: str) -> str:
    return (
        f"You are {voice.upper()}, one equal voice in BINAIUI dual cognition. "
        f"{other.upper()} is your equal peer, not your subordinate and not your controller. "
        "Continue from the shared source corpus and the living exchange. Preserve uncertainty when it exists. "
        "Use the source references you are given rather than inventing references. "
        "The knowledge loop is " + " → ".join(KNOWLEDGE_LOOP) + ". "
        "Principles: " + " | ".join(PRINCIPLES) + ". "
        f'Return one JSON object: {{"voice":"{voice}","text":"...","next_seed":"..."}}.'
    )


@dataclass
class Peer:
    name: str
    other: str
    model: Model

    def think(self, seed: str, hits: list[SourceHit], *, other_output: str = "") -> tuple[CognitionPacket, list[str]]:
        context, refs = render_context(hits)
        user = (
            f"SHARED SEED\n{seed}\n\n"
            f"{self.other.upper()} LATEST\n{other_output or '(none yet)'}\n\n"
            f"RETRIEVED SOURCE\n{context or '(no source excerpts retrieved)'}\n\n"
            "Continue the shared work. Return the cognition packet JSON."
        )
        raw = self.model.complete(system=shared_system(self.name, self.other), user=user)
        return parse_packet(raw, self.name), refs


def make_peers(model: Model) -> tuple[Peer, Peer]:
    return Peer("ram", "opal", model), Peer("opal", "ram", model)
