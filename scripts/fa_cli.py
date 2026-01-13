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
import mimetypes
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
    request_timeout: float = 60.0


class TokenStore:
    def __init__(self, env_path: Path, env_file_data: Dict[str, str], env_lookup: Dict[str, str]):
        self.env_path = env_path
        self.env_file_data = env_file_data
        self.env_lookup = env_lookup

    def load(self) -> Optional[OAuthTokens]:
        access = self.env_lookup.get("FREEAGENT_ACCESS_TOKEN") or self.env_lookup.get("ACCESS_TOKEN")
        refresh = self.env_lookup.get("FREEAGENT_REFRESH_TOKEN") or self.env_lookup.get("REFRESH_TOKEN")
        expires_at_raw = self.env_lookup.get("FREEAGENT_EXPIRES_AT") or self.env_lookup.get("EXPIRES_AT")
        if not access:
            return None
        expires_at = float(expires_at_raw) if expires_at_raw else 0.0
        return OAuthTokens(access_token=access, refresh_token=refresh or "", expires_at=expires_at)

    def save(self, tokens: OAuthTokens) -> None:
        self.env_file_data["FREEAGENT_ACCESS_TOKEN"] = tokens.access_token
        self.env_lookup["FREEAGENT_ACCESS_TOKEN"] = tokens.access_token
        if tokens.refresh_token:
            self.env_file_data["FREEAGENT_REFRESH_TOKEN"] = tokens.refresh_token
            self.env_lookup["FREEAGENT_REFRESH_TOKEN"] = tokens.refresh_token
        self.env_file_data["FREEAGENT_EXPIRES_AT"] = str(tokens.expires_at)
        self.env_lookup["FREEAGENT_EXPIRES_AT"] = str(tokens.expires_at)
        lines = [f"{k}={v}" for k, v in sorted(self.env_file_data.items()) if k.isupper()]
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
    env_path: Path, base_url: str, *, debug: bool = False, request_timeout: float = 60.0
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
        request_timeout=request_timeout,
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
    auth_basic = base64.b64encode(f"{config.oauth_id}:{config.oauth_secret}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_basic}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    resp = requests.post(TOKEN_ENDPOINT, data=payload, headers=headers, timeout=30)

    if resp.status_code >= 400:
        debug_lines: List[str] = []
        debug_lines.append(f"grant_type={payload.get('grant_type')}, redirect_uri={payload.get('redirect_uri')}")
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
            + (detail if config.debug else f"Status {resp.status_code}. Enable --debug for details.")
        )

    if config.debug:
        print(f"Token request succeeded: status={resp.status_code} content-type={resp.headers.get('Content-Type')}")

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
        msg = "Authorization received. You may close this window." if code else "Authorization failed."
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
    data: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    allow_refresh: bool = True,
) -> requests.Response:
    tokens = ensure_tokens(config, store)
    url = urljoin(config.base_url + "/", path.lstrip("/"))
    if config.debug:
        print(
            "HTTP "
            f"{method} {url} params={params} json_body_present={json_body is not None} "
            f"files_present={files is not None} timeout={config.request_timeout}"
        )
    req_headers = {
        "Authorization": f"Bearer {tokens.access_token}",
        "Accept": "application/json",
    }
    if json_body is not None and files is None:
        req_headers["Content-Type"] = "application/json"
    if headers:
        req_headers.update(headers)
    resp = requests.request(
        method,
        url,
        params=params,
        json=json_body,
        data=data,
        files=files,
        headers=req_headers,
        timeout=config.request_timeout,
    )

    if resp.status_code == 401 and allow_refresh:
        tokens = refresh_access_token(config, tokens)
        store.save(tokens)
        req_headers["Authorization"] = f"Bearer {tokens.access_token}"
        resp = requests.request(
            method,
            url,
            params=params,
            json=json_body,
            data=data,
            files=files,
            headers=req_headers,
            timeout=config.request_timeout,
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
            data=data,
            files=files,
            headers=headers,
            allow_refresh=False,
        )

    if resp.status_code >= 400:
        raise SystemExit(f"API error {resp.status_code}: {resp.text}. " f"Path={path}, params={params}")
    return resp


