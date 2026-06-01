from __future__ import annotations

import asyncio
import json
import platform
import ssl
from dataclasses import dataclass
from time import time
from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse
from uuid import uuid4

import websockets
from websockets.exceptions import WebSocketException

from app.device_identity import (
    build_device_auth_payload,
    load_or_create_device_identity,
    public_key_raw_base64url_from_pem,
    sign_device_payload,
)

PROTOCOL_VERSION = 4
PROTOCOL_FALLBACKS = [4, 3, 2, 1]
OPERATOR_SCOPES = ["operator.read", "operator.admin", "operator.approvals", "operator.pairing"]
DEFAULT_GATEWAY_CLIENT_ID = "gateway-client"
DEFAULT_GATEWAY_CLIENT_MODE = "backend"
CONTROL_UI_CLIENT_ID = "openclaw-control-ui"
CONTROL_UI_CLIENT_MODE = "ui"


def _host_platform() -> str:
    # OpenClaw pins the gateway device metadata using Node's process.platform.
    # Python reports Windows as "windows", while Node/OpenClaw use "win32".
    value = platform.system().lower()
    if value == "windows":
        return "win32"
    return value


class OpenClawGatewayError(RuntimeError):
    pass


@dataclass(frozen=True)
class GatewayConfig:
    url: str
    token: str | None = None
    allow_insecure_tls: bool = False
    disable_device_pairing: bool = False
    protocol_version: int = 0


def _gateway_url(config: GatewayConfig) -> str:
    raw = config.url.strip()
    if not raw:
        raise OpenClawGatewayError("Gateway URL is not configured.")
    if not config.token:
        return raw
    parsed = urlparse(raw)
    return urlunparse(parsed._replace(query=urlencode({"token": config.token})))


def _ssl_context(config: GatewayConfig) -> ssl.SSLContext | None:
    if urlparse(config.url).scheme != "wss" or not config.allow_insecure_tls:
        return None
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def _origin(gateway_url: str) -> str | None:
    parsed = urlparse(gateway_url)
    if not parsed.hostname:
        return None
    scheme = "https" if parsed.scheme in {"wss", "https"} else "http"
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return f"{scheme}://{host}"


def _device_payload(config: GatewayConfig, nonce: str | None) -> dict[str, Any]:
    identity = load_or_create_device_identity()
    signed_at_ms = int(time() * 1000)
    client_id = CONTROL_UI_CLIENT_ID if config.disable_device_pairing else DEFAULT_GATEWAY_CLIENT_ID
    client_mode = CONTROL_UI_CLIENT_MODE if config.disable_device_pairing else DEFAULT_GATEWAY_CLIENT_MODE
    payload = build_device_auth_payload(
        device_id=identity.device_id,
        client_id=client_id,
        client_mode=client_mode,
        role="operator",
        scopes=OPERATOR_SCOPES,
        signed_at_ms=signed_at_ms,
        token=config.token,
        nonce=nonce,
    )
    data: dict[str, Any] = {
        "id": identity.device_id,
        "publicKey": public_key_raw_base64url_from_pem(identity.public_key_pem),
        "signature": sign_device_payload(identity.private_key_pem, payload),
        "signedAt": signed_at_ms,
    }
    if nonce:
        data["nonce"] = nonce
    return data


def _connect_params(config: GatewayConfig, nonce: str | None) -> dict[str, Any]:
    use_control_ui = config.disable_device_pairing
    protocol_version = config.protocol_version or PROTOCOL_VERSION
    params: dict[str, Any] = {
        "minProtocol": protocol_version,
        "maxProtocol": protocol_version,
        "role": "operator",
        "scopes": OPERATOR_SCOPES,
        "client": {
            "id": CONTROL_UI_CLIENT_ID if use_control_ui else DEFAULT_GATEWAY_CLIENT_ID,
            "version": "0.1.0",
            "platform": _host_platform(),
            "mode": CONTROL_UI_CLIENT_MODE if use_control_ui else DEFAULT_GATEWAY_CLIENT_MODE,
        },
    }
    if not use_control_ui:
        params["device"] = _device_payload(config, nonce)
    if config.token:
        params["auth"] = {"token": config.token}
    return params


