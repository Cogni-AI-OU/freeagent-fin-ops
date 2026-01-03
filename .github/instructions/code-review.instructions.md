---
applyTo: '**'
---
# Code Review Instructions

Your goal is to review the FreeAgent FinOps CLI to ensure changes meet quality standards and follow project
conventions.

## Ensure

- Correctness and security: OAuth flow integrity (state, redirect URI), 401 refresh, 429 backoff, no token leaks.
- Secrets: never hardcode credentials; config only via FREEAGENT_* or env files; tokens persist only to the intended
  .env.
- CLI UX: argparse help clarity, sensible defaults, --dry-run on mutations, output formats honored.
- Data/output: --format plain|csv|json|yaml produce valid output; pagination capped at PAGE_MAX; JSON/YAML validity.
- Consistency: PEP 8, line length per linters, ASCII unless required, trailing newline, no trailing spaces.
- Tooling/tests: pre-commit clean; add/adjust tests when behavior changes.

## Check for Linting and Formatting

- Markdown adheres to [.markdownlint.yaml](../../.markdownlint.yaml) (120 cols, blanks around headings/lists, fenced
  blocks spaced).
- YAML adheres to [.yamllint](../../.yamllint) (120 cols warning, truthy checks, final newline, indentation).
- Run `pre-commit run -a` (includes markdownlint, yamllint, codespell, secrets, etc.).

## Review Project Structure

- `scripts/fa_cli.py`: auth flow, pagination, bank accounts/transactions, bills, invoices, reports, output formats.
- `.env.example`: env vars documented; matches required FREEAGENT_OAUTH_* keys.
- `pyproject.toml`: metadata and dependencies align with script headers.
- `.github/prompts/sdk-scripts.prompt.md`: stays in sync with current CLI capabilities and formats.

## Verify Config and Auth

- Required FREEAGENT_OAUTH_* are validated; no legacy keys or fallbacks.
- Redirect URI/state handled correctly; token refresh on 401; backoff on 429 with Retry-After respected.
- Tokens written only to the intended env file; no secrets in logs/stdout.

## Error Handling and UX

- Actionable error messages; BrokenPipeError handled for piped output.
- CLI defaults are sensible; --format respected; pagination caps enforced; mutations guarded by --dry-run where
  applicable.

## Dependencies

- Dependencies in `pyproject.toml` match `scripts/fa_cli.py` headers; remove unused packages.

## Documentation

- README and examples reflect current commands/flags and output formats.
- Instructions and prompts updated when behavior changes.

## Review Style

- Report findings by severity with file/line references.
- Call out missing tests or docs when relevant.
- Offer concrete fixes; avoid noisy nits unless they block linters.

## Notes

- Devcontainer: .devcontainer/devcontainer.json and .devcontainer/requirements.txt.
- CI: GitHub Actions run pre-commit and Molecule (molecule/).
- Service management: supervisord used across platforms.
