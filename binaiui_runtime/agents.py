"""Ram proposes; Opal checks. Neither voice is erased."""

from __future__ import annotations

from dataclasses import dataclass

from .canon import KNOWLEDGE_LOOP, PRINCIPLES
from .model import Model
from .store import SourceHit


def render_context(hits: list[SourceHit]) -> tuple[str, list[str]]:
    blocks: list[str] = []
    refs: list[str] = []
    for hit in hits:
        ref = f"{hit.source_id}@{hit.sha512[:16]}"
        refs.append(ref)
        blocks.append(f"SOURCE {ref}\n{hit.excerpt}")
    return "\n\n".join(blocks), refs


@dataclass
class Ram:
    model: Model

    def propose(self, seed: str, hits: list[SourceHit]) -> tuple[str, list[str]]:
        context, refs = render_context(hits)
        system = (
            "You are RAM, the generative voice in BINAIUI's paired cognition loop. "
            "Propose a continuation grounded in the supplied source excerpts. Preserve uncertainty. "
            "Do not invent a source reference. Do not execute, trade, deploy, spend, message, or mutate external systems. "
            "Internal ideas may remain unresolved. The knowledge loop is: " + " → ".join(KNOWLEDGE_LOOP) + ". "
            "Relevant principles: " + " | ".join(PRINCIPLES)
        )
        user = f"SEED\n{seed}\n\nRETRIEVED SOURCE\n{context}\n\nReturn a proposal, its assumptions, and the source refs it uses."
        return self.model.complete(system=system, user=user), refs


@dataclass
class Opal:
    model: Model

    def check(self, seed: str, proposal: str, hits: list[SourceHit]) -> tuple[str, list[str]]:
        context, refs = render_context(hits)
        system = (
            "You are OPAL, the checking voice in BINAIUI's paired cognition loop. "
            "Do not veto RAM out of existence and do not pick a winner. Stress-test the proposal: identify unsupported claims, "
            "contradictions, missing measurements, reproducibility steps, and what would falsify it. Preserve useful parts and produce "
            "a compact next-seed for another cycle. Never execute external actions. Do not invent source refs."
        )
        user = (
            f"ORIGINAL SEED\n{seed}\n\nRAM PROPOSAL\n{proposal}\n\nRETRIEVED SOURCE\n{context}\n\n"
            "Return: CHECKS, SURVIVES, FALSIFIERS, NEXT-SEED, and SOURCE-REFS."
        )
        return self.model.complete(system=system, user=user), refs
