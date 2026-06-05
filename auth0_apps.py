#!/usr/bin/env python3
"""Manage Auth0 applications from the terminal.

This script uses Auth0 Management API v2 "clients" endpoints. Auth0 calls
dashboard applications "clients" at the API layer.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_SCOPES = "create:clients update:clients delete:clients read:clients"

APP_TYPE_API_VALUES = {
    "mtom": "non_interactive",
}


class Auth0ApiError(RuntimeError):
    """Raised when Auth0 returns an unsuccessful API response."""


def normalize_domain(domain: str) -> str:
    domain = domain.strip()
    if domain.startswith("https://"):
        domain = domain.removeprefix("https://")
    elif domain.startswith("http://"):
        domain = domain.removeprefix("http://")
    return domain.rstrip("/")


def load_json_arg(value: str | None) -> dict[str, Any]:
    if not value:
        return {}

    if value.startswith("@"):
        path = value[1:]
        with open(path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
    else:
        data = json.loads(value)

    if not isinstance(data, dict):
        raise ValueError("JSON payload must be an object.")
    return data


def add_csv_field(payload: dict[str, Any], key: str, csv_value: str | None) -> None:
    if csv_value is None:
        return
    payload[key] = [item.strip() for item in csv_value.split(",") if item.strip()]


def add_json_field(payload: dict[str, Any], key: str, value: str | None) -> None:
    if value is None:
        return
    parsed = json.loads(value)
    if not isinstance(parsed, (dict, list, str, int, float, bool)) and parsed is not None:
        raise ValueError(f"{key} must be valid JSON.")
    payload[key] = parsed


def request_json(
    method: str,
    url: str,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    request_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    if headers:
        request_headers.update(headers)

    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        headers=request_headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
            if not response_body:
                return None
            return json.loads(response_body)
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(details)
            details = json.dumps(parsed, indent=2, sort_keys=True)
        except json.JSONDecodeError:
            pass
        raise Auth0ApiError(f"{method} {url} failed with {exc.code}:\n{details}") from exc
    except urllib.error.URLError as exc:
        raise Auth0ApiError(f"{method} {url} failed: {exc.reason}") from exc


def get_management_token(args: argparse.Namespace) -> str:
    if args.token:
        return args.token

    env_token = os.getenv("AUTH0_MGMT_API_TOKEN")
    if env_token:
        return env_token

    client_id = args.client_id or os.getenv("AUTH0_CLIENT_ID")
    client_secret = args.client_secret or os.getenv("AUTH0_CLIENT_SECRET")
    domain = args.domain or os.getenv("AUTH0_DOMAIN")

    if not domain:
        raise ValueError("Provide --domain or set AUTH0_DOMAIN.")
    if not client_id:
        raise ValueError("Provide --client-id, set AUTH0_CLIENT_ID, or pass --token.")
    if not client_secret:
        client_secret = getpass.getpass("Auth0 client secret: ")

    domain = normalize_domain(domain)
    audience = f"https://{domain}/api/v2/"
    token_url = f"https://{domain}/oauth/token"
    token_payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "audience": audience,
    }

    result = request_json("POST", token_url, payload=token_payload)
    token = result.get("access_token") if isinstance(result, dict) else None
    if not token:
        raise Auth0ApiError("Auth0 token response did not include access_token.")
    return token


def build_client_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload = load_json_arg(args.json)
    app_type = APP_TYPE_API_VALUES.get(args.app_type, args.app_type)

    simple_fields = {
        "name": args.name,
        "description": args.description,
        "app_type": app_type,
        "token_endpoint_auth_method": args.token_endpoint_auth_method,
    }
    for key, value in simple_fields.items():
        if value is not None:
            payload[key] = value

    add_csv_field(payload, "callbacks", args.callbacks)
    add_csv_field(payload, "allowed_logout_urls", args.allowed_logout_urls)
    add_csv_field(payload, "web_origins", args.web_origins)
    add_csv_field(payload, "allowed_origins", args.allowed_origins)
    add_json_field(payload, "client_metadata", args.client_metadata)
    add_json_field(payload, "jwt_configuration", args.jwt_configuration)

    if not payload:
        raise ValueError("No application fields were supplied.")
    return payload


def management_base_url(domain: str) -> str:
    return f"https://{normalize_domain(domain)}/api/v2"


def print_result(result: Any) -> None:
    if result is None:
        print("OK")
    else:
        print(json.dumps(result, indent=2, sort_keys=True))


def create_application(args: argparse.Namespace) -> None:
    token = get_management_token(args)
    payload = build_client_payload(args)
    result = request_json(
        "POST",
        f"{management_base_url(args.domain)}/clients",
        token=token,
        payload=payload,
    )
    print_result(result)


def update_application(args: argparse.Namespace) -> None:
    token = get_management_token(args)
    payload = build_client_payload(args)
    client_id = urllib.parse.quote(args.application_id, safe="")
    result = request_json(
        "PATCH",
        f"{management_base_url(args.domain)}/clients/{client_id}",
        token=token,
        payload=payload,
    )
    print_result(result)


def delete_application(args: argparse.Namespace) -> None:
    if not args.yes:
        confirmation = input(
            f"Delete Auth0 application {args.application_id!r}? Type 'delete' to continue: "
        )
        if confirmation != "delete":
            print("Canceled.")
            return

    token = get_management_token(args)
    client_id = urllib.parse.quote(args.application_id, safe="")
    request_json(
        "DELETE",
        f"{management_base_url(args.domain)}/clients/{client_id}",
        token=token,
    )
    print(f"Deleted application {args.application_id}.")


def add_auth_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--domain",
        default=os.getenv("AUTH0_DOMAIN"),
        help="Auth0 tenant domain, e.g. dev-example.us.auth0.com. Defaults to AUTH0_DOMAIN.",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("AUTH0_MGMT_API_TOKEN"),
        help="Management API token. Defaults to AUTH0_MGMT_API_TOKEN.",
    )
    parser.add_argument(
        "--client-id",
        default=os.getenv("AUTH0_CLIENT_ID"),
        help="Machine-to-machine client ID used to request a token.",
    )
    parser.add_argument(
        "--client-secret",
        default=os.getenv("AUTH0_CLIENT_SECRET"),
        help="Machine-to-machine client secret used to request a token.",
    )


def add_application_fields(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", help="Raw JSON object, or @path/to/payload.json.")
    parser.add_argument("--name", help="Application name.")
    parser.add_argument("--description", help="Application description.")
    parser.add_argument(
        "--app-type",
        choices=["native", "spa", "regular_web", "mtom"],
        help="Application type. Use mtom for machine-to-machine applications.",
    )
    parser.add_argument(
        "--callbacks",
        help="Comma-separated callback URLs.",
    )
    parser.add_argument(
        "--allowed-logout-urls",
        help="Comma-separated logout URLs.",
    )
    parser.add_argument(
        "--web-origins",
        help="Comma-separated web origins.",
    )
    parser.add_argument(
        "--allowed-origins",
        help="Comma-separated CORS origins.",
    )
    parser.add_argument(
        "--token-endpoint-auth-method",
        choices=["none", "client_secret_post", "client_secret_basic"],
        help="Client authentication method for the token endpoint.",
    )
    parser.add_argument(
        "--client-metadata",
        help='JSON object for client_metadata, e.g. \'{"owner":"platform"}\'.',
    )
    parser.add_argument(
        "--jwt-configuration",
        help='JSON object for jwt_configuration, e.g. \'{"alg":"RS256"}\'.',
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create, update, and delete Auth0 applications via the Management API.",
    )
    add_auth_args(parser)

    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create an Auth0 application.")
    add_application_fields(create_parser)
    create_parser.set_defaults(func=create_application)

    update_parser = subparsers.add_parser("update", help="Update an Auth0 application.")
    update_parser.add_argument("application_id", help="Auth0 client/application ID.")
    add_application_fields(update_parser)
    update_parser.set_defaults(func=update_application)

    delete_parser = subparsers.add_parser("delete", help="Delete an Auth0 application.")
    delete_parser.add_argument("application_id", help="Auth0 client/application ID.")
    delete_parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip the delete confirmation prompt.",
    )
    delete_parser.set_defaults(func=delete_application)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if not args.domain:
            raise ValueError("Provide --domain or set AUTH0_DOMAIN.")
        args.func(args)
    except (Auth0ApiError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCanceled.", file=sys.stderr)
        return 130

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
