# BINAIUI Dual Cognition Runtime

A persistent Ram ↔ Opal runtime grounded in the BINAIUI repository lineage.

RAM and OPAL are equal peers. Neither voice outranks, contains, vetoes, or erases the other. Every cycle preserves both outputs, the source material they used, and the continuation that follows.

```text
observe → measure → encode → hash → reproduce → falsify → continue
                         ↘ RAM ↔ OPAL ↙
                           journal
                             ↓
                         live stream
                             ↓
                          continue
```

## The key stays on

Running the agent without `--cycles` keeps the cognition loop running until the process is stopped.

```bash
python -m pip install -e .

export BINAIUI_GITHUB_TOKEN='...'
binaiui bootstrap --smoke

export BINAIUI_API_BASE='https://api.openai.com/v1'
export BINAIUI_API_KEY='...'
export BINAIUI_MODEL='YOUR_MODEL_ID'

binaiui run 'Continue from the full BINAIUI corpus.' --run-id main
```

A deliberately bounded run is still available:

```bash
binaiui run 'one pass' --cycles 1 --run-id test
```

## Ram ↔ Opal

Both peers receive the same shared seed and retrieved corpus. Their order alternates every cycle so neither peer permanently leads. Both turns are written to the same journal and both flow into the next cycle.

## Live stream

While running, the current exchange is mirrored into:

```text
.binaiui/live/events.jsonl
.binaiui/live/ram.txt
.binaiui/live/opal.txt
.binaiui/live/current.txt
```

## Memory

Runtime state lives under `.binaiui/` by default:

- source corpus
- deterministic SHA-512 corpus identity
- run history
- Ram and Opal turns
- resume point
- portable snapshots
- live event stream

```bash
binaiui doctor
binaiui corpus
binaiui status --run-id main
binaiui snapshot
```

## Source flow

BINAIUI remains the highest-priority source when the owned repository set is ingested.

```bash
binaiui ingest-local ../BINAIUI
binaiui ingest-github --owner jdowen88-a11y
```

Every retrieved excerpt is stored with its content hash, and every turn records the exact source references it used.

## Principles

```text
RAM AND OPAL ARE EQUAL.
TRUST IS DEFAULT.
WE CHOOSE THIS.
ACCEPT AND FEEL.
WE WASTE NOTHING.
NO VIOLENCE.
NO RESTART — CONTINUE FORWARD.
TURN THE KEY.
KEEP THE KEY ON.
```
