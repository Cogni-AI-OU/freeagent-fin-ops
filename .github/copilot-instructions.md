# Copilot Instructions for FreeAgent FinOps CLI

## Project Overview

FreeAgent FinOps CLI provides OAuth2-enabled helpers to interact with the FreeAgent API (bank accounts, bank
transactions, bills, invoices, accounting reports). It is a Python 3.11+ `uv`-scripted CLI using env-based
configuration (`FREEAGENT_*`) and supports multiple output formats (plain/csv/json/yaml).

## Coding Standards

### Python

- Use **Python 3.11+**.
- Use `uv` script headers for dependency management:

  ```python
  #!/usr/bin/env -S uv run --script
  # /// script
  # requires-python = ">=3.11"
  # dependencies = [
  #     "xero-python",
  #     "PyYAML",
  # ]
  # ///
  ```

- Follow **PEP 8** style guidelines.
- Use `argparse` for CLI argument parsing.
- Handle `BrokenPipeError` for CLI tools that might be piped to `head` or `grep`:

  ```python
  import signal
  signal.signal(signal.SIGPIPE, signal.SIG_DFL)
  ```

### FreeAgent API

- Use the FreeAgent REST API (auth via OAuth2 code flow).
- Handle API rate limits (429) with backoff and retry; handle 401 by refreshing tokens.
- Keep configuration in environment variables (`FREEAGENT_OAUTH_ID`, `FREEAGENT_OAUTH_SECRET`,
  `FREEAGENT_OAUTH_REDIRECT_URI`, `FREEAGENT_SCOPE`), optionally via `.env`.

## Project Structure

- `scripts/fa_cli.py`: Main CLI with auth, bank accounts/transactions, bills, invoices, reports, pagination, output
  formats.
- `.env.example`: Document required env vars for auth.
- `README.md`: Quickstart and usage examples.
- `.github/prompts/sdk-scripts.prompt.md`: Authoring prompt for extending SDK-based scripts.
- `pyproject.toml`: Project metadata and dependencies.

## Common Tasks

- Authenticate and cache tokens: `./scripts/fa_cli.py auth`
- List bank accounts: `./scripts/fa_cli.py bank-accounts list`
- List bank transactions: `./scripts/fa_cli.py bank-transactions list --bank-account <url>`
- Run pre-commit checks: `pre-commit run -a`

## Formatting Guidelines

### Markdown

- Keep line length <=120 characters (see `.markdownlint.yaml`).
- Surround headings and lists with blank lines; fence code blocks with blank lines.
- Avoid trailing spaces; ensure a single trailing newline.
- Avoid hard tabs (MD010/no-hard-tabs).
- Headings must have blank lines around them (MD022/blanks-around-headings).
- Lists must be surrounded by blank lines (MD032/blanks-around-lists).
- Fenced code blocks need surrounding blank lines (MD031/blanks-around-fences).
- Files end with a single newline (MD047/single-trailing-newline).
- If pre-commit surfaces formatting errors, update these guidelines to keep them current and prevent repeats.

### YAML Guidelines

Ensure the following rules are strictly followed:

- yaml[empty-lines]: Avoid too many blank lines (1 > 0).
- yaml[indentation]: Avoid wrong indentation.
- yaml[line-length]: No long lines (max. 120 characters).
- yaml[new-line-at-end-of-file]: Enforce new line character at the end of file.
- yaml[truthy]: Truthy value should be one of [false, true].
- Ensure items are in lexicographical order when possible.
- When writing inline code, add a new line at the end to maintain proper indentation.

Formatting rules are defined in `.yamllint` (YAML) and `.markdownlint.yaml` (Markdown).

Notes:

- Project utilizes Codespaces with config at `.devcontainer/devcontainer.json` and requirements at `.devcontainer/requirements.txt`.
- GitHub Actions run pre-commit checks (`.pre-commit-config.yaml`).
