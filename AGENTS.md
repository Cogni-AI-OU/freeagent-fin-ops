# AGENTS.md

Guidance for AI agents working in the FreeAgent FinOps CLI repository.

## Quick Start

- See [README.md](README.md) for setup and installation instructions
- This is a Python 3.11+ project using `uv` for script execution
- OAuth2-enabled FreeAgent API client for bank accounts, transactions, bills, invoices, and reports

## Instructions

For detailed coding standards and formatting guidelines, refer to:

- [Copilot Instructions](.github/copilot-instructions.md) - Main coding standards and project overview

### Specialized Agents

For specific tasks, use the following specialized agent instructions:

- [Code Tour Agent](.github/agents/code-tour.agent.md) - For creating/updating `.tours/` files
- [Copilot Plus Agent](.github/agents/copilot-plus.agent.md) - Enhanced Copilot capabilities

## Common Tasks

### Before commit

Before each commit change:

- Verify your expected changes by `git diff --no-color`.
- Use linting and validation tools to confirm your changes meet the coding standard.
- Run pre-commit hooks to validate your changes.

### Linting and Validation

```bash
# Run all pre-commit checks
pre-commit run -a

# Run specific checks
pre-commit run markdownlint -a
pre-commit run yamllint -a
pre-commit run black -a
pre-commit run flake8 -a
```

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

### Testing

```bash
# Run tests if available
python -m pytest tests/

# Test CLI script manually
./scripts/fa_cli.py --help
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

## Configuration

- **Environment Variables**: All configuration is via `FREEAGENT_*` environment variables
- **OAuth2 Flow**: Uses authorization code flow with token refresh
- **Output Formats**: Supports plain, csv, json, and yaml output formats
- **Pagination**: Built-in pagination support with configurable page size

## Project Structure

- `.devcontainer/`: Development container configuration
- `.github/`: GitHub workflows and instructions
- `docs/`: How-to guides and documentation
- `scripts/`: CLI scripts (main: `fa_cli.py`)
- `tests/`: Test files
- `.env.example`: Example environment configuration

## References

- Claude-specific guidance: [CLAUDE.md](CLAUDE.md)
- Main documentation: [README.md](README.md)

## Troubleshooting

### FreeAgent API Issues

- Check API rate limits (429 responses)
- Verify OAuth tokens are valid (refresh on 401)
- Ensure environment variables are set correctly

### Pre-commit Issues

```bash
# Update pre-commit hooks
pre-commit autoupdate

# Clear cache and retry
pre-commit clean
pre-commit run -a
```

### Python Issues

```bash
# Ensure Python 3.11+ is installed
python --version

# Install uv if needed
pip install uv

# Run script with uv
uv run scripts/fa_cli.py --help
```
