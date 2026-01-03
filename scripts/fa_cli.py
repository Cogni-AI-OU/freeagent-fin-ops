#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests>=2.32.0",
#     "tabulate>=0.9.0",
#     "pyyaml>=6.0.1",
# ]
# ///
"""FreeAgent FinOps CLI.

Supports OAuth2 auth flow, pagination, and CRUD/report operations for core
FreeAgent resources using the public API (https://api.freeagent.com/v2).

Usage examples:
    ./scripts/fa_cli.py auth
    ./scripts/fa_cli.py bank-accounts list
    ./scripts/fa_cli.py --format json bank-transactions list --bank-account <url> --from-date 2024-01-01
    ./scripts/fa_cli.py --format yaml invoices create --body '{"invoice": {...}}' --dry-run
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import signal
import sys
import time
import uuid
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlencode, urljoin, urlparse, parse_qs

import requests
from tabulate import tabulate

# Prevent BrokenPipeError when piping output
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

API_BASE_URL = "https://api.freeagent.com/v2"
TOKEN_ENDPOINT = "https://api.freeagent.com/v2/token_endpoint"
AUTH_ENDPOINT = "https://api.freeagent.com/v2/approve_app"
DEFAULT_ENV_FILE = Path(".env")
DEFAULT_SCOPE = "full"
PAGE_MAX = 100


@dataclass
class OAuthTokens:
    access_token: str
    refresh_token: str
    expires_at: float  # epoch seconds
    token_type: str = "Bearer"

    @classmethod
    def from_response(cls, payload: Dict[str, Any]) -> "OAuthTokens":
        expires_in = payload.get("expires_in", 0)
        return cls(
            access_token=payload["access_token"],
            refresh_token=payload.get("refresh_token", ""),
            expires_at=time.time() + expires_in - 30,  # buffer to refresh early
            token_type=payload.get("token_type", "Bearer"),
        )

    def is_expired(self) -> bool:
        return time.time() >= self.expires_at


@dataclass
class AppConfig:
    oauth_id: str
    oauth_secret: str
    redirect_uri: str
    scope: str = DEFAULT_SCOPE
    base_url: str = API_BASE_URL
    env_file: Path = DEFAULT_ENV_FILE
    debug: bool = False


class TokenStore:
    def __init__(
        self, env_path: Path, env_file_data: Dict[str, str], env_lookup: Dict[str, str]
    ):
        self.env_path = env_path
        self.env_file_data = env_file_data
        self.env_lookup = env_lookup

    def load(self) -> Optional[OAuthTokens]:
        access = self.env_lookup.get("FREEAGENT_ACCESS_TOKEN") or self.env_lookup.get(
            "ACCESS_TOKEN"
        )
        refresh = self.env_lookup.get("FREEAGENT_REFRESH_TOKEN") or self.env_lookup.get(
            "REFRESH_TOKEN"
        )
        expires_at_raw = self.env_lookup.get(
            "FREEAGENT_EXPIRES_AT"
        ) or self.env_lookup.get("EXPIRES_AT")
        if not access:
            return None
        expires_at = float(expires_at_raw) if expires_at_raw else 0.0
        return OAuthTokens(
            access_token=access, refresh_token=refresh or "", expires_at=expires_at
        )

    def save(self, tokens: OAuthTokens) -> None:
        self.env_file_data["FREEAGENT_ACCESS_TOKEN"] = tokens.access_token
        self.env_lookup["FREEAGENT_ACCESS_TOKEN"] = tokens.access_token
        if tokens.refresh_token:
            self.env_file_data["FREEAGENT_REFRESH_TOKEN"] = tokens.refresh_token
            self.env_lookup["FREEAGENT_REFRESH_TOKEN"] = tokens.refresh_token
        self.env_file_data["FREEAGENT_EXPIRES_AT"] = str(tokens.expires_at)
        self.env_lookup["FREEAGENT_EXPIRES_AT"] = str(tokens.expires_at)
        lines = [
            f"{k}={v}" for k, v in sorted(self.env_file_data.items()) if k.isupper()
        ]
        self.env_path.write_text("\n".join(lines) + "\n")


def load_env_file(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def load_config(
    env_path: Path, base_url: str, *, debug: bool = False
) -> Tuple[AppConfig, Dict[str, str], Dict[str, str]]:
    env_file_data = load_env_file(env_path)
    env_lookup = {**env_file_data, **os.environ}

    def pick(*keys: str) -> Optional[str]:
        for key in keys:
            val = env_lookup.get(key)
            if val:
                return val
        return None

    oauth_id = pick("FREEAGENT_OAUTH_ID")
    oauth_secret = pick("FREEAGENT_OAUTH_SECRET")
    redirect_uri = pick("FREEAGENT_OAUTH_REDIRECT_URI")
    scope = pick("FREEAGENT_SCOPE") or DEFAULT_SCOPE

    missing = [
        name
        for name, value in (
            ("FREEAGENT_OAUTH_ID", oauth_id),
            ("FREEAGENT_OAUTH_SECRET", oauth_secret),
            ("FREEAGENT_OAUTH_REDIRECT_URI", redirect_uri),
        )
        if not value
    ]
    if missing:
        raise SystemExit(
            "Missing config keys: "
            + ", ".join(missing)
            + f". Set them in {env_path} or env vars FREEAGENT_OAUTH_ID/SECRET/OAUTH_REDIRECT_URI."
        )

    config = AppConfig(
        oauth_id=oauth_id,  # type: ignore[arg-type]
        oauth_secret=oauth_secret,  # type: ignore[arg-type]
        redirect_uri=redirect_uri,  # type: ignore[arg-type]
        scope=scope,
        base_url=base_url,
        env_file=env_path,
        debug=debug,
    )
    # Ensure .env retains core settings even if sourced from process env
    env_file_data.setdefault("FREEAGENT_OAUTH_ID", oauth_id)
    env_file_data.setdefault("FREEAGENT_OAUTH_SECRET", oauth_secret)
    env_file_data.setdefault("FREEAGENT_OAUTH_REDIRECT_URI", redirect_uri)
    env_file_data.setdefault("FREEAGENT_SCOPE", scope)
    return config, env_file_data, env_lookup


def build_auth_url(config: AppConfig, state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": config.oauth_id,
        "redirect_uri": config.redirect_uri,
        "scope": config.scope,
        "state": state,
    }
    return f"{AUTH_ENDPOINT}?{urlencode(params)}"


def exchange_code_for_token(config: AppConfig, code: str) -> OAuthTokens:
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.redirect_uri,
    }
    return _token_request(config, payload)


def refresh_access_token(config: AppConfig, tokens: OAuthTokens) -> OAuthTokens:
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": tokens.refresh_token,
    }
    return _token_request(config, payload)


def _token_request(config: AppConfig, payload: Dict[str, Any]) -> OAuthTokens:
    auth_basic = base64.b64encode(
        f"{config.oauth_id}:{config.oauth_secret}".encode()
    ).decode()
    headers = {
        "Authorization": f"Basic {auth_basic}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    resp = requests.post(TOKEN_ENDPOINT, data=payload, headers=headers, timeout=30)

    if resp.status_code >= 400:
        debug_lines: List[str] = []
        debug_lines.append(
            f"grant_type={payload.get('grant_type')}, redirect_uri={payload.get('redirect_uri')}"
        )
        debug_lines.append(f"status={resp.status_code} {resp.reason}")
        www_auth = resp.headers.get("WWW-Authenticate")
        if www_auth:
            debug_lines.append(f"www-authenticate: {www_auth}")
        debug_lines.append(f"content-type: {resp.headers.get('Content-Type')}")
        body = resp.text
        debug_lines.append(f"body: {body}")
        detail = " | ".join(debug_lines)
        raise SystemExit(
            "Token request failed. Check credentials and redirect URI. "
            + (
                detail
                if config.debug
                else f"Status {resp.status_code}. Enable --debug for details."
            )
        )

    if config.debug:
        print(
            f"Token request succeeded: status={resp.status_code} content-type={resp.headers.get('Content-Type')}"
        )

    data = resp.json()
    return OAuthTokens.from_response(data)


class _AuthHandler(BaseHTTPRequestHandler):
    server: HTTPServer  # type: ignore[assignment]

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        state = params.get("state", [None])[0]
        self.server.auth_code = code  # type: ignore[attr-defined]
        self.server.auth_state = state  # type: ignore[attr-defined]
        msg = (
            "Authorization received. You may close this window."
            if code
            else "Authorization failed."
        )
        self.send_response(200)
        self.end_headers()
        self.wfile.write(msg.encode())

    def log_message(self, fmt: str, *args: Any) -> None:  # silence default logging
        return


def run_local_server(port: int) -> Tuple[str, str]:
    server = HTTPServer(("127.0.0.1", port), _AuthHandler)
    server.auth_code = None  # type: ignore[attr-defined]
    server.auth_state = None  # type: ignore[attr-defined]
    try:
        server.handle_request()
    finally:
        server.server_close()
    return server.auth_code, server.auth_state  # type: ignore[attr-defined]


def start_auth_flow(config: AppConfig, port: int, open_browser: bool) -> OAuthTokens:
    state = uuid.uuid4().hex
    auth_url = build_auth_url(config, state)
    if open_browser:
        webbrowser.open(auth_url)
    else:
        print(f"Open this URL in your browser:\n{auth_url}\n")
    print(f"Listening on http://127.0.0.1:{port} for the callback...")
    code, returned_state = run_local_server(port)
    if not code:
        raise SystemExit("No authorization code received.")
    if returned_state and returned_state != state:
        raise SystemExit("State mismatch during OAuth flow.")
    tokens = exchange_code_for_token(config, code)
    return tokens


def ensure_tokens(config: AppConfig, store: TokenStore) -> OAuthTokens:
    tokens = store.load()
    if not tokens:
        raise SystemExit("No tokens found. Run `uv run scripts/fa_cli.py auth` first.")
    if tokens.is_expired():
        tokens = refresh_access_token(config, tokens)
        store.save(tokens)
    return tokens


def api_request(
    method: str,
    config: AppConfig,
    store: TokenStore,
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Any] = None,
    headers: Optional[Dict[str, str]] = None,
    allow_refresh: bool = True,
) -> requests.Response:
    tokens = ensure_tokens(config, store)
    url = urljoin(config.base_url + "/", path.lstrip("/"))
    req_headers = {
        "Authorization": f"Bearer {tokens.access_token}",
        "Accept": "application/json",
    }
    if json_body is not None:
        req_headers["Content-Type"] = "application/json"
    if headers:
        req_headers.update(headers)
    resp = requests.request(
        method, url, params=params, json=json_body, headers=req_headers, timeout=60
    )

    if resp.status_code == 401 and allow_refresh:
        tokens = refresh_access_token(config, tokens)
        store.save(tokens)
        req_headers["Authorization"] = f"Bearer {tokens.access_token}"
        resp = requests.request(
            method, url, params=params, json=json_body, headers=req_headers, timeout=60
        )

    if resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", "1"))
        print(f"Rate limited. Retrying after {retry_after}s...", file=sys.stderr)
        time.sleep(retry_after)
        return api_request(
            method,
            config,
            store,
            path,
            params=params,
            json_body=json_body,
            headers=headers,
            allow_refresh=False,
        )

    if resp.status_code >= 400:
        raise SystemExit(
            f"API error {resp.status_code}: {resp.text}. "
            f"Path={path}, params={params}"
        )
    return resp


def paginate_get(
    config: AppConfig,
    store: TokenStore,
    path: str,
    *,
    params: Dict[str, Any],
    collection_key: str,
) -> Iterable[Dict[str, Any]]:
    page = int(params.get("page", 1))
    per_page = min(int(params.get("per_page", PAGE_MAX)), PAGE_MAX)
    while True:
        page_params = {**params, "page": page, "per_page": per_page}
        resp = api_request("GET", config, store, path, params=page_params)
        payload = resp.json()
        items = payload.get(collection_key, [])
        for item in items:
            yield item
        if len(items) < per_page:
            break
        page += 1


def _project_fields(
    rows: List[Dict[str, Any]], fields: List[str]
) -> List[Dict[str, Any]]:
    return [{k: row.get(k, "") for k in fields} for row in rows]


def format_output(
    rows: List[Dict[str, Any]], fields: List[str], output_format: str
) -> str:
    projected = _project_fields(rows, fields)

    if output_format == "csv":
        import csv
        from io import StringIO

        buf = StringIO()
        writer = csv.DictWriter(buf, fieldnames=fields)
        writer.writeheader()
        writer.writerows(projected)
        return buf.getvalue()

    if output_format == "json":
        return json.dumps(projected, indent=2)

    if output_format == "yaml":
        import yaml

        return yaml.safe_dump(projected, sort_keys=False)

    # plain table (default)
    table = [[row.get(f, "") for f in fields] for row in projected]
    return tabulate(table, headers=fields, tablefmt="github")


def parse_json_body(raw: str) -> Dict[str, Any]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON body: {exc}") from exc


# Handlers for subcommands


def handle_auth(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    tokens = start_auth_flow(config, args.port, not args.no_browser)
    store.save(tokens)
    print(
        f"Tokens saved to {store.env_path}. Try: uv run scripts/fa_cli.py invoices list"
    )


def handle_bank_accounts_list(
    args: argparse.Namespace, config: AppConfig, store: TokenStore
) -> None:
    params = {"per_page": args.per_page, "page": args.page}
    rows = list(
        paginate_get(
            config,
            store,
            "/bank_accounts",
            params=params,
            collection_key="bank_accounts",
        )
    )
    fields = ["url", "name", "type", "currency", "current_balance"]
    print(format_output(rows, fields, args.format))


def handle_bank_transactions_list(
    args: argparse.Namespace, config: AppConfig, store: TokenStore
) -> None:
    params = {
        "bank_account": args.bank_account,
        "from_date": args.from_date,
        "to_date": args.to_date,
        "view": args.view,
        "updated_since": args.updated_since,
        "per_page": args.per_page,
        "page": args.page,
    }
    params = {k: v for k, v in params.items() if v is not None}
    rows = list(
        paginate_get(
            config,
            store,
            "/bank_transactions",
            params=params,
            collection_key="bank_transactions",
        )
    )
    fields = [
        "url",
        "dated_on",
        "unexplained_amount",
        "description",
        "is_bank_account_transfer",
    ]
    print(format_output(rows, fields, args.format))


def handle_bank_transactions_get(
    args: argparse.Namespace, config: AppConfig, store: TokenStore
) -> None:
    resp = api_request("GET", config, store, f"/bank_transactions/{args.id}")
    data = resp.json().get("bank_transaction", {})
    print(json.dumps(data, indent=2))


def handle_bank_transactions_delete(
    args: argparse.Namespace, config: AppConfig, store: TokenStore
) -> None:
    if args.dry_run:
        print(f"[dry-run] Would delete bank transaction {args.id}")
        return
    api_request("DELETE", config, store, f"/bank_transactions/{args.id}")
    print(f"Deleted bank transaction {args.id}")


def handle_bills_list(
    args: argparse.Namespace, config: AppConfig, store: TokenStore
) -> None:
    params = {
        "view": args.view,
        "from_date": args.from_date,
        "to_date": args.to_date,
        "updated_since": args.updated_since,
        "nested_bill_items": str(args.nested_bill_items).lower(),
        "per_page": args.per_page,
        "page": args.page,
    }
    params = {k: v for k, v in params.items() if v not in (None, "false")}
    rows = list(
        paginate_get(config, store, "/bills", params=params, collection_key="bills")
    )
    fields = ["url", "reference", "dated_on", "due_on", "total_value", "status"]
    print(format_output(rows, fields, args.format))


def handle_bills_get(
    args: argparse.Namespace, config: AppConfig, store: TokenStore
) -> None:
    resp = api_request("GET", config, store, f"/bills/{args.id}")
    print(json.dumps(resp.json().get("bill", {}), indent=2))


def handle_bills_create(
    args: argparse.Namespace, config: AppConfig, store: TokenStore
) -> None:
    body = parse_json_body(args.body)
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return
    resp = api_request("POST", config, store, "/bills", json_body=body)
    print(json.dumps(resp.json(), indent=2))


def handle_bills_update(
    args: argparse.Namespace, config: AppConfig, store: TokenStore
) -> None:
    body = parse_json_body(args.body)
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return
    resp = api_request("PUT", config, store, f"/bills/{args.id}", json_body=body)
    print(json.dumps(resp.json(), indent=2))


def handle_bills_delete(
    args: argparse.Namespace, config: AppConfig, store: TokenStore
) -> None:
    if args.dry_run:
        print(f"[dry-run] Would delete bill {args.id}")
        return
    api_request("DELETE", config, store, f"/bills/{args.id}")
    print(f"Deleted bill {args.id}")


def handle_invoices_list(
    args: argparse.Namespace, config: AppConfig, store: TokenStore
) -> None:
    params = {
        "view": args.view,
        "updated_since": args.updated_since,
        "sort": args.sort,
        "nested_invoice_items": str(args.nested_invoice_items).lower(),
        "per_page": args.per_page,
        "page": args.page,
    }
    params = {k: v for k, v in params.items() if v not in (None, "false")}
    rows = list(
        paginate_get(
            config, store, "/invoices", params=params, collection_key="invoices"
        )
    )
    fields = [
        "url",
        "reference",
        "contact",
        "status",
        "dated_on",
        "due_on",
        "total_value",
    ]
    print(format_output(rows, fields, args.format))


def handle_invoices_get(
    args: argparse.Namespace, config: AppConfig, store: TokenStore
) -> None:
    resp = api_request("GET", config, store, f"/invoices/{args.id}")
    print(json.dumps(resp.json().get("invoice", {}), indent=2))


def handle_invoices_create(
    args: argparse.Namespace, config: AppConfig, store: TokenStore
) -> None:
    body = parse_json_body(args.body)
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return
    resp = api_request("POST", config, store, "/invoices", json_body=body)
    print(json.dumps(resp.json(), indent=2))


def handle_invoices_update(
    args: argparse.Namespace, config: AppConfig, store: TokenStore
) -> None:
    body = parse_json_body(args.body)
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return
    resp = api_request("PUT", config, store, f"/invoices/{args.id}", json_body=body)
    print(json.dumps(resp.json(), indent=2))


def handle_invoices_delete(
    args: argparse.Namespace, config: AppConfig, store: TokenStore
) -> None:
    if args.dry_run:
        print(f"[dry-run] Would delete invoice {args.id}")
        return
    api_request("DELETE", config, store, f"/invoices/{args.id}")
    print(f"Deleted invoice {args.id}")


def handle_reports_profit_loss(
    args: argparse.Namespace, config: AppConfig, store: TokenStore
) -> None:
    params = {
        "from_date": args.from_date,
        "to_date": args.to_date,
        "accounting_period": args.accounting_period,
    }
    params = {k: v for k, v in params.items() if v}
    resp = api_request(
        "GET", config, store, "/accounting/profit_and_loss/summary", params=params
    )
    data = resp.json().get("profit_and_loss", {})
    print(json.dumps(data, indent=2))


def handle_reports_balance_sheet(
    args: argparse.Namespace, config: AppConfig, store: TokenStore
) -> None:
    params = {"as_at_date": args.as_at_date}
    params = {k: v for k, v in params.items() if v}
    resp = api_request("GET", config, store, "/accounting/balance_sheet", params=params)
    print(json.dumps(resp.json().get("balance_sheet", {}), indent=2))


def handle_reports_trial_balance(
    args: argparse.Namespace, config: AppConfig, store: TokenStore
) -> None:
    params = {"from_date": args.from_date, "to_date": args.to_date}
    params = {k: v for k, v in params.items() if v}
    resp = api_request(
        "GET", config, store, "/accounting/trial_balance/summary", params=params
    )
    print(json.dumps(resp.json().get("trial_balance", {}), indent=2))


# CLI assembly


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FreeAgent FinOps CLI")
    parser.add_argument(
        "--env-file",
        default=str(DEFAULT_ENV_FILE),
        help="Path to .env file (default: .env)",
    )
    parser.add_argument(
        "--base-url", default=API_BASE_URL, help="Override API base URL"
    )
    parser.add_argument(
        "--format",
        default="plain",
        choices=["plain", "csv", "json", "yaml"],
        help="Output format for list commands",
    )
    parser.add_argument("--page", type=int, default=1, help="Pagination start page")
    parser.add_argument(
        "--per-page", type=int, default=PAGE_MAX, help="Items per page (max 100)"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Print verbose debug output for HTTP calls"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Auth
    auth_p = subparsers.add_parser("auth", help="Run OAuth flow and cache tokens")
    auth_p.add_argument(
        "--port", type=int, default=8888, help="Local port for OAuth callback"
    )
    auth_p.add_argument(
        "--no-browser", action="store_true", help="Do not auto-open the browser"
    )
    auth_p.set_defaults(func=handle_auth)

    # Bank accounts
    ba = subparsers.add_parser("bank-accounts", help="Bank account operations")
    ba_sub = ba.add_subparsers(dest="action", required=True)

    ba_list = ba_sub.add_parser("list", help="List bank accounts")
    ba_list.set_defaults(func=handle_bank_accounts_list)

    # Bank transactions
    bt = subparsers.add_parser("bank-transactions", help="Bank transaction operations")
    bt_sub = bt.add_subparsers(dest="action", required=True)

    bt_list = bt_sub.add_parser("list", help="List bank transactions")
    bt_list.add_argument("--bank-account", required=True, help="Bank account URL")
    bt_list.add_argument("--from-date", help="Filter from date (YYYY-MM-DD)")
    bt_list.add_argument("--to-date", help="Filter to date (YYYY-MM-DD)")
    bt_list.add_argument(
        "--view",
        choices=["all", "unexplained", "uncategorised", "explained"],
        help="View filter",
    )
    bt_list.add_argument("--updated-since", help="Filter by updated_since timestamp")
    bt_list.set_defaults(func=handle_bank_transactions_list)

    bt_get = bt_sub.add_parser("get", help="Get a single bank transaction")
    bt_get.add_argument("id", help="Transaction ID")
    bt_get.set_defaults(func=handle_bank_transactions_get)

    bt_del = bt_sub.add_parser("delete", help="Delete an unexplained bank transaction")
    bt_del.add_argument("id", help="Transaction ID")
    bt_del.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deletion without calling the API",
    )
    bt_del.set_defaults(func=handle_bank_transactions_delete)

    # Bills
    bills = subparsers.add_parser("bills", help="Bill operations")
    bills_sub = bills.add_subparsers(dest="action", required=True)

    bills_list = bills_sub.add_parser("list", help="List bills")
    bills_list.add_argument("--view", help="View filter (open, overdue, etc.)")
    bills_list.add_argument("--from-date")
    bills_list.add_argument("--to-date")
    bills_list.add_argument("--updated-since")
    bills_list.add_argument(
        "--nested-bill-items", action="store_true", help="Include nested bill items"
    )
    bills_list.set_defaults(func=handle_bills_list)

    bills_get = bills_sub.add_parser("get", help="Get bill by ID")
    bills_get.add_argument("id", help="Bill ID")
    bills_get.set_defaults(func=handle_bills_get)

    bills_create = bills_sub.add_parser("create", help="Create a bill from JSON body")
    bills_create.add_argument(
        "--body", required=True, help='JSON payload: {"bill": {...}}'
    )
    bills_create.add_argument("--dry-run", action="store_true")
    bills_create.set_defaults(func=handle_bills_create)

    bills_update = bills_sub.add_parser("update", help="Update a bill from JSON body")
    bills_update.add_argument("id", help="Bill ID")
    bills_update.add_argument(
        "--body", required=True, help='JSON payload: {"bill": {...}}'
    )
    bills_update.add_argument("--dry-run", action="store_true")
    bills_update.set_defaults(func=handle_bills_update)

    bills_delete = bills_sub.add_parser("delete", help="Delete a bill")
    bills_delete.add_argument("id", help="Bill ID")
    bills_delete.add_argument("--dry-run", action="store_true")
    bills_delete.set_defaults(func=handle_bills_delete)

    # Invoices
    invoices = subparsers.add_parser("invoices", help="Invoice operations")
    inv_sub = invoices.add_subparsers(dest="action", required=True)

    inv_list = inv_sub.add_parser("list", help="List invoices")
    inv_list.add_argument("--view")
    inv_list.add_argument("--updated-since")
    inv_list.add_argument("--sort", choices=["created_at", "updated_at"])
    inv_list.add_argument(
        "--nested-invoice-items",
        action="store_true",
        help="Include nested invoice items",
    )
    inv_list.set_defaults(func=handle_invoices_list)

    inv_get = inv_sub.add_parser("get", help="Get invoice by ID")
    inv_get.add_argument("id", help="Invoice ID")
    inv_get.set_defaults(func=handle_invoices_get)

    inv_create = inv_sub.add_parser("create", help="Create an invoice from JSON body")
    inv_create.add_argument(
        "--body", required=True, help='JSON payload: {"invoice": {...}}'
    )
    inv_create.add_argument("--dry-run", action="store_true")
    inv_create.set_defaults(func=handle_invoices_create)

    inv_update = inv_sub.add_parser("update", help="Update an invoice from JSON body")
    inv_update.add_argument("id", help="Invoice ID")
    inv_update.add_argument(
        "--body", required=True, help='JSON payload: {"invoice": {...}}'
    )
    inv_update.add_argument("--dry-run", action="store_true")
    inv_update.set_defaults(func=handle_invoices_update)

    inv_delete = inv_sub.add_parser("delete", help="Delete an invoice")
    inv_delete.add_argument("id", help="Invoice ID")
    inv_delete.add_argument("--dry-run", action="store_true")
    inv_delete.set_defaults(func=handle_invoices_delete)

    # Reports
    reports = subparsers.add_parser("reports", help="Accounting reports")
    rep_sub = reports.add_subparsers(dest="action", required=True)

    rep_pl = rep_sub.add_parser("profit-loss", help="Profit and loss summary")
    rep_pl.add_argument("--from-date", required=True)
    rep_pl.add_argument("--to-date", required=True)
    rep_pl.add_argument("--accounting-period", help="Optional accounting period token")
    rep_pl.set_defaults(func=handle_reports_profit_loss)

    rep_bs = rep_sub.add_parser("balance-sheet", help="Balance sheet")
    rep_bs.add_argument("--as-at-date", help="Report date (YYYY-MM-DD)")
    rep_bs.set_defaults(func=handle_reports_balance_sheet)

    rep_tb = rep_sub.add_parser("trial-balance", help="Trial balance summary")
    rep_tb.add_argument("--from-date")
    rep_tb.add_argument("--to-date")
    rep_tb.set_defaults(func=handle_reports_trial_balance)

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    args = build_parser().parse_args(argv)
    env_path = Path(args.env_file)
    config, env_file_data, env_lookup = load_config(
        env_path, base_url=args.base_url, debug=args.debug
    )
    store = TokenStore(env_path, env_file_data, env_lookup)

    # Adjust global defaults for pagination/format for handlers
    args.per_page = min(args.per_page, PAGE_MAX)

    args.func(args, config, store)


if __name__ == "__main__":
    main()
