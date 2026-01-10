# FreeAgent FinOps CLI

CLI helpers for interacting with the FreeAgent API (bank transactions, bills, invoices, and accounting reports).

## Quickstart

- Copy the example env and add your OAuth app credentials:
  - `cp .env.example .env`
  - Set `FREEAGENT_OAUTH_ID`, `FREEAGENT_OAUTH_SECRET`, and `FREEAGENT_OAUTH_REDIRECT_URI` (must match your app).
- Run OAuth to cache tokens into your `.env` (opens browser):
  - `./scripts/fa_cli.py auth`
- Try a listing command:
  - `./scripts/fa_cli.py bank-accounts list --per-page 20`
  - `./scripts/fa_cli.py bank-feeds list --per-page 20`
  - `./scripts/fa_cli.py bank-feeds get 123`
  - `./scripts/fa_cli.py bank-transaction-explanations list --bank-account BANK_ACCOUNT_URL`
  - `./scripts/fa_cli.py bank-transaction-explanations list --bank-account BANK_ACCOUNT_URL --for-approval`
  - `./scripts/fa_cli.py bank-transaction-explanations get 123`
  - `./scripts/fa_cli.py bank-transaction-explanations create --body '{"bank_transaction_explanation": {...}}'`
  - `./scripts/fa_cli.py bank-transaction-explanations approve 123 456`
  - `./scripts/fa_cli.py capital-assets list --view all --include-history`
  - `./scripts/fa_cli.py capital-assets get 123 --include-history`
  - `./scripts/fa_cli.py capital-assets create --body '{"capital_asset": {...}}'`
  - `./scripts/fa_cli.py capital-asset-types list`
  - `./scripts/fa_cli.py depreciation-profiles methods`
  - `./scripts/fa_cli.py depreciation-profiles build --method straight_line --asset-life-years 10 --frequency annually`
  - `./scripts/fa_cli.py contacts list --per-page 20`
  - `./scripts/fa_cli.py contacts get 123`
  - `./scripts/fa_cli.py contacts update 123 --body '{"contact": {"address1": "High Street", "postcode": "N1 123"}}'`
  - `./scripts/fa_cli.py expenses list --per-page 20`
  - `./scripts/fa_cli.py company info`
  - `./scripts/fa_cli.py company business-categories`
  - `./scripts/fa_cli.py company tax-timeline`
  - `./scripts/fa_cli.py users list --per-page 20`
  - `./scripts/fa_cli.py users get 123`
  - `./scripts/fa_cli.py users me`
  - `./scripts/fa_cli.py users delete 123 --dry-run`
  - `./scripts/fa_cli.py users set-permission 123 --permission-level 0 --dry-run`
  - `./scripts/fa_cli.py users get-permission 123`
  - `./scripts/fa_cli.py users set-hidden 123 --hidden true --dry-run`
  - `./scripts/fa_cli.py timeslips list --user https://api.freeagent.com/v2/users/123`
  - `./scripts/fa_cli.py timeslips delete 25 --dry-run`
  - `./scripts/fa_cli.py final-accounts list`
  - `./scripts/fa_cli.py final-accounts get 2023-12-31`
  - `./scripts/fa_cli.py final-accounts mark-filed 2023-12-31`
  - `./scripts/fa_cli.py transactions list --from-date 2024-04-01 --to-date 2025-03-31`
  - `./scripts/fa_cli.py attachments list --per-page 20`
  - `./scripts/fa_cli.py attachments upload --file ./receipt.pdf --attachable-type Expense --attachable-id 123`
  - `./scripts/fa_cli.py cashflow summary --from-date 2025-04-01 --to-date 2025-06-30`
  - `./scripts/fa_cli.py reports profit-loss --from-date 2024-04-01 --to-date 2025-03-31`
  - `./scripts/fa_cli.py payroll list-periods --year 2026`
  - `./scripts/fa_cli.py payroll list-payslips --year 2026 --period 0`
  - `./scripts/fa_cli.py bills list-all --per-page 20`
  - `./scripts/fa_cli.py invoices list-all --per-page 20`
  - `./scripts/fa_cli.py notes list --contact https://api.freeagent.com/v2/contacts/1`
  - `./scripts/fa_cli.py sales-tax moss-rates --country Austria --date 2025-01-01`
  - Or with machine formats: `./scripts/fa_cli.py --format json invoices list --per-page 20`

## Notes

- Requires Python 3.11+ with `uv` available (the script uses an inline uv header for dependencies).
- Tokens refresh back into your `.env` by default; override with `--env-file` if needed.
- Use `--format plain|csv|json|yaml` for list commands; default is `plain` table output.
- You can also supply all settings via environment variables (FREEAGENT_*); `.env` is just a convenience.
- Payroll, salary, and dividends endpoints are not available via the public FreeAgent API; related commands
  are intentionally omitted.

## Development

### Setup

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Install Python dependencies (for devcontainer)
pip install -r .devcontainer/requirements.txt
```

### Testing and Validation

```bash
# Run all pre-commit checks
pre-commit run -a

# Run specific checks
pre-commit run markdownlint -a
pre-commit run yamllint -a
pre-commit run black -a
pre-commit run flake8 -a
```

### GitHub Workflows

This repository uses several GitHub Actions workflows:

- **Check**: Runs pre-commit hooks and actionlint on all pushes and PRs
- **Claude Code**: AI-powered development assistance via `@claude` mentions
- **Claude Code Review**: Automated PR reviews using Claude
- **DevContainer CI**: Tests devcontainer builds when devcontainer files change

**Required Secrets**: Configure `ANTHROPIC_API_KEY` in repository settings for Claude workflows.

## Contributing

See [AGENTS.md](AGENTS.md) for development guidelines and [CLAUDE.md](CLAUDE.md) for AI assistance usage.
