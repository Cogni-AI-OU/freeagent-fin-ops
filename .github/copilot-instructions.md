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

- `.devcontainer/devcontainer.json`: Devcontainer setup for consistent development environment.
- `.devcontainer/requirements.txt`: Python dependencies for the devcontainer.
- `.env.example`: Document required env vars for auth.
- `.github/prompts/sdk-scripts.prompt.md`: Authoring prompt for extending SDK-based scripts.
- `.pre-commit-config.yaml`: Pre-commit hooks for formatting and linting (YAML, Markdown).
- `pyproject.toml`: Project metadata and dependencies.
- `README.md`: Quickstart and usage examples.
- `scripts/fa_cli.py`: Main CLI with auth, bank accounts/transactions, bills, invoices, reports, pagination,
  output formats.

## Common Tasks

### Running the CLI

```bash
# Authenticate and cache tokens
./scripts/fa_cli.py auth

# List bank accounts
./scripts/fa_cli.py bank-accounts list

# List bank transactions
./scripts/fa_cli.py bank-transactions list --bank-account <url>

# List bills
./scripts/fa_cli.py bills list

# List invoices
./scripts/fa_cli.py invoices list

# Get accounting reports
./scripts/fa_cli.py reports balance-sheet
./scripts/fa_cli.py reports profit-and-loss
```

### Environment Setup

```bash
# Install dependencies
pip install -r .devcontainer/requirements.txt

# Install pre-commit hooks
pre-commit install

# Set up environment variables (copy from .env.example)
cp .env.example .env
# Edit .env with your FreeAgent OAuth credentials
```

### Linting and Validation

```bash
# Run all pre-commit checks
pre-commit run -a

# Run specific checks
pre-commit run markdownlint -a
pre-commit run yamllint -a
```

### Testing

```bash
# Run tests if available
python -m pytest tests/

# Test CLI script manually
./scripts/fa_cli.py --help
```

## Configuration

- **Environment Variables**: All configuration is via `FREEAGENT_*` environment variables
- **OAuth2 Flow**: Uses authorization code flow with token refresh
- **Output Formats**: Supports plain, csv, json, and yaml output formats
- **Pagination**: Built-in pagination support with configurable page size

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

## Agent AI Guidelines

- When already inside the devcontainer, skip setting up or switching the Python environment; the container
  image already provides the intended tooling.
- If some functionality is missing, suggest user whether to implement it via API if possible.
- When struggling how to achieve something, consider creating additional documentation in docs/how-to/ or
  extending README.md with examples.
- After complete refactoring, run pre-commit to ensure formatting and linting are correct.

## Troubleshooting

### FreeAgent API Issues

- Check API rate limits (429 responses)
- Verify OAuth tokens are valid (refresh on 401)
- Ensure environment variables are set correctly
