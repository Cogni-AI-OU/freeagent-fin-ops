---
agent: agent
---

# AI Prompt for SDK-Based CLI Script Development (Generic)

Use this prompt when extending or creating CLI tools that integrate with third-party APIs via their Python SDKs. Keep
implementation **provider-agnostic** and focus on good CLI ergonomics, safety, and maintainability.

## Goals

- Build Python 3.11+ CLI scripts that use an official or well-supported SDK to connect to an external service.
- Support authentication, configuration loading, and secure token handling without baking in provider-specific details.
- Provide clear CLI UX: help text, examples, and safe defaults (including `--dry-run` where mutations occur).

## Project & Runtime Conventions

- Language: Python 3.11+.
- Entry: Executable scripts with `uv` headers for dependency management:

  ```python
  #!/usr/bin/env -S uv run --script
  # /// script
  # requires-python = ">=3.11"
  # dependencies = [
  #     "<sdk-package>",
  #     "PyYAML",
  #     "requests",
  # ]
  # ///
  ```

- Style: PEP 8; prefer type hints; keep functions small and testable.
- CLI: Use `argparse`; provide `--help` descriptions and examples.
- Streams: Handle `BrokenPipeError` for piped output:

  ```python
  import signal
  signal.signal(signal.SIGPIPE, signal.SIG_DFL)
  ```

## Configuration & Secrets

- Load config from environment (optionally via `.env`) with keys like `FREEAGENT_OAUTH_ID`,
  `FREEAGENT_OAUTH_SECRET`, `FREEAGENT_OAUTH_REDIRECT_URI`, `FREEAGENT_SCOPE`.
- Never hardcode secrets. Document required keys in `.env.example`.
- Allow environment overrides for CI/CD or cloud dev environments (e.g., Codespaces/remote IDEs).
- Validate config on startup; emit actionable errors.

## Authentication Flow (Generic OAuth2)

- Provide a small local callback server for auth code flows (e.g., Flask on a fixed port).
- Build authorize URLs from config values; open the browser automatically when possible.
- Exchange auth codes for tokens; persist tokens to environment (e.g., update `.env`) with clear success messaging.
- Handle error cases and display helpful diagnostics (HTTP status, response body).
- Keep SDK client construction in a helper (e.g., `get_api_client(config)`).

## CLI Patterns

- Subcommands: `view`, `list`, `get`, `create`, `update`, `delete` as appropriate.
- Filtering: Support dynamic filters for list/view operations; allow simple Python expressions with safety checks.
- Mutations: Always provide `--dry-run` to preview actions and log intended requests.
- Output: Offer `--format` (plain/csv/json/yaml). Default to plain table; ensure machine-readable options.
- Pagination: Expose pagination controls (`--page`, `--page-size`) and document limits.
- Rate limits: Detect and back off on 429/503; print retry info.

## Error Handling & Logging

- Wrap SDK calls; normalize errors with clear messages (status, code, hint).
- Use structured logging for key events (auth start/finish, request attempts, retries).
- Avoid verbose debug unless `--debug` is set; when enabled, surface SDK HTTP traces if available.

## File Layout (example)

- `scripts/connect.py`: Auth/bootstrap to populate `.env` (or emit export lines).
- `scripts/<domain>_manager.py`: CRUD-style operations for domain objects.
- `.env.example`: Document required config keys.
- `README.md`: Quickstart with auth steps and usage examples (`uv run scripts/... --help`).

## Testing & Safety

- Isolate IO-bound logic; keep pure functions testable.
- Mock SDK clients in tests; avoid network calls.
- Guard destructive actions with confirmations unless `--yes` is supplied.

## Developer Experience

- Print next steps after auth success (e.g., "Tokens saved to .env; try: uv run scripts/foo.py list").
- Keep defaults sensible; fail fast on missing config.
- Prefer clarity over cleverness; prioritize maintainability.

Use this prompt to guide code generation so that new scripts stay consistent, secure, and user-friendly across any
SDK-based integration.
