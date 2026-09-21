# BINAIUI Ram / Opal Runtime

A resumable dual-cognition runner built from the existing BINAIUI and related repository lineage.

The loop is deliberately simple and inspectable:

```text
observe → measure → encode → hash → reproduce → falsify
                              │             │
                              ├─ RAM        └─ OPAL
                              └──── journal + source refs ────→ next cycle
```

**RAM proposes. OPAL checks. Both outputs remain in history.** Each turn records the exact source refs and hashes used. An interrupted run resumes from the last OPAL output rather than restarting from zero.

## Source behavior

- BINAIUI is retrieval priority 100.
- Every other repository is priority 10.
- Text sources are stored in a local SQLite database under `.binaiui/` and are ignored by Git.
- Private repository contents are never copied into this Git repository by default.
- The runtime can ingest a directory of cloned repos or read repositories through GitHub's API when `BINAIUI_GITHUB_TOKEN` is present.

## External-action boundary

The cognition loop only reads source text and appends to its own journal. Model output is **never** evaluated as code and is never routed into trading, deployments, account changes, messages, shell commands, or money movement. That preserves the existing "do not turn the key automatically" rule while letting the internal Ram/Opal exchange continue.

## Run

```bash
python -m pip install -e .

# Import every owned GitHub repo visible to a read token.
export BINAIUI_GITHUB_TOKEN='...'
binaiui ingest-github --owner jdowen88-a11y

# Use any OpenAI Chat-Completions-compatible endpoint.
export BINAIUI_API_BASE='https://api.openai.com/v1'
export BINAIUI_API_KEY='...'
export BINAIUI_MODEL='YOUR_MODEL_ID'

# Start a bounded run.
binaiui run 'Continue from the BINAIUI corpus without restarting.' --cycles 8 --run-id main

# Resume the same run later.
binaiui run 'resume' --cycles 8 --run-id main

# Explicitly opt into an uninterrupted process in an environment that stays alive.
binaiui run 'continue' --run-id main --forever --sleep 30
```

For a no-network proof that ingestion, hashing, journaling, and resume work:

```bash
binaiui ingest-local ../BINAIUI
binaiui run 'test seed' --cycles 2 --run-id test --deterministic
binaiui status --run-id test
```

## Why this repo is private

The runtime is intended to learn from the full repository set, including private repositories. Keeping the runner private avoids accidentally publishing source names, excerpts, journals, or derived context. The canonical BINAIUI source repository can remain public while this runtime stays private.
