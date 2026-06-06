#!/usr/bin/env python3
"""Create an AdsPower profile with a random SOCKS5 proxy and open ChatGPT."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import error, request
from urllib.parse import quote, unquote, urlparse


DEFAULT_BASE_URL = "http://localhost:50325"
DEFAULT_TARGET_URL = "https://www.chatgpt.com"
DEFAULT_PROXY_FILE = "proxies.txt"


class AdsPowerError(RuntimeError):
    pass


def request_json(
    method: str,
    base_url: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    timeout: float = 20,
) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    body = None
    headers = {"Accept": "application/json"}

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = request.Request(url, data=body, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except error.URLError as exc:
        raise AdsPowerError(f"Cannot call AdsPower API at {url}: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AdsPowerError(f"AdsPower API returned non-JSON response: {raw}") from exc

    if data.get("code") != 0:
        if "api-key" in str(data.get("msg", "")).lower():
            raise AdsPowerError(
                "AdsPower requires an API key. Run with "
                'ADSPOWER_API_KEY="your_api_key" ./adspower_open_chatgpt.py'
            )
        raise AdsPowerError(f"AdsPower API failed at {path}: {data}")

    return data


def check_connection(base_url: str, api_key: Optional[str]) -> None:
    request_json("GET", base_url, "/status", api_key=api_key)


def normalize_proxy_line(line: str) -> str:
    value = line.strip()
    if not value:
        raise AdsPowerError("Proxy line is empty")

    parsed = urlparse(value if "://" in value else f"socks5://{value}")
    try:
        parsed_port = parsed.port
    except ValueError:
        parsed_port = None
    if parsed.hostname and parsed_port:
        host = parsed.hostname
        port = str(parsed_port)
        username = unquote(parsed.username or "")
        password = unquote(parsed.password or "")
        if username and password:
            return f"{host}:{port}:{username}:{password}"

    value = value.split("://", 1)[-1]
    if "@" in value:
        auth, server = value.rsplit("@", 1)
        auth_parts = auth.split(":", 1)
        server_parts = server.split(":", 1)
        if len(auth_parts) == 2 and len(server_parts) == 2:
            username, password = auth_parts
            host, port = server_parts
            if host and port and username and password:
                return f"{host}:{port}:{username}:{password}"

    parts = value.split(":", 3)
    if len(parts) != 4:
        raise AdsPowerError(
            "Proxy lines must use host:port:username:password format, "
            "or socks5://username:password@host:port format, "
            f"but got: {line.strip()}"
        )

    host, port, username, password = parts
    if not host or not port or not username or not password:
        raise AdsPowerError(f"Proxy line has an empty field: {line.strip()}")
    return f"{host}:{port}:{username}:{password}"


def parse_proxy_line(line: str) -> Dict[str, str]:
    host, port, username, password = normalize_proxy_line(line).split(":", 3)
    return {
        "proxy_soft": "other",
        "proxy_type": "socks5",
        "proxy_host": host,
        "proxy_port": port,
        "proxy_user": username,
        "proxy_password": password,
    }


def load_proxies(proxy_file: str) -> List[Dict[str, str]]:
    path = Path(proxy_file)
    if not path.exists():
        return []

    proxies = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        proxies.append(parse_proxy_line(line))

    if not proxies:
        raise AdsPowerError(f"Proxy file exists but has no usable proxies: {proxy_file}")
    return proxies


def create_profile(
    base_url: str,
    api_key: Optional[str],
    group_id: str,
    target_url: str,
    name: Optional[str],
    proxy_config: Optional[Dict[str, str]],
    account_email: Optional[str] = None,
) -> str:
    profile_name = name or f"ChatGPT Auto {datetime.now().strftime('%Y%m%d-%H%M%S')}"
    payload = {
        "name": profile_name,
        "group_id": group_id,
        "platform": "chatgpt.com",
        "tabs": [target_url],
        "username": "",
        "remark": f"email: {account_email}" if account_email else "",
        "fingerprint_config": {
            "automatic_timezone": "1",
            "language_switch": "1",
            "page_language_switch": "1",
            "webrtc": "disabled",
            "location": "ask",
            "screen_resolution": "none",
            "fonts": ["all"],
            "canvas": "1",
            "webgl_image": "1",
            "webgl": "3",
            "audio": "1",
            "flash": "block",
            "random_ua": {
                "ua_browser": ["chrome"],
                "ua_system_version": ["Mac OS X"],
            },
            "browser_kernel_config": {
                "version": "ua_auto",
                "type": "chrome",
            },
        },
    }

    if proxy_config:
        payload["user_proxy_config"] = proxy_config
    else:
        payload["proxyid"] = "random"

    data = request_json("POST", base_url, "/api/v2/browser-profile/create", payload, api_key)
    profile_id = data.get("data", {}).get("profile_id")
    if not profile_id:
        raise AdsPowerError(f"Created profile but no profile_id was returned: {data}")
    return profile_id


def open_profile(base_url: str, api_key: Optional[str], profile_id: str) -> Dict[str, Any]:
    payload = {
        "profile_id": profile_id,
        "headless": "0",
        "last_opened_tabs": "0",
        "proxy_detection": "0",
        "cdp_mask": "0",
    }
    return request_json("POST", base_url, "/api/v2/browser-profile/start", payload, api_key)


def open_url_by_debug_port(debug_port: Optional[str], target_url: str) -> bool:
    if not debug_port:
        return False

    encoded_url = quote(target_url, safe="")
    endpoints = [
        ("PUT", f"http://127.0.0.1:{debug_port}/json/new?{encoded_url}"),
        ("GET", f"http://127.0.0.1:{debug_port}/json/new?{encoded_url}"),
    ]
    for method, url in endpoints:
        req = request.Request(url, method=method)
        try:
            with request.urlopen(req, timeout=8) as resp:
                raw = resp.read().decode("utf-8")
            target = json.loads(raw) if raw else {}
            target_id = target.get("id")
            if target_id:
                activate_url = f"http://127.0.0.1:{debug_port}/json/activate/{target_id}"
                with request.urlopen(activate_url, timeout=5) as resp:
                    resp.read()
            return True
        except (error.URLError, json.JSONDecodeError):
            continue
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a new AdsPower browser profile, choose a proxy randomly, open it, and visit ChatGPT."
    )
    parser.add_argument("--base-url", default=os.getenv("ADSPOWER_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--api-key", default=os.getenv("ADSPOWER_API_KEY"))
    parser.add_argument("--group-id", default=os.getenv("ADSPOWER_GROUP_ID", "0"))
    parser.add_argument("--url", default=os.getenv("ADSPOWER_TARGET_URL", DEFAULT_TARGET_URL))
    parser.add_argument("--name", default=os.getenv("ADSPOWER_PROFILE_NAME"))
    parser.add_argument(
        "--proxy-file",
        default=os.getenv("ADSPOWER_PROXY_FILE", DEFAULT_PROXY_FILE),
        help=(
            "Proxy list file. Each line uses host:port:username:password. "
            "If the file is missing, AdsPower saved-proxy random mode is used."
        ),
    )
    args = parser.parse_args()

    try:
        check_connection(args.base_url, args.api_key)
        proxies = load_proxies(args.proxy_file)
        proxy_config = random.choice(proxies) if proxies else None
        profile_id = create_profile(
            base_url=args.base_url,
            api_key=args.api_key,
            group_id=args.group_id,
            target_url=args.url,
            name=args.name,
            proxy_config=proxy_config,
        )

        # AdsPower rate-limits profile operations; a tiny pause keeps the run calm.
        time.sleep(1.1)
        started = open_profile(args.base_url, args.api_key, profile_id)
        debug_port = str(started.get("data", {}).get("debug_port") or "")
        navigated = open_url_by_debug_port(debug_port, args.url)
    except AdsPowerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Created profile: {profile_id}")
    print(f"Opened URL: {args.url}")
    if proxy_config:
        print(
            "Proxy: "
            f"{proxy_config['proxy_type']}://"
            f"{proxy_config['proxy_host']}:{proxy_config['proxy_port']}"
        )
    if debug_port:
        print(f"Debug port: {debug_port}")
    if not navigated:
        print("Warning: browser opened, but DevTools URL navigation did not confirm.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
