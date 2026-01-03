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
  - Or with machine formats: `./scripts/fa_cli.py --format json invoices list --per-page 20`

## Notes

- Requires Python 3.11+ with `uv` available (the script uses an inline uv header for dependencies).
- Tokens refresh back into your `.env` by default; override with `--env-file` if needed.
- Use `--format plain|csv|json|yaml` for list commands; default is `plain` table output.
- You can also supply all settings via environment variables (FREEAGENT_*); `.env` is just a convenience.
