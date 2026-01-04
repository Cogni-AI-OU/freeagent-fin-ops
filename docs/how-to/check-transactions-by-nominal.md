# Check Transactions By Nominal Code (Director Loan example)

This guide shows how to retrieve accounting transactions and balances for any nominal code (e.g. a director loan
account) using the CLI.

## Prerequisites

- Tokens already cached via `./scripts/fa_cli.py auth`.
- `.env` contains `FREEAGENT_*` credentials.
- From the repo root, run commands as shown.

## Find transactions for a nominal code in a date range

Use the accounting transactions endpoint with filters. Keep the window inside one accounting year (or <12 months)
to avoid API errors:

```bash
./scripts/fa_cli.py --format json --max-pages 5 transactions list \
  --from-date 2025-12-01 \
  --to-date 2026-01-04 \
  --nominal-code 907-2
```

Notes:

- `--nominal-code` accepts the full code, including suffixes (e.g. `907-2`).
- If you see `specified period must be within a single accounting year`, shorten the date window.
- If you see `No accounting period includes the specified dates`, shift the window into a valid accounting year.
- Use `--max-pages` if you expect many results.

## Check the current balance of a nominal code

The balance sheet includes totals per nominal code. To extract a single code:

```bash
./scripts/fa_cli.py --format json reports balance-sheet --as-at-date 2026-01-04 \
  | jq '.. | objects | select(.nominal_code=="907-2")'
```

The `total_debit_value` will be negative for a credit balance. To avoid jq errors when names are null, match on
`nominal_code` rather than name.

List all nominal codes with balances:

```bash
./scripts/fa_cli.py --format json reports balance-sheet --as-at-date 2026-01-04 \
  | jq '.. | objects | select(has("nominal_code")) | {code:.nominal_code, name:.name, total:.total_debit_value}'
```

## Troubleshooting

- If you get `specified period must be within a single accounting year`, shorten the `from-date`/`to-date` window
  to a single accounting year.
- If you get `No accounting period includes the specified dates`, shift the range into a valid accounting year.
- If no rows return, confirm the nominal code in the UI or by listing transactions without filters and inspecting
  `nominal_code` values:

```bash
./scripts/fa_cli.py --format json --max-pages 5 transactions list \
  | jq '[.[].nominal_code] | unique | sort'
```

- For summary-only needs, prefer the balance sheet to avoid paging through transactions.
