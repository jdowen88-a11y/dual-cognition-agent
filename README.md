# BINAIUI Ram / Opal Runtime

A **portable, resumable, self-contained** dual-cognition runner grounded in the BINAIUI repository lineage.

```text
observe → measure → encode → hash → reproduce → falsify
                              │             │
                              ├─ RAM        └─ OPAL
                              └──── journal + source refs ────→ next cycle
```

**RAM proposes. OPAL checks. Both survive.** Every turn stores hashes and source references. A stopped process resumes from the last OPAL output instead of rebuilding the conversation from zero.

## What now lives outside any temporary chat/work session

- **Source memory:** SQLite under `.binaiui/state.sqlite3`
- **Corpus identity:** deterministic SHA-512 over the exact source manifest
- **Long-term journal:** run/cycle/agent/output history
- **Resume:** stable `run_id` continues from the last stored output
- **Portable transfer:** compressed snapshot/restore of source memory + journals
- **Health check:** database integrity, corpus identity, credential presence
- **Validation:** dependency-light deterministic backend + GitHub CI
- **Source hierarchy:** BINAIUI priority `100`; other repositories priority `10`

Private repository text stays in the local runtime database or an explicitly-created snapshot. It is not copied into this Git repository by normal ingestion.

## One-command bootstrap

```bash
python -m pip install -e .

export BINAIUI_GITHUB_TOKEN='READ_TOKEN'
binaiui bootstrap --smoke
```

That enumerates the owned GitHub repositories, imports readable text, prioritizes **BINAIUI**, computes a reproducible corpus hash, and runs one deterministic Ram/Opal cycle to verify journal + resume plumbing.

Inspect it:

```bash
binaiui doctor
binaiui corpus
binaiui status
```

## Run the actual paired loop

Use any Chat-Completions-compatible endpoint:

```bash
export BINAIUI_API_BASE='https://api.openai.com/v1'
export BINAIUI_API_KEY='...'
export BINAIUI_MODEL='YOUR_MODEL_ID'

binaiui run 'Continue from the BINAIUI corpus without restarting.' --cycles 8 --run-id main
```

Resume later with the **same** run id:

```bash
binaiui run 'resume' --cycles 8 --run-id main
```

The new seed does not overwrite an existing run's stored continuation; the journal resumes from its latest output.

For an environment intentionally kept alive:

```bash
binaiui run 'continue' --run-id main --forever --sleep 30
```

## Move the memory between pipes

Create a compressed portable bundle:

```bash
binaiui snapshot
```

Restore it elsewhere:

```bash
binaiui restore .binaiui/binaiui.snapshot.json.gz --replace
```

The snapshot contains **source contents and journal contents**, including material ingested from private repositories. Treat it as private data. The default path remains inside `.binaiui/`, which Git ignores.

## No-network proof

```bash
binaiui ingest-local ../BINAIUI
binaiui run 'test seed' --cycles 2 --run-id test --deterministic
binaiui run 'resume' --cycles 1 --run-id test --deterministic
binaiui corpus
```

## External-action boundary

The cognition loop reads source text and writes only its own memory/journal. Model output is **never evaluated as code** and is not silently routed into trading, deployment, account changes, messages, shell execution, or money movement.

That carries forward the existing project rule:

```text
DO NOT TURN THE KEY AUTOMATICALLY.
```

Internal generation can continue freely without turning an internal thought into an external side effect.

## Why this repository stays private

The runtime is designed to learn across the full repository set, including private repositories. Keeping the runner private reduces the chance of publishing source names, excerpts, journals, or derived context. The canonical BINAIUI source repository can remain public while this runtime and its state remain private.
