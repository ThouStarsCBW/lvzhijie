from __future__ import annotations

from app.gateway_rpc import (
    CONTROL_UI_CLIENT_ID,
    DEFAULT_GATEWAY_CLIENT_ID,
    GatewayConfig,
    _connect_params,
    _host_platform,
    _protocol_versions,
)


def test_gateway_connect_uses_allowed_device_client_id() -> None:
    params = _connect_params(GatewayConfig(url="ws://localhost:18789"), None)

    assert params["client"]["id"] == DEFAULT_GATEWAY_CLIENT_ID
    assert params["client"]["mode"] == "backend"
    assert "device" in params


def test_gateway_connect_control_ui_bypass_uses_control_client_id() -> None:
    params = _connect_params(
        GatewayConfig(url="ws://localhost:18789", disable_device_pairing=True),
        None,
    )

    assert params["client"]["id"] == CONTROL_UI_CLIENT_ID
    assert params["client"]["mode"] == "ui"
    assert "device" not in params


def test_gateway_connect_uses_configured_protocol_version() -> None:
    params = _connect_params(GatewayConfig(url="ws://localhost:18789", protocol_version=2), None)

    assert params["minProtocol"] == 2
    assert params["maxProtocol"] == 2


def test_gateway_protocol_auto_fallback_order() -> None:
    assert _protocol_versions(0) == [4, 3, 2, 1]
    assert _protocol_versions(4) == [4]
    assert _protocol_versions(1) == [1]


def test_gateway_host_platform_uses_openclaw_windows_name(monkeypatch) -> None:
    monkeypatch.setattr("app.gateway_rpc.platform.system", lambda: "Windows")

    assert _host_platform() == "win32"
