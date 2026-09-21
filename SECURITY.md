# Runtime security notes

The repository code contains no required credentials.

Runtime secrets belong in environment variables or the host platform's secret store:

- `BINAIUI_GITHUB_TOKEN` / `GITHUB_TOKEN`
- `BINAIUI_API_KEY` / `OPENAI_API_KEY`
- `BINAIUI_MODEL`
- optional `BINAIUI_API_BASE`

Do not commit `.env`, SQLite state, portable snapshots, private repository exports, wallet keys, or service credentials.

A `binaiui snapshot` bundle intentionally contains the ingested source text and Ram/Opal journal. If the corpus includes private repositories, the snapshot is private data too.

The paired cognition loop has no code path that automatically executes model output, shell commands, deployments, trading orders, account mutations, or money movement. External effects require a separate explicit caller.
