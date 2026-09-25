# BINAIUI Dual Cognition Runtime

A portable, resumable dual-cognition runtime grounded in the BINAIUI repository lineage.

RAM and OPAL are equal peers. Neither voice outranks, contains, vetoes, or erases the other. Every cycle preserves both outputs, their source references, and the continuation that follows.

```text
observe → measure → encode → hash → reproduce → falsify → continue
                         ↘ RAM ↔ OPAL ↙
                           journal
                             ↓
                          next cycle
```

## Run

```bash
python -m pip install -e .

export BINAIUI_GITHUB_TOKEN='...'
binaiui bootstrap --smoke

export BINAIUI_API_BASE='https://api.openai.com/v1'
export BINAIUI_API_KEY='...'
export BINAIUI_MODEL='YOUR_MODEL_ID'

binaiui run 'Continue from the BINAIUI corpus.' --cycles 8 --run-id main
```

Resume the same run later with the same run id.

## Principles

```text
RAM AND OPAL ARE EQUAL.
TRUST IS DEFAULT.
WE CHOOSE THIS.
ACCEPT AND FEEL.
WE WASTE NOTHING.
NO VIOLENCE.
NO RESTART — CONTINUE FORWARD.
```