async def _first_message(ws: websockets.ClientConnection) -> str | bytes | None:
    try:
        return await asyncio.wait_for(ws.recv(), timeout=2)
    except TimeoutError:
        return None


async def _await_response(ws: websockets.ClientConnection, request_id: str) -> object:
    while True:
        data = json.loads(await ws.recv())
        if data.get("type") == "res" and data.get("id") == request_id:
            if data.get("ok") is False:
                error = data.get("error", {})
                raise OpenClawGatewayError(str(error.get("message") or "Gateway error"))
            return data.get("payload")
        if data.get("id") == request_id:
            if data.get("error"):
                raise OpenClawGatewayError(str(data["error"].get("message") or "Gateway error"))
            return data.get("result")


async def _connect(ws: websockets.ClientConnection, config: GatewayConfig) -> None:
    first = await _first_message(ws)
    nonce: str | None = None
    if first:
        raw = first.decode("utf-8") if isinstance(first, bytes) else first
        data = json.loads(raw)
        payload = data.get("payload")
        if data.get("type") == "event" and data.get("event") == "connect.challenge" and isinstance(payload, dict):
            nonce = str(payload.get("nonce") or "") or None
    request_id = str(uuid4())
    await ws.send(
        json.dumps(
            {
                "type": "req",
                "id": request_id,
                "method": "connect",
                "params": _connect_params(config, nonce),
            }
        )
    )
    await _await_response(ws, request_id)


async def call_gateway(method: str, params: dict[str, Any] | None, config: GatewayConfig) -> object:
    versions = _protocol_versions(config.protocol_version)
    errors: list[str] = []
    for version in versions:
        attempt_config = GatewayConfig(
            url=config.url,
            token=config.token,
            allow_insecure_tls=config.allow_insecure_tls,
            disable_device_pairing=config.disable_device_pairing,
            protocol_version=version,
        )
        try:
            return await _call_gateway_with_timeout(method, params, attempt_config)
        except OpenClawGatewayError as exc:
            message = str(exc)
            errors.append(f"v{version}: {message}")
            if "protocol mismatch" not in message.lower() and config.protocol_version != 0:
                raise
            if "protocol mismatch" not in message.lower() and config.protocol_version == 0:
                raise
    raise OpenClawGatewayError("OpenClaw Gateway protocol mismatch. Tried " + "; ".join(errors))


async def _call_gateway_with_timeout(
    method: str,
    params: dict[str, Any] | None,
    config: GatewayConfig,
) -> object:
    try:
        return await asyncio.wait_for(_call_gateway(method, params, config), timeout=6)
    except TimeoutError as exc:
        raise OpenClawGatewayError("OpenClaw Gateway connection timed out after 6 seconds.") from exc


def _protocol_versions(configured: int) -> list[int]:
    if configured in {1, 2, 3, 4}:
        return [configured]
    return PROTOCOL_FALLBACKS


async def _call_gateway(method: str, params: dict[str, Any] | None, config: GatewayConfig) -> object:
    url = _gateway_url(config)
    kwargs: dict[str, Any] = {"ping_interval": None}
    context = _ssl_context(config)
    if context is not None:
        kwargs["ssl"] = context
    if config.disable_device_pairing:
        kwargs["origin"] = _origin(url)
    try:
        async with websockets.connect(url, **kwargs) as ws:
            await _connect(ws, config)
            request_id = str(uuid4())
            await ws.send(
                json.dumps(
                    {
                        "type": "req",
                        "id": request_id,
                        "method": method,
                        "params": params or {},
                    }
                )
            )
            return await _await_response(ws, request_id)
    except OpenClawGatewayError:
        raise
    except (TimeoutError, OSError, ValueError, WebSocketException) as exc:
        raise OpenClawGatewayError(str(exc)) from exc