def paginate_get(
    config: AppConfig,
    store: TokenStore,
    path: str,
    *,
    params: Dict[str, Any],
    collection_key: str,
    max_pages: Optional[int] = None,
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
        if max_pages is not None and page >= max_pages:
            break
        page += 1


def _project_fields(rows: List[Dict[str, Any]], fields: List[str]) -> List[Dict[str, Any]]:
    return [{k: row.get(k, "") for k in fields} for row in rows]


def format_output(rows: List[Dict[str, Any]], fields: List[str], output_format: str) -> str:
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
    print(f"Tokens saved to {store.env_path}. Try: uv run scripts/fa_cli.py invoices list")


def handle_bank_accounts_list(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {"per_page": args.per_page, "page": args.page}
    rows = list(
        paginate_get(
            config,
            store,
            "/bank_accounts",
            params=params,
            collection_key="bank_accounts",
            max_pages=args.max_pages,
        )
    )
    fields = ["url", "name", "type", "currency", "current_balance"]
    print(format_output(rows, fields, args.format))


def handle_bank_feeds_list(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {"per_page": args.per_page, "page": args.page}
    rows = list(
        paginate_get(
            config,
            store,
            "/bank_feeds",
            params=params,
            collection_key="bank_feeds",
            max_pages=args.max_pages,
        )
    )
    fields = [
        "url",
        "bank_account",
        "state",
        "feed_type",
        "bank_service_name",
        "sca_expires_at",
        "created_at",
        "updated_at",
    ]
    print(format_output(rows, fields, args.format))


def handle_bank_feeds_get(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    resp = api_request("GET", config, store, f"/bank_feeds/{args.id}")
    feed = resp.json().get("bank_feed", {})
    fields = [
        "url",
        "bank_account",
        "state",
        "feed_type",
        "bank_service_name",
        "sca_expires_at",
        "created_at",
        "updated_at",
    ]
    print(format_output([feed], fields, args.format))


def handle_contacts_list(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {
        "view": args.view,
        "search": args.search,
        "updated_since": args.updated_since,
        "per_page": args.per_page,
        "page": args.page,
    }
    params = {k: v for k, v in params.items() if v not in (None, "")}
    rows = list(
        paginate_get(
            config,
            store,
            "/contacts",
            params=params,
            collection_key="contacts",
            max_pages=args.max_pages,
        )
    )
    fields = ["url", "first_name", "last_name", "organisation_name", "email"]
    print(format_output(rows, fields, args.format))


def handle_contacts_get(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    resp = api_request("GET", config, store, f"/contacts/{args.id}")
    contact = resp.json().get("contact", {})
    fields = [
        "url",
        "first_name",
        "last_name",
        "organisation_name",
        "email",
        "phone_number",
        "mobile",
        "address1",
        "address2",
        "address3",
        "town",
        "region",
        "postcode",
        "country",
        "created_at",
        "updated_at",
    ]
    print(format_output([contact], fields, args.format))


def handle_contacts_update(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    body = parse_json_body(args.body)
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return
    resp = api_request("PUT", config, store, f"/contacts/{args.id}", json_body=body)
    print(json.dumps(resp.json(), indent=2))


def handle_expenses_list(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {
        "view": args.view,
        "from_date": args.from_date,
        "to_date": args.to_date,
        "updated_since": args.updated_since,
        "project": args.project,
        "per_page": args.per_page,
        "page": args.page,
    }
    params = {k: v for k, v in params.items() if v not in (None, "")}
    rows = list(
        paginate_get(
            config,
            store,
            "/expenses",
            params=params,
            collection_key="expenses",
            max_pages=args.max_pages,
        )
    )
    fields = ["url", "dated_on", "category", "description", "gross_value", "currency"]
    print(format_output(rows, fields, args.format))


def handle_payroll_list_periods(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    path = f"/payroll/{args.year}"
    resp = api_request("GET", config, store, path)
    periods = resp.json().get("periods", [])
    fields = ["url", "period", "frequency", "dated_on", "status"]
    print(format_output(periods, fields, args.format))


def handle_payroll_list_payslips(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    path = f"/payroll/{args.year}/{args.period}"
    resp = api_request("GET", config, store, path)
    period = resp.json().get("period", {})
    payslips = period.get("payslips", [])
    fields = [
        "user",
        "dated_on",
        "tax_code",
        "basic_pay",
        "tax_deducted",
        "employee_ni",
        "employer_ni",
        "net_pay",
    ]
    print(format_output(payslips, fields, args.format))


def handle_company_info(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    resp = api_request("GET", config, store, "/company")
    company = resp.json().get("company", {})
    fields = [
        "url",
        "name",
        "subdomain",
        "type",
        "currency",
        "mileage_units",
        "company_start_date",
        "trading_start_date",
        "freeagent_start_date",
        "first_accounting_year_end",
        "sales_tax_registration_status",
        "sales_tax_registration_number",
        "business_type",
        "business_category",
    ]
    print(format_output([company], fields, args.format))


def handle_company_business_categories(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    resp = api_request("GET", config, store, "/company/business_categories")
    categories = resp.json().get("business_categories", [])
    rows = [{"business_category": name} for name in categories]
    print(format_output(rows, ["business_category"], args.format))


def handle_company_tax_timeline(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    resp = api_request("GET", config, store, "/company/tax_timeline")
    items = resp.json().get("timeline_items", [])
    fields = ["description", "nature", "dated_on", "amount_due", "is_personal"]
    print(format_output(items, fields, args.format))


def handle_capital_assets_list(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {
        "view": args.view,
        "include_history": (str(args.include_history).lower() if args.include_history else None),
        "per_page": args.per_page,
        "page": args.page,
    }
    params = {k: v for k, v in params.items() if v not in (None, "")}
    rows = list(
        paginate_get(
            config,
            store,
            "/capital_assets",
            params=params,
            collection_key="capital_assets",
            max_pages=args.max_pages,
        )
    )
    fields = [
        "url",
        "description",
        "asset_type",
        "purchased_on",
        "disposed_on",
        "asset_life_years",
        "depreciation_profile",
        "capital_asset_history",
        "created_at",
        "updated_at",
    ]
    print(format_output(rows, fields, args.format))


def handle_capital_assets_get(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {"include_history": (str(args.include_history).lower() if args.include_history else None)}
    params = {k: v for k, v in params.items() if v not in (None, "")}
    resp = api_request("GET", config, store, f"/capital_assets/{args.id}", params=params)
    asset = resp.json().get("capital_asset", {})
    fields = [
        "url",
        "description",
        "asset_type",
        "purchased_on",
        "disposed_on",
        "asset_life_years",
        "depreciation_profile",
        "capital_asset_history",
        "created_at",
        "updated_at",
    ]
    print(format_output([asset], fields, args.format))


def handle_capital_assets_create(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    body = parse_json_body(args.body)
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return
    resp = api_request("POST", config, store, "/capital_assets", json_body=body)
    print(json.dumps(resp.json(), indent=2))


def handle_capital_assets_update(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    body = parse_json_body(args.body)
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return
    resp = api_request("PUT", config, store, f"/capital_assets/{args.id}", json_body=body)
    print(json.dumps(resp.json(), indent=2))


def handle_capital_assets_delete(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    if args.dry_run:
        print(f"[dry-run] Would delete capital asset {args.id}")
        return
    api_request("DELETE", config, store, f"/capital_assets/{args.id}")
    print(f"Deleted capital asset {args.id}")


def handle_capital_asset_types_list(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {"per_page": args.per_page, "page": args.page}
    rows = list(
        paginate_get(
            config,
            store,
            "/capital_asset_types",
            params=params,
            collection_key="capital_asset_types",
            max_pages=args.max_pages,
        )
    )
    fields = ["url", "name", "system_default", "created_at", "updated_at"]
    print(format_output(rows, fields, args.format))


def handle_capital_asset_types_get(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    resp = api_request("GET", config, store, f"/capital_asset_types/{args.id}")
    asset_type = resp.json().get("capital_asset_type", {})
    fields = ["url", "name", "system_default", "created_at", "updated_at"]
    print(format_output([asset_type], fields, args.format))


def handle_capital_asset_types_create(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    body = parse_json_body(args.body)
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return
    resp = api_request("POST", config, store, "/capital_asset_types", json_body=body)
    print(json.dumps(resp.json(), indent=2))


def handle_capital_asset_types_update(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    body = parse_json_body(args.body)
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return
    resp = api_request("PUT", config, store, f"/capital_asset_types/{args.id}", json_body=body)
    print(json.dumps(resp.json(), indent=2))


def handle_capital_asset_types_delete(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    if args.dry_run:
        print(f"[dry-run] Would delete capital asset type {args.id}")
        return
    api_request("DELETE", config, store, f"/capital_asset_types/{args.id}")
    print(f"Deleted capital asset type {args.id}")


def handle_users_list(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {
        "view": args.view,
        "per_page": args.per_page,
        "page": args.page,
    }
    params = {k: v for k, v in params.items() if v not in (None, "")}
    rows = list(
        paginate_get(
            config,
            store,
            "/users",
            params=params,
            collection_key="users",
            max_pages=args.max_pages,
        )
    )
    fields = [
        "url",
        "first_name",
        "last_name",
        "email",
        "role",
        "permission_level",
        "opening_mileage",
        "created_at",
        "updated_at",
    ]
    print(format_output(rows, fields, args.format))


def handle_users_get(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    path = "/users/me" if args.id == "me" else f"/users/{args.id}"
    resp = api_request("GET", config, store, path)
    user = resp.json().get("user", {})
    fields = [
        "url",
        "first_name",
        "last_name",
        "email",
        "role",
        "permission_level",
        "opening_mileage",
        "created_at",
        "updated_at",
    ]
    print(format_output([user], fields, args.format))


def handle_users_me(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    handle_users_get(argparse.Namespace(id="me", format=args.format), config, store)


def handle_users_delete(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    if args.dry_run:
        print(f"[dry-run] Would delete user {args.id}")
        return
    api_request("DELETE", config, store, f"/users/{args.id}")
    print(f"Deleted user {args.id}")


def handle_users_update_permission(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    body = {"user": {"permission_level": args.permission_level}}
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return
    resp = api_request("PUT", config, store, f"/users/{args.id}", json_body=body)
    print(json.dumps(resp.json(), indent=2))


def handle_users_permission(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    resp = api_request("GET", config, store, f"/users/{args.id}")
    user = resp.json().get("user", {})
    print(json.dumps({"permission_level": user.get("permission_level")}, indent=2))


def handle_users_set_hidden(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    body = {"user": {"hidden": args.hidden}}
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return
    resp = api_request("PUT", config, store, f"/users/{args.id}", json_body=body)
    print(json.dumps(resp.json(), indent=2))


def handle_timeslips_list(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {
        "user": args.user,
        "project": args.project,
        "task": args.task,
        "from_date": args.from_date,
        "to_date": args.to_date,
        "view": args.view,
        "per_page": args.per_page,
        "page": args.page,
    }
    params = {k: v for k, v in params.items() if v not in (None, "")}
    rows = list(
        paginate_get(
            config,
            store,
            "/timeslips",
            params=params,
            collection_key="timeslips",
            max_pages=args.max_pages,
        )
    )
    fields = [
        "url",
        "user",
        "project",
        "task",
        "dated_on",
        "hours",
        "billable",
        "billed_on",
        "comment",
    ]
    print(format_output(rows, fields, args.format))


def handle_timeslips_delete(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    if args.dry_run:
        print(f"[dry-run] Would delete timeslip {args.id}")
        return
    api_request("DELETE", config, store, f"/timeslips/{args.id}")
    print(f"Deleted timeslip {args.id}")


def handle_final_accounts_list(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {"per_page": args.per_page, "page": args.page}
    rows = list(
        paginate_get(
            config,
            store,
            "/final_accounts_reports",
            params=params,
            collection_key="final_accounts_reports",
            max_pages=args.max_pages,
        )
    )
    fields = [
        "url",
        "period_ends_on",
        "period_starts_on",
        "filing_due_on",
        "filing_status",
        "filed_at",
        "filed_reference",
    ]
    print(format_output(rows, fields, args.format))


def handle_final_accounts_get(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    resp = api_request("GET", config, store, f"/final_accounts_reports/{args.period_ends_on}")
    report = resp.json().get("final_accounts_report", {})
    fields = [
        "url",
        "period_ends_on",
        "period_starts_on",
        "filing_due_on",
        "filing_status",
        "filed_at",
        "filed_reference",
    ]
    print(format_output([report], fields, args.format))


def handle_final_accounts_mark_as_filed(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    path = f"/final_accounts_reports/{args.period_ends_on}/mark_as_filed"
    resp = api_request("PUT", config, store, path)
    print(json.dumps(resp.json(), indent=2))


def handle_final_accounts_mark_as_unfiled(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    path = f"/final_accounts_reports/{args.period_ends_on}/mark_as_unfiled"
    resp = api_request("PUT", config, store, path)
    print(json.dumps(resp.json(), indent=2))


def handle_projects_list(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {
        "view": args.view,
        "updated_since": args.updated_since,
        "per_page": args.per_page,
        "page": args.page,
    }
    params = {k: v for k, v in params.items() if v not in (None, "")}
    rows = list(
        paginate_get(
            config,
            store,
            "/projects",
            params=params,
            collection_key="projects",
            max_pages=args.max_pages,
        )
    )
    fields = [
        "url",
        "name",
        "status",
        "contact",
        "currency",
        "budget_units",
        "budget",
        "normal_billing_rate",
        "started_on",
        "ended_on",
    ]
    print(format_output(rows, fields, args.format))


def handle_projects_get(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    resp = api_request("GET", config, store, f"/projects/{args.id}")
    project = resp.json().get("project", {})
    fields = [
        "url",
        "name",
        "status",
        "contact",
        "currency",
        "budget_units",
        "budget",
        "normal_billing_rate",
        "started_on",
        "ended_on",
    ]
    print(format_output([project], fields, args.format))


def handle_bank_transactions_list(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
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
            max_pages=args.max_pages,
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


def handle_bank_transaction_explanations_list(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {
        "bank_account": args.bank_account,
        "from_date": args.from_date,
        "to_date": args.to_date,
        "updated_since": args.updated_since,
        "per_page": args.per_page,
        "page": args.page,
    }
    params = {k: v for k, v in params.items() if v is not None}
    rows = list(
        paginate_get(
            config,
            store,
            "/bank_transaction_explanations",
            params=params,
            collection_key="bank_transaction_explanations",
            max_pages=args.max_pages,
        )
    )
    fields = [
        "url",
        "bank_account",
        "bank_transaction",
        "category",
        "type",
        "dated_on",
        "description",
        "gross_value",
        "project",
        "rebill_type",
        "sales_tax_status",
        "sales_tax_rate",
        "marked_for_review",
        "is_deletable",
        "updated_at",
    ]
    if getattr(args, "for_approval", False):
        rows = [r for r in rows if str(r.get("marked_for_review", "")).lower() == "true"]
    print(format_output(rows, fields, args.format))


def handle_bank_transaction_explanations_get(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    resp = api_request("GET", config, store, f"/bank_transaction_explanations/{args.id}")
    explanation = resp.json().get("bank_transaction_explanation", {})
    fields = [
        "url",
        "bank_account",
        "bank_transaction",
        "category",
        "type",
        "dated_on",
        "description",
        "gross_value",
        "project",
        "rebill_type",
        "sales_tax_status",
        "sales_tax_rate",
        "is_deletable",
        "updated_at",
    ]
    print(format_output([explanation], fields, args.format))


def handle_bank_transaction_explanations_create(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    body = parse_json_body(args.body)
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return
    resp = api_request(
        "POST",
        config,
        store,
        "/bank_transaction_explanations",
        json_body=body,
    )
    print(json.dumps(resp.json(), indent=2))


def handle_bank_transaction_explanations_update(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    body = parse_json_body(args.body)
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return
    resp = api_request(
        "PUT",
        config,
        store,
        f"/bank_transaction_explanations/{args.id}",
        json_body=body,
    )
    print(json.dumps(resp.json(), indent=2))


def handle_bank_transaction_explanations_delete(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    if args.dry_run:
        print(f"[dry-run] Would delete bank transaction explanation {args.id}")
        return
    api_request("DELETE", config, store, f"/bank_transaction_explanations/{args.id}")
    print(f"Deleted bank transaction explanation {args.id}")


def handle_bank_transaction_explanations_approve(
    args: argparse.Namespace, config: AppConfig, store: TokenStore
) -> None:
    ids = args.ids
    payload = {"bank_transaction_explanation": {"marked_for_review": False}}
    for explanation_id in ids:
        if args.dry_run:
            print(
                json.dumps(
                    {"id": explanation_id, **payload},
                    indent=2,
                )
            )
            continue
        resp = api_request(
            "PUT",
            config,
            store,
            f"/bank_transaction_explanations/{explanation_id}",
            json_body=payload,
        )
        print(json.dumps(resp.json(), indent=2))


def handle_transactions_list(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {
        "from_date": args.from_date,
        "to_date": args.to_date,
        "nominal_code": args.nominal_code,
        "per_page": args.per_page,
        "page": args.page,
    }
    params = {k: v for k, v in params.items() if v not in (None, "")}
    rows = list(
        paginate_get(
            config,
            store,
            "/accounting/transactions",
            params=params,
            collection_key="transactions",
            max_pages=args.max_pages,
        )
    )
    fields = [
        "url",
        "dated_on",
        "description",
        "category",
        "category_name",
        "nominal_code",
        "debit_value",
        "source_item_url",
        "created_at",
        "updated_at",
        "foreign_currency_data",
    ]
    print(format_output(rows, fields, args.format))


def handle_transactions_get(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    resp = api_request("GET", config, store, f"/accounting/transactions/{args.id}")
    transaction = resp.json().get("transaction", {})
    fields = [
        "url",
        "dated_on",
        "description",
        "category",
        "category_name",
        "nominal_code",
        "debit_value",
        "source_item_url",
        "created_at",
        "updated_at",
        "foreign_currency_data",
    ]
    print(format_output([transaction], fields, args.format))


def handle_journal_sets_list(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {
        "from_date": args.from_date,
        "to_date": args.to_date,
        "updated_since": args.updated_since,
        "tag": args.tag,
        "per_page": args.per_page,
        "page": args.page,
    }
    params = {k: v for k, v in params.items() if v not in (None, "")}
    rows = list(
        paginate_get(
            config,
            store,
            "/journal_sets",
            params=params,
            collection_key="journal_sets",
            max_pages=args.max_pages,
        )
    )
    fields = ["url", "dated_on", "description", "updated_at", "tag"]
    print(format_output(rows, fields, args.format))


def handle_journal_sets_get(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    resp = api_request("GET", config, store, f"/journal_sets/{args.id}")
    journal_set = resp.json().get("journal_set", {})
    fields = [
        "url",
        "dated_on",
        "description",
        "updated_at",
        "tag",
        "journal_entries",
        "bank_accounts",
        "stock_items",
    ]
    print(format_output([journal_set], fields, args.format))


def handle_journal_sets_opening_balances(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    resp = api_request("GET", config, store, "/journal_sets/opening_balances")
    journal_set = resp.json().get("journal_set", {})
    fields = [
        "url",
        "dated_on",
        "description",
        "updated_at",
        "tag",
        "journal_entries",
        "bank_accounts",
        "stock_items",
    ]
    print(format_output([journal_set], fields, args.format))


def handle_journal_sets_create(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    body = parse_json_body(args.body)
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return
    resp = api_request("POST", config, store, "/journal_sets", json_body=body)
    print(json.dumps(resp.json(), indent=2))


def handle_journal_sets_update(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    body = parse_json_body(args.body)
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return
    resp = api_request(
        "PUT",
        config,
        store,
        f"/journal_sets/{args.id}",
        json_body=body,
    )
    print(json.dumps(resp.json(), indent=2))


def handle_journal_sets_delete(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    if args.dry_run:
        print(f"[dry-run] Would delete journal set {args.id}")
        return
    api_request("DELETE", config, store, f"/journal_sets/{args.id}")
    print(f"Deleted journal set {args.id}")


def handle_attachments_list(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {
        "attachable_type": args.attachable_type,
        "attachable_id": args.attachable_id,
        "per_page": args.per_page,
        "page": args.page,
    }
    params = {k: v for k, v in params.items() if v not in (None, "")}
    rows = list(
        paginate_get(
            config,
            store,
            "/attachments",
            params=params,
            collection_key="attachments",
            max_pages=args.max_pages,
        )
    )
    fields = [
        "url",
        "file_name",
        "content_type",
        "file_size",
        "description",
        "expires_at",
        "content_src",
    ]
    print(format_output(rows, fields, args.format))


def handle_attachments_get(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    resp = api_request("GET", config, store, f"/attachments/{args.id}")
    attachment = resp.json().get("attachment", {})
    fields = [
        "url",
        "file_name",
        "content_type",
        "file_size",
        "description",
        "expires_at",
        "content_src",
        "content_src_medium",
        "content_src_small",
    ]
    print(format_output([attachment], fields, args.format))


def handle_attachments_upload(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    file_path = Path(args.file)
    if not file_path.exists():
        raise SystemExit(f"File not found: {file_path}")
    content_type = args.content_type or mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    file_name = args.file_name or file_path.name
    form_data = {
        "description": args.description,
        "content_type": content_type,
        "file_name": file_name,
        "attachable_type": args.attachable_type,
        "attachable_id": args.attachable_id,
    }
    form_data = {k: v for k, v in form_data.items() if v not in (None, "")}

    if args.dry_run:
        preview = {"file": str(file_path), "form": form_data}
        print(json.dumps(preview, indent=2))
        return

    with file_path.open("rb") as fh:
        files = {"file": (file_name, fh, content_type)}
        resp = api_request(
            "POST",
            config,
            store,
            "/attachments",
            data=form_data,
            files=files,
        )
    print(json.dumps(resp.json(), indent=2))


def handle_attachments_delete(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    if args.dry_run:
        print(f"[dry-run] Would delete attachment {args.id}")
        return
    api_request("DELETE", config, store, f"/attachments/{args.id}")
    print(f"Deleted attachment {args.id}")


def handle_bank_transactions_get(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    resp = api_request("GET", config, store, f"/bank_transactions/{args.id}")
    data = resp.json().get("bank_transaction", {})
    print(json.dumps(data, indent=2))


def handle_bank_transactions_delete(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    if args.dry_run:
        print(f"[dry-run] Would delete bank transaction {args.id}")
        return
    api_request("DELETE", config, store, f"/bank_transactions/{args.id}")
    print(f"Deleted bank transaction {args.id}")


def handle_bills_list(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
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
        paginate_get(
            config,
            store,
            "/bills",
            params=params,
            collection_key="bills",
            max_pages=args.max_pages,
        )
    )
    fields = ["url", "reference", "dated_on", "due_on", "total_value", "status"]
    print(format_output(rows, fields, args.format))


def handle_bills_list_all(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {"per_page": args.per_page, "page": args.page}
    rows = list(
        paginate_get(
            config,
            store,
            "/bills",
            params=params,
            collection_key="bills",
            max_pages=args.max_pages,
        )
    )
    fields = ["url", "reference", "dated_on", "due_on", "total_value", "status"]
    print(format_output(rows, fields, args.format))


def handle_bills_get(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    resp = api_request("GET", config, store, f"/bills/{args.id}")
    print(json.dumps(resp.json().get("bill", {}), indent=2))


def handle_bills_create(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    body = parse_json_body(args.body)
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return
    resp = api_request("POST", config, store, "/bills", json_body=body)
    print(json.dumps(resp.json(), indent=2))


def handle_bills_update(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    body = parse_json_body(args.body)
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return
    resp = api_request("PUT", config, store, f"/bills/{args.id}", json_body=body)
    print(json.dumps(resp.json(), indent=2))


def handle_bills_delete(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    if args.dry_run:
        print(f"[dry-run] Would delete bill {args.id}")
        return
    api_request("DELETE", config, store, f"/bills/{args.id}")
    print(f"Deleted bill {args.id}")


def handle_invoices_list(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
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
            config,
            store,
            "/invoices",
            params=params,
            collection_key="invoices",
            max_pages=args.max_pages,
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


def handle_invoices_list_all(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {"per_page": args.per_page, "page": args.page}
    rows = list(
        paginate_get(
            config,
            store,
            "/invoices",
            params=params,
            collection_key="invoices",
            max_pages=args.max_pages,
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


def handle_invoices_get(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    resp = api_request("GET", config, store, f"/invoices/{args.id}")
    print(json.dumps(resp.json().get("invoice", {}), indent=2))


def handle_invoices_create(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    body = parse_json_body(args.body)
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return
    resp = api_request("POST", config, store, "/invoices", json_body=body)
    print(json.dumps(resp.json(), indent=2))


def handle_invoices_update(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    body = parse_json_body(args.body)
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return
    resp = api_request("PUT", config, store, f"/invoices/{args.id}", json_body=body)
    print(json.dumps(resp.json(), indent=2))


def handle_invoices_delete(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    if args.dry_run:
        print(f"[dry-run] Would delete invoice {args.id}")
        return
    api_request("DELETE", config, store, f"/invoices/{args.id}")
    print(f"Deleted invoice {args.id}")


def handle_reports_profit_loss(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {
        "from_date": args.from_date,
        "to_date": args.to_date,
        "accounting_period": args.accounting_period,
    }
    params = {k: v for k, v in params.items() if v not in (None, "")}
    resp = api_request("GET", config, store, "/accounting/profit_and_loss/summary", params=params)
    data = resp.json().get("profit_and_loss_summary", {})
    print(json.dumps(data, indent=2))


def handle_reports_balance_sheet(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {"as_at_date": args.as_at_date}
    params = {k: v for k, v in params.items() if v}
    resp = api_request("GET", config, store, "/accounting/balance_sheet", params=params)
    print(json.dumps(resp.json().get("balance_sheet", {}), indent=2))


def handle_reports_trial_balance(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {"from_date": args.from_date, "to_date": args.to_date}
    params = {k: v for k, v in params.items() if v}
    resp = api_request("GET", config, store, "/accounting/trial_balance/summary", params=params)
    print(json.dumps(resp.json().get("trial_balance", {}), indent=2))


def handle_cashflow_summary(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {"from_date": args.from_date, "to_date": args.to_date}
    params = {k: v for k, v in params.items() if v}
    resp = api_request("GET", config, store, "/cashflow", params=params)
    data = resp.json().get("cashflow", {})

    if args.format == "json":
        print(json.dumps(data, indent=2))
        return
    if args.format == "yaml":
        import yaml

        print(yaml.safe_dump(data, sort_keys=False))
        return

    rows = [
        {"label": "balance", "value": data.get("balance", "")},
        {"label": "incoming_total", "value": data.get("incoming", {}).get("total", "")},
        {"label": "outgoing_total", "value": data.get("outgoing", {}).get("total", "")},
        {"label": "from", "value": data.get("from", "")},
        {"label": "to", "value": data.get("to", "")},
    ]
    print(format_output(rows, ["label", "value"], args.format))


def handle_notes_list(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {"contact": args.contact, "project": args.project}
    params = {k: v for k, v in params.items() if v}
    resp = api_request("GET", config, store, "/notes", params=params)
    notes = resp.json().get("notes", [])
    fields = ["url", "note", "parent_url", "author", "created_at", "updated_at"]
    print(format_output(notes, fields, args.format))


def handle_notes_get(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    resp = api_request("GET", config, store, f"/notes/{args.id}")
    note = resp.json().get("note", {})
    fields = ["url", "note", "parent_url", "author", "created_at", "updated_at"]
    print(format_output([note], fields, args.format))


def handle_notes_create(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {"contact": args.contact, "project": args.project}
    params = {k: v for k, v in params.items() if v}
    body = parse_json_body(args.body)
    if args.dry_run:
        print(json.dumps({"params": params, "body": body}, indent=2))
        return
    resp = api_request("POST", config, store, "/notes", params=params, json_body=body)
    print(json.dumps(resp.json(), indent=2))


def handle_notes_update(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    body = parse_json_body(args.body)
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return
    resp = api_request("PUT", config, store, f"/notes/{args.id}", json_body=body)
    print(json.dumps(resp.json(), indent=2))


def handle_notes_delete(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    if args.dry_run:
        print(f"[dry-run] Would delete note {args.id}")
        return
    api_request("DELETE", config, store, f"/notes/{args.id}")
    print(f"Deleted note {args.id}")


def handle_depreciation_profiles_methods(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    rows = [
        {
            "method": "straight_line",
            "required_parameters": "asset_life_years",
            "optional_parameters": "frequency (monthly|annually)",
        },
        {
            "method": "reducing_balance",
            "required_parameters": "annual_depreciation_percentage",
            "optional_parameters": "frequency (monthly|annually)",
        },
        {
            "method": "no_depreciation",
            "required_parameters": "-",
            "optional_parameters": "frequency (monthly|annually)",
        },
    ]
    fields = ["method", "required_parameters", "optional_parameters"]
    print(format_output(rows, fields, args.format))


def handle_depreciation_profiles_build(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    method = args.method
    profile: Dict[str, Any] = {"method": method}

    if args.frequency:
        profile["frequency"] = args.frequency

    if method == "straight_line":
        if args.asset_life_years is None:
            raise SystemExit("--asset-life-years is required for straight_line")
        if not 2 <= args.asset_life_years <= 25:
            raise SystemExit("asset life years must be between 2 and 25")
        profile["asset_life_years"] = args.asset_life_years
    elif method == "reducing_balance":
        if args.annual_depreciation_percentage is None:
            raise SystemExit("--annual-depreciation-percentage is required for reducing_balance")
        if not 1 <= args.annual_depreciation_percentage <= 99:
            raise SystemExit("annual depreciation percentage must be between 1 and 99")
        profile["annual_depreciation_percentage"] = args.annual_depreciation_percentage
    else:
        if args.asset_life_years is not None:
            raise SystemExit("--asset-life-years is not used for no_depreciation")
        if args.annual_depreciation_percentage is not None:
            raise SystemExit("--annual-depreciation-percentage is not used for no_depreciation")

    payload = {"capital_asset": {"depreciation_profile": profile}}

    if args.format == "yaml":
        import yaml

        print(yaml.safe_dump(payload, sort_keys=False))
        return

    print(json.dumps(payload, indent=2))


def handle_sales_tax_moss_rates(args: argparse.Namespace, config: AppConfig, store: TokenStore) -> None:
    params = {"country": args.country, "date": args.date}
    resp = api_request("GET", config, store, "/ec_moss/sales_tax_rates", params=params)
    rates = resp.json().get("sales_tax_rates", [])

    if args.format == "json":
        print(json.dumps(rates, indent=2))
        return
    if args.format == "yaml":
        import yaml

        print(yaml.safe_dump(rates, sort_keys=False))
        return

    fields = ["percentage", "band"]
    print(format_output(rates, fields, args.format))


# CLI assembly


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FreeAgent FinOps CLI")
    parser.add_argument(
        "--env-file",
        default=str(DEFAULT_ENV_FILE),
        help="Path to .env file (default: .env)",
    )
    parser.add_argument("--base-url", default=API_BASE_URL, help="Override API base URL")
    parser.add_argument(
        "--format",
        default="plain",
        choices=["plain", "csv", "json", "yaml"],
        help="Output format for list commands",
    )
    parser.add_argument("--page", type=int, default=1, help="Pagination start page")
    parser.add_argument("--per-page", type=int, default=PAGE_MAX, help="Items per page (max 100)")
    parser.add_argument("--debug", action="store_true", help="Print verbose debug output for HTTP calls")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional maximum number of pages to fetch for list commands",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP connect/read timeout in seconds (default: 30)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Auth
    auth_p = subparsers.add_parser("auth", help="Run OAuth flow and cache tokens")
    auth_p.add_argument("--port", type=int, default=8888, help="Local port for OAuth callback")
    auth_p.add_argument("--no-browser", action="store_true", help="Do not auto-open the browser")
    auth_p.set_defaults(func=handle_auth)

    # Bank accounts
    ba = subparsers.add_parser("bank-accounts", help="Bank account operations")
    ba_sub = ba.add_subparsers(dest="action", required=True)

    ba_list = ba_sub.add_parser("list", help="List bank accounts")
    ba_list.set_defaults(func=handle_bank_accounts_list)

    # Bank feeds
    feeds = subparsers.add_parser("bank-feeds", help="Bank feed operations")
    feeds_sub = feeds.add_subparsers(dest="action", required=True)

    feeds_list = feeds_sub.add_parser("list", help="List bank feeds")
    feeds_list.set_defaults(func=handle_bank_feeds_list)

    feeds_get = feeds_sub.add_parser("get", help="Get a bank feed by ID")
    feeds_get.add_argument("id", help="Bank feed ID")
    feeds_get.set_defaults(func=handle_bank_feeds_get)

    # Contacts
    contacts = subparsers.add_parser("contacts", help="Contact operations")
    contacts_sub = contacts.add_subparsers(dest="action", required=True)

    contacts_list = contacts_sub.add_parser("list", help="List contacts")
    contacts_list.add_argument("--view", help="View filter (active, inactive)")
    contacts_list.add_argument("--search", help="Search by name or email")
    contacts_list.add_argument("--updated-since", help="Filter by updated_since")
    contacts_list.set_defaults(func=handle_contacts_list)

    contacts_get = contacts_sub.add_parser("get", help="Get a contact by ID")
    contacts_get.add_argument("id", help="Contact ID")
    contacts_get.set_defaults(func=handle_contacts_get)

    contacts_update = contacts_sub.add_parser("update", help="Update a contact from JSON body")
    contacts_update.add_argument("id", help="Contact ID")
    contacts_update.add_argument("--body", required=True, help='JSON payload: {"contact": {...}}')
    contacts_update.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview update without calling the API",
    )
    contacts_update.set_defaults(func=handle_contacts_update)

    # Expenses
    expenses = subparsers.add_parser("expenses", help="Expense operations")
    expenses_sub = expenses.add_subparsers(dest="action", required=True)

    expenses_list = expenses_sub.add_parser("list", help="List expenses")
    expenses_list.add_argument("--view", choices=["recent", "recurring"], help="View filter")
    expenses_list.add_argument("--from-date", help="Filter from date (YYYY-MM-DD)")
    expenses_list.add_argument("--to-date", help="Filter to date (YYYY-MM-DD)")
    expenses_list.add_argument("--updated-since", help="Filter by updated_since timestamp")
    expenses_list.add_argument("--project", help="Project URL to filter by project")
    expenses_list.set_defaults(func=handle_expenses_list)

    # Payroll
    payroll = subparsers.add_parser("payroll", help="Payroll operations")
    payroll_sub = payroll.add_subparsers(dest="action", required=True)

    payroll_periods = payroll_sub.add_parser("list-periods", help="List payroll periods for a tax year")
    payroll_periods.add_argument("--year", required=True, type=int, help="Payroll tax year end (e.g. 2026)")
    payroll_periods.set_defaults(func=handle_payroll_list_periods)

    payroll_payslips = payroll_sub.add_parser("list-payslips", help="List payslips for a payroll period")
    payroll_payslips.add_argument("--year", required=True, type=int, help="Payroll tax year end (e.g. 2026)")
    payroll_payslips.add_argument("--period", required=True, type=int, help="Payroll period number (0-11)")
    payroll_payslips.set_defaults(func=handle_payroll_list_payslips)

    # Company
    company = subparsers.add_parser("company", help="Company operations")
    company_sub = company.add_subparsers(dest="action", required=True)

    company_info = company_sub.add_parser("info", help="Show company information")
    company_info.set_defaults(func=handle_company_info)

    company_categories = company_sub.add_parser("business-categories", help="List all business categories")
    company_categories.set_defaults(func=handle_company_business_categories)

    company_timeline = company_sub.add_parser("tax-timeline", help="Show upcoming tax events")
    company_timeline.set_defaults(func=handle_company_tax_timeline)

    # Capital assets
    capital_assets = subparsers.add_parser("capital-assets", help="Capital asset operations")
    ca_sub = capital_assets.add_subparsers(dest="action", required=True)

    ca_list = ca_sub.add_parser("list", help="List capital assets")
    ca_list.add_argument(
        "--view",
        choices=["all", "disposed", "disposable"],
        help="Filter capital assets by view",
    )
    ca_list.add_argument(
        "--include-history",
        action="store_true",
        help="Include capital asset history events",
    )
    ca_list.set_defaults(func=handle_capital_assets_list)

    ca_get = ca_sub.add_parser("get", help="Get a capital asset by ID")
    ca_get.add_argument("id", help="Capital asset ID")
    ca_get.add_argument(
        "--include-history",
        action="store_true",
        help="Include capital asset history events",
    )
    ca_get.set_defaults(func=handle_capital_assets_get)

    ca_create = ca_sub.add_parser("create", help="Create a capital asset from JSON body")
    ca_create.add_argument("--body", required=True, help='JSON payload: {"capital_asset": {...}}')
    ca_create.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview creation without calling the API",
    )
    ca_create.set_defaults(func=handle_capital_assets_create)

    ca_update = ca_sub.add_parser("update", help="Update a capital asset from JSON body")
    ca_update.add_argument("id", help="Capital asset ID")
    ca_update.add_argument("--body", required=True, help='JSON payload: {"capital_asset": {...}}')
    ca_update.add_argument("--dry-run", action="store_true", help="Preview update without calling the API")
    ca_update.set_defaults(func=handle_capital_assets_update)

    ca_delete = ca_sub.add_parser("delete", help="Delete a capital asset")
    ca_delete.add_argument("id", help="Capital asset ID")
    ca_delete.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deletion without calling the API",
    )
    ca_delete.set_defaults(func=handle_capital_assets_delete)

    # Capital asset types
    cat = subparsers.add_parser("capital-asset-types", help="Capital asset type operations")
    cat_sub = cat.add_subparsers(dest="action", required=True)

    cat_list = cat_sub.add_parser("list", help="List capital asset types")
    cat_list.set_defaults(func=handle_capital_asset_types_list)

    cat_get = cat_sub.add_parser("get", help="Get a capital asset type by ID")
    cat_get.add_argument("id", help="Capital asset type ID")
    cat_get.set_defaults(func=handle_capital_asset_types_get)

    cat_create = cat_sub.add_parser("create", help="Create a capital asset type from JSON body")
    cat_create.add_argument("--body", required=True, help='JSON payload: {"capital_asset_type": {...}}')
    cat_create.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview creation without calling the API",
    )
    cat_create.set_defaults(func=handle_capital_asset_types_create)

    cat_update = cat_sub.add_parser("update", help="Update a capital asset type from JSON body")
    cat_update.add_argument("id", help="Capital asset type ID")
    cat_update.add_argument("--body", required=True, help='JSON payload: {"capital_asset_type": {...}}')
    cat_update.add_argument("--dry-run", action="store_true", help="Preview update without calling the API")
    cat_update.set_defaults(func=handle_capital_asset_types_update)

    cat_delete = cat_sub.add_parser("delete", help="Delete a capital asset type")
    cat_delete.add_argument("id", help="Capital asset type ID")
    cat_delete.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deletion without calling the API",
    )
    cat_delete.set_defaults(func=handle_capital_asset_types_delete)

    # Depreciation profiles (helper; no dedicated API endpoint)
    dep = subparsers.add_parser("depreciation-profiles", help="Helpers for depreciation_profile payloads")
    dep_sub = dep.add_subparsers(dest="action", required=True)

    dep_methods = dep_sub.add_parser("methods", help="List valid depreciation methods and required parameters")
    dep_methods.set_defaults(func=handle_depreciation_profiles_methods)

    dep_build = dep_sub.add_parser("build", help="Build a depreciation_profile payload for capital assets")
    dep_build.add_argument(
        "--method",
        required=True,
        choices=["straight_line", "reducing_balance", "no_depreciation"],
        help="Depreciation method",
    )
    dep_build.add_argument(
        "--frequency",
        choices=["monthly", "annually"],
        help="Posting frequency (optional; defaults to monthly if omitted)",
    )
    dep_build.add_argument(
        "--asset-life-years",
        type=int,
        help="Asset life in years (required for straight_line)",
    )
    dep_build.add_argument(
        "--annual-depreciation-percentage",
        type=int,
        help="Annual depreciation percentage 1-99 (required for reducing_balance)",
    )
    dep_build.set_defaults(func=handle_depreciation_profiles_build)

    # Users
    users = subparsers.add_parser("users", help="User operations")
    users_sub = users.add_subparsers(dest="action", required=True)

    users_list = users_sub.add_parser("list", help="List users")
    users_list.add_argument(
        "--view",
        choices=["all", "staff", "active_staff", "advisors", "active_advisors"],
        help="Filter users by view",
    )
    users_list.set_defaults(func=handle_users_list)

    users_get = users_sub.add_parser("get", help="Get a user by ID")
    users_get.add_argument("id", help="User ID")
    users_get.set_defaults(func=handle_users_get)

    users_me = users_sub.add_parser("me", help="Get the current user profile")
    users_me.set_defaults(func=handle_users_me)

    users_delete = users_sub.add_parser("delete", help="Delete a user")
    users_delete.add_argument("id", help="User ID")
    users_delete.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deletion without calling the API",
    )
    users_delete.set_defaults(func=handle_users_delete)

    users_perm = users_sub.add_parser("set-permission", help="Update a user's permission level")
    users_perm.add_argument("id", help="User ID")
    users_perm.add_argument(
        "--permission-level",
        required=True,
        type=int,
        choices=list(range(0, 9)),
        help="Permission level 0-8 (see FreeAgent docs)",
    )
    users_perm.add_argument("--dry-run", action="store_true", help="Preview update without calling the API")
    users_perm.set_defaults(func=handle_users_update_permission)

    users_perm_get = users_sub.add_parser("get-permission", help="Show a user's permission level")
    users_perm_get.add_argument("id", help="User ID")
    users_perm_get.set_defaults(func=handle_users_permission)

    users_hide = users_sub.add_parser("set-hidden", help="Hide or unhide a user")
    users_hide.add_argument("id", help="User ID")
    users_hide.add_argument(
        "--hidden",
        required=True,
        choices=["true", "false"],
        help="Set hidden flag (true|false)",
    )
    users_hide.add_argument("--dry-run", action="store_true", help="Preview update without calling the API")
    users_hide.set_defaults(
        func=lambda a, c, s: handle_users_set_hidden(
            argparse.Namespace(
                id=a.id,
                hidden=a.hidden == "true",
                dry_run=a.dry_run,
                format=getattr(a, "format", "json"),
            ),
            c,
            s,
        )
    )

    # Timeslips
    timeslips = subparsers.add_parser("timeslips", help="Timeslip operations")
    timeslips_sub = timeslips.add_subparsers(dest="action", required=True)

    timeslips_list = timeslips_sub.add_parser("list", help="List timeslips")
    timeslips_list.add_argument("--user", help="Filter by user URL")
    timeslips_list.add_argument("--project", help="Filter by project URL")
    timeslips_list.add_argument("--task", help="Filter by task URL")
    timeslips_list.add_argument("--from-date", help="Filter from date (YYYY-MM-DD)")
    timeslips_list.add_argument("--to-date", help="Filter to date (YYYY-MM-DD)")
    timeslips_list.add_argument(
        "--view",
        choices=["all", "unbilled", "billed"],
        help="Filter timeslips by billing state",
    )
    timeslips_list.set_defaults(func=handle_timeslips_list)

    timeslips_del = timeslips_sub.add_parser("delete", help="Delete a timeslip")
    timeslips_del.add_argument("id", help="Timeslip ID")
    timeslips_del.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deletion without calling the API",
    )
    timeslips_del.set_defaults(func=handle_timeslips_delete)

    # Final accounts reports
    fa = subparsers.add_parser("final-accounts", help="Final accounts reports")
    fa_sub = fa.add_subparsers(dest="action", required=True)

    fa_list = fa_sub.add_parser("list", help="List final accounts reports")
    fa_list.set_defaults(func=handle_final_accounts_list)

    fa_get = fa_sub.add_parser("get", help="Get a final accounts report by period end")
    fa_get.add_argument("period_ends_on", help="Period end date (YYYY-MM-DD)")
    fa_get.set_defaults(func=handle_final_accounts_get)

    fa_mark_filed = fa_sub.add_parser("mark-filed", help="Mark a final accounts report as filed")
    fa_mark_filed.add_argument("period_ends_on", help="Period end date (YYYY-MM-DD)")
    fa_mark_filed.set_defaults(func=handle_final_accounts_mark_as_filed)

    fa_mark_unfiled = fa_sub.add_parser("mark-unfiled", help="Mark a final accounts report as unfiled")
    fa_mark_unfiled.add_argument("period_ends_on", help="Period end date (YYYY-MM-DD)")
    fa_mark_unfiled.set_defaults(func=handle_final_accounts_mark_as_unfiled)

    # Projects
    projects = subparsers.add_parser("projects", help="Project operations")
    projects_sub = projects.add_subparsers(dest="action", required=True)

    projects_list = projects_sub.add_parser("list", help="List projects")
    projects_list.add_argument(
        "--view",
        choices=["active", "completed", "all"],
        help="Filter projects by status",
    )
    projects_list.add_argument("--updated-since", help="Filter by updated_since timestamp")
    projects_list.set_defaults(func=handle_projects_list)

    projects_get = projects_sub.add_parser("get", help="Get a project by ID")
    projects_get.add_argument("id", help="Project ID")
    projects_get.set_defaults(func=handle_projects_get)

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

    # Bank transaction explanations
    bte = subparsers.add_parser("bank-transaction-explanations", help="Bank transaction explanation operations")
    bte_sub = bte.add_subparsers(dest="action", required=True)

    bte_list = bte_sub.add_parser("list", help="List bank transaction explanations (requires bank account)")
    bte_list.add_argument(
        "--bank-account",
        required=True,
        help="Bank account URL to scope explanations",
    )
    bte_list.add_argument("--from-date", help="Filter from date (YYYY-MM-DD)")
    bte_list.add_argument("--to-date", help="Filter to date (YYYY-MM-DD)")
    bte_list.add_argument("--updated-since", help="Filter by updated_since timestamp")
    bte_list.add_argument(
        "--for-approval",
        action="store_true",
        help="Only show explanations marked for approval (marked_for_review=true)",
    )
    bte_list.set_defaults(func=handle_bank_transaction_explanations_list)

    bte_get = bte_sub.add_parser("get", help="Get a bank transaction explanation by ID")
    bte_get.add_argument("id", help="Explanation ID")
    bte_get.set_defaults(func=handle_bank_transaction_explanations_get)

    bte_create = bte_sub.add_parser("create", help="Create a bank transaction explanation from JSON body")
    bte_create.add_argument(
        "--body",
        required=True,
        help='JSON payload: {"bank_transaction_explanation": {...}}',
    )
    bte_create.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview creation without calling the API",
    )
    bte_create.set_defaults(func=handle_bank_transaction_explanations_create)

    bte_update = bte_sub.add_parser("update", help="Update a bank transaction explanation from JSON body")
    bte_update.add_argument("id", help="Explanation ID")
    bte_update.add_argument(
        "--body",
        required=True,
        help='JSON payload: {"bank_transaction_explanation": {...}}',
    )
    bte_update.add_argument("--dry-run", action="store_true", help="Preview update without calling the API")
    bte_update.set_defaults(func=handle_bank_transaction_explanations_update)

    bte_delete = bte_sub.add_parser("delete", help="Delete a bank transaction explanation")
    bte_delete.add_argument("id", help="Explanation ID")
    bte_delete.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deletion without calling the API",
    )
    bte_delete.set_defaults(func=handle_bank_transaction_explanations_delete)

    bte_approve = bte_sub.add_parser(
        "approve",
        help="Mark bank transaction explanations as approved (clears marked_for_review)",
    )
    bte_approve.add_argument("ids", nargs="+", help="Explanation IDs to approve")
    bte_approve.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview approval without calling the API",
    )
    bte_approve.set_defaults(func=handle_bank_transaction_explanations_approve)

    # Accounting transactions
    transactions = subparsers.add_parser("transactions", help="Accounting transactions")
    transactions_sub = transactions.add_subparsers(dest="action", required=True)

    transactions_list = transactions_sub.add_parser("list", help="List accounting transactions")
    transactions_list.add_argument("--from-date", help="Filter from date (YYYY-MM-DD)")
    transactions_list.add_argument("--to-date", help="Filter to date (YYYY-MM-DD)")
    transactions_list.add_argument("--nominal-code", help="Filter by nominal code")
    transactions_list.set_defaults(func=handle_transactions_list)

    transactions_get = transactions_sub.add_parser("get", help="Get a single accounting transaction")
    transactions_get.add_argument("id", help="Transaction ID")
    transactions_get.set_defaults(func=handle_transactions_get)

    # Journal sets
    journal_sets = subparsers.add_parser("journal-sets", help="Journal set operations")
    js_sub = journal_sets.add_subparsers(dest="action", required=True)

    js_list = js_sub.add_parser("list", help="List journal sets")
    js_list.add_argument("--from-date", help="Filter from date (YYYY-MM-DD)")
    js_list.add_argument("--to-date", help="Filter to date (YYYY-MM-DD)")
    js_list.add_argument("--updated-since", help="Filter by updated_since timestamp")
    js_list.add_argument("--tag", help="Filter by tag")
    js_list.set_defaults(func=handle_journal_sets_list)

    js_get = js_sub.add_parser("get", help="Get a journal set by ID")
    js_get.add_argument("id", help="Journal set ID")
    js_get.set_defaults(func=handle_journal_sets_get)

    js_opening = js_sub.add_parser("opening-balances", help="Get the opening balances journal set")
    js_opening.set_defaults(func=handle_journal_sets_opening_balances)

    js_create = js_sub.add_parser("create", help="Create a journal set from JSON body")
    js_create.add_argument("--body", required=True, help='JSON payload: {"journal_set": {...}}')
    js_create.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview creation without calling the API",
    )
    js_create.set_defaults(func=handle_journal_sets_create)

    js_update = js_sub.add_parser("update", help="Update a journal set from JSON body")
    js_update.add_argument("id", help="Journal set ID")
    js_update.add_argument("--body", required=True, help='JSON payload: {"journal_set": {...}}')
    js_update.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview update without calling the API",
    )
    js_update.set_defaults(func=handle_journal_sets_update)

    js_delete = js_sub.add_parser("delete", help="Delete a journal set")
    js_delete.add_argument("id", help="Journal set ID")
    js_delete.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deletion without calling the API",
    )
    js_delete.set_defaults(func=handle_journal_sets_delete)

    # Attachments
    attachments = subparsers.add_parser("attachments", help="Attachment operations")
    attachments_sub = attachments.add_subparsers(dest="action", required=True)

    attachments_list = attachments_sub.add_parser("list", help="List attachments")
    attachments_list.add_argument(
        "--attachable-type",
        help=("Filter by attachable type (e.g. Expense, BankTransactionExplanation)"),
    )
    attachments_list.add_argument("--attachable-id", help="Filter by attachable ID (resource ID)")
    attachments_list.set_defaults(func=handle_attachments_list)

    attachments_get = attachments_sub.add_parser("get", help="Get an attachment")
    attachments_get.add_argument("id", help="Attachment ID")
    attachments_get.set_defaults(func=handle_attachments_get)

    attachments_upload = attachments_sub.add_parser("upload", help="Upload a new attachment")
    attachments_upload.add_argument("--file", required=True, help="Path to file")
    attachments_upload.add_argument("--description", help="Optional description")
    attachments_upload.add_argument(
        "--attachable-type",
        help=("Attach to type (e.g. Expense, BankTransactionExplanation)"),
    )
    attachments_upload.add_argument("--attachable-id", help="Attach to resource ID")
    attachments_upload.add_argument(
        "--content-type",
        help="Override MIME type (default guessed from filename)",
    )
    attachments_upload.add_argument(
        "--file-name",
        help=("Override file name sent to FreeAgent " "(default: source file name)"),
    )
    attachments_upload.add_argument("--dry-run", action="store_true", help="Preview upload without calling the API")
    attachments_upload.set_defaults(func=handle_attachments_upload)

    attachments_delete = attachments_sub.add_parser("delete", help="Delete an attachment")
    attachments_delete.add_argument("id", help="Attachment ID")
    attachments_delete.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deletion without calling the API",
    )
    attachments_delete.set_defaults(func=handle_attachments_delete)

    # Bills
    bills = subparsers.add_parser("bills", help="Bill operations")
    bills_sub = bills.add_subparsers(dest="action", required=True)

    bills_list = bills_sub.add_parser("list", help="List bills")
    bills_list.add_argument("--view", help="View filter (open, overdue, etc.)")
    bills_list.add_argument("--from-date")
    bills_list.add_argument("--to-date")
    bills_list.add_argument("--updated-since")
    bills_list.add_argument("--nested-bill-items", action="store_true", help="Include nested bill items")
    bills_list.set_defaults(func=handle_bills_list)

    bills_list_all = bills_sub.add_parser("list-all", help="List all bills")
    bills_list_all.set_defaults(func=handle_bills_list_all)

    bills_get = bills_sub.add_parser("get", help="Get bill by ID")
    bills_get.add_argument("id", help="Bill ID")
    bills_get.set_defaults(func=handle_bills_get)

    bills_create = bills_sub.add_parser("create", help="Create a bill from JSON body")
    bills_create.add_argument("--body", required=True, help='JSON payload: {"bill": {...}}')
    bills_create.add_argument("--dry-run", action="store_true")
    bills_create.set_defaults(func=handle_bills_create)

    bills_update = bills_sub.add_parser("update", help="Update a bill from JSON body")
    bills_update.add_argument("id", help="Bill ID")
    bills_update.add_argument("--body", required=True, help='JSON payload: {"bill": {...}}')
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

    inv_list_all = inv_sub.add_parser("list-all", help="List all invoices")
    inv_list_all.set_defaults(func=handle_invoices_list_all)

    inv_get = inv_sub.add_parser("get", help="Get invoice by ID")
    inv_get.add_argument("id", help="Invoice ID")
    inv_get.set_defaults(func=handle_invoices_get)

    inv_create = inv_sub.add_parser("create", help="Create an invoice from JSON body")
    inv_create.add_argument("--body", required=True, help='JSON payload: {"invoice": {...}}')
    inv_create.add_argument("--dry-run", action="store_true")
    inv_create.set_defaults(func=handle_invoices_create)

    inv_update = inv_sub.add_parser("update", help="Update an invoice from JSON body")
    inv_update.add_argument("id", help="Invoice ID")
    inv_update.add_argument("--body", required=True, help='JSON payload: {"invoice": {...}}')
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
    rep_pl.add_argument("--from-date", help="Start date (YYYY-MM-DD); optional")
    rep_pl.add_argument("--to-date", help="End date (YYYY-MM-DD); optional")
    rep_pl.add_argument(
        "--accounting-period",
        help="Accounting period token (e.g. 2024/25); optional",
    )
    rep_pl.set_defaults(func=handle_reports_profit_loss)

    rep_bs = rep_sub.add_parser("balance-sheet", help="Balance sheet")
    rep_bs.add_argument("--as-at-date", help="Report date (YYYY-MM-DD)")
    rep_bs.set_defaults(func=handle_reports_balance_sheet)

    rep_tb = rep_sub.add_parser("trial-balance", help="Trial balance summary")
    rep_tb.add_argument("--from-date")
    rep_tb.add_argument("--to-date")
    rep_tb.set_defaults(func=handle_reports_trial_balance)

    # Cashflow
    cashflow = subparsers.add_parser("cashflow", help="Cashflow summary")
    cf_sub = cashflow.add_subparsers(dest="action", required=True)

    cf_sum = cf_sub.add_parser("summary", help="Cashflow summary for date range")
    cf_sum.add_argument("--from-date", required=True, help="Start date (YYYY-MM-DD)")
    cf_sum.add_argument("--to-date", required=True, help="End date (YYYY-MM-DD)")
    cf_sum.set_defaults(func=handle_cashflow_summary)

    # Notes
    notes = subparsers.add_parser("notes", help="Note operations")
    notes_sub = notes.add_subparsers(dest="action", required=True)

    notes_list = notes_sub.add_parser("list", help="List notes for a contact or project")
    note_scope = notes_list.add_mutually_exclusive_group(required=True)
    note_scope.add_argument("--contact", help="Contact URL")
    note_scope.add_argument("--project", help="Project URL")
    notes_list.set_defaults(func=handle_notes_list)

    notes_get = notes_sub.add_parser("get", help="Get a single note")
    notes_get.add_argument("id", help="Note ID")
    notes_get.set_defaults(func=handle_notes_get)

    notes_create = notes_sub.add_parser("create", help="Create a note for a contact or project")
    note_scope_create = notes_create.add_mutually_exclusive_group(required=True)
    note_scope_create.add_argument("--contact", help="Contact URL")
    note_scope_create.add_argument("--project", help="Project URL")
    notes_create.add_argument("--body", required=True, help='JSON payload: {"note": {"note": "..."}}')
    notes_create.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview creation without calling the API",
    )
    notes_create.set_defaults(func=handle_notes_create)

    notes_update = notes_sub.add_parser("update", help="Update a note")
    notes_update.add_argument("id", help="Note ID")
    notes_update.add_argument("--body", required=True, help='JSON payload: {"note": {"note": "..."}}')
    notes_update.add_argument("--dry-run", action="store_true", help="Preview update without calling the API")
    notes_update.set_defaults(func=handle_notes_update)

    notes_delete = notes_sub.add_parser("delete", help="Delete a note")
    notes_delete.add_argument("id", help="Note ID")
    notes_delete.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deletion without calling the API",
    )
    notes_delete.set_defaults(func=handle_notes_delete)

    # Sales tax
    sales_tax = subparsers.add_parser("sales-tax", help="Sales tax operations")
    st_sub = sales_tax.add_subparsers(dest="action", required=True)

    st_moss = st_sub.add_parser("moss-rates", help="List EC MOSS sales tax rates for a country/date")
    st_moss.add_argument("--country", required=True, help="EU country name (place_of_supply)")
    st_moss.add_argument("--date", required=True, help="Transaction date (YYYY-MM-DD)")
    st_moss.set_defaults(func=handle_sales_tax_moss_rates)

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    args = build_parser().parse_args(argv)
    env_path = Path(args.env_file)
    config, env_file_data, env_lookup = load_config(
        env_path,
        base_url=args.base_url,
        debug=args.debug,
        request_timeout=args.timeout,
    )
    store = TokenStore(env_path, env_file_data, env_lookup)

    # Adjust global defaults for pagination/format for handlers
    args.per_page = min(args.per_page, PAGE_MAX)

    args.func(args, config, store)


if __name__ == "__main__":
    main()
