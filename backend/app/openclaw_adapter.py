from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.gateway_rpc import GatewayConfig, OpenClawGatewayError, call_gateway
from app.models import OpenClawConnection, OpenClawStatus, WechatMessage, new_id, now_iso


class OpenClawWechatAdapter:
    """Boundary adapter: OpenClaw is used only as the WeChat transport."""

    def __init__(self, connection: OpenClawConnection) -> None:
        self.connection = connection

    async def get_status(self) -> OpenClawStatus:
        if self.connection.transport_mode == "mock":
            return OpenClawStatus(
                online=True,
                message="Mock 微信通道已启用，未连接真实 OpenClaw。",
                checked_at=now_iso(),
                transport_mode=self.connection.transport_mode,
                sessions_count=1,
            )
        try:
            sessions = await self.list_sessions()
            return OpenClawStatus(
                online=True,
                message="已连接 OpenClaw Gateway，可读取会话并发送消息。",
                checked_at=now_iso(),
                transport_mode=self.connection.transport_mode,
                sessions_count=len(sessions),
            )
        except OpenClawGatewayError as exc:
            return OpenClawStatus(
                online=False,
                message="OpenClaw Gateway 暂不可用。",
                checked_at=now_iso(),
                transport_mode=self.connection.transport_mode,
                error=str(exc),
            )

    async def list_sessions(self) -> list[dict[str, Any]]:
        payload = await self._call(self.connection.list_method, {})
        if isinstance(payload, dict):
            raw_items = (
                payload.get("sessions")
                or payload.get("items")
                or payload.get("conversations")
                or []
            )
        else:
            raw_items = payload
        if not isinstance(raw_items, list):
            return []
        sessions = [item for item in raw_items if isinstance(item, dict)]
        filter_text = self.connection.wechat_session_filter.strip().lower()
        if filter_text:
            sessions = [
                item
                for item in sessions
                if filter_text in self.session_key(item).lower()
                or filter_text in self.session_label(item).lower()
            ]
        return sessions

    async def get_session_history(self, session_key: str) -> list[dict[str, Any]]:
        payload = await self._call(
            self.connection.history_method,
            {
                "sessionKey": session_key,
                "key": session_key,
                "limit": self.connection.history_limit,
            },
        )
        if isinstance(payload, dict):
            raw_items = payload.get("messages") or payload.get("history") or payload.get("items") or []
        else:
            raw_items = payload
        if not isinstance(raw_items, list):
            return []
        return [item for item in raw_items if isinstance(item, dict)]

    async def send_wechat_message(self, *, conversation_id: str, content: str) -> WechatMessage:
        if self.connection.transport_mode == "mock":
            return self._mock_sent_message(conversation_id=conversation_id, content=content)
        try:
            payload = await self._call(
                self.connection.send_method,
                {
                    "sessionKey": conversation_id,
                    "key": conversation_id,
                    "message": content,
                    "content": content,
                    "deliver": True,
                    "idempotencyKey": new_id("idem"),
                },
            )
            return WechatMessage(
                conversation_id=conversation_id,
                sender="owner",
                direction="outbound",
                content=content,
                status="sent_via_openclaw",
                openclaw_message_id=self._openclaw_message_id(payload),
            )
        except OpenClawGatewayError as exc:
            return WechatMessage(
                conversation_id=conversation_id,
                sender="owner",
                direction="outbound",
                content=content,
                status="failed",
                raw_payload={"error": str(exc), "transport": "openclaw_gateway_rpc"},
            )

    def normalize_history_message(self, raw: dict[str, Any], *, conversation_id: str) -> WechatMessage:
        role = str(raw.get("role") or raw.get("sender") or raw.get("from") or "").lower()
        direction = "outbound" if role in {"assistant", "agent", "bot", "openclaw"} else "inbound"
        sender = "openclaw_auto" if direction == "outbound" else "wechat_user"
        return WechatMessage(
            conversation_id=conversation_id,
            sender=sender,
            direction=direction,
            content=self._message_content(raw),
            status="openclaw_auto_replied" if sender == "openclaw_auto" else "synced",
            openclaw_message_id=self._message_id(raw),
            created_at=self._message_time(raw),
            raw_payload=raw,
        )

    def session_key(self, raw: dict[str, Any]) -> str:
        return str(
            raw.get("key")
            or raw.get("sessionKey")
            or raw.get("id")
            or raw.get("conversationId")
            or raw.get("name")
            or new_id("ocsession")
        )

    def session_label(self, raw: dict[str, Any]) -> str:
        return str(
            raw.get("label")
            or raw.get("title")
            or raw.get("name")
            or raw.get("displayName")
            or raw.get("key")
            or "微信会话"
        )

    async def _call(self, method: str, params: dict[str, Any]) -> object:
        return await call_gateway(
            method,
            params,
            GatewayConfig(
                url=self.connection.gateway_url,
                token=self.connection.gateway_token,
                allow_insecure_tls=self.connection.allow_insecure_tls,
                disable_device_pairing=self.connection.disable_device_pairing,
                protocol_version=self.connection.gateway_protocol_version,
            ),
        )

    @staticmethod
    def _message_content(raw: dict[str, Any]) -> str:
        value = raw.get("content") or raw.get("message") or raw.get("text")
        if isinstance(value, list):
            return "\n".join(str(item) for item in value)
        if isinstance(value, dict):
            return str(value.get("text") or value.get("content") or value)
        if value is None:
            parts = raw.get("parts")
            if isinstance(parts, list):
                return "\n".join(
                    str(part.get("text") if isinstance(part, dict) else part) for part in parts
                )
            return ""
        return str(value)

    @staticmethod
    def _message_id(raw: dict[str, Any]) -> str | None:
        value = raw.get("id") or raw.get("messageId") or raw.get("uuid")
        return str(value) if value else None

    @staticmethod
    def _message_time(raw: dict[str, Any]) -> str:
        value = raw.get("createdAt") or raw.get("created_at") or raw.get("timestamp") or raw.get("time")
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, (int, float)):
            timestamp = value / 1000 if value > 10_000_000_000 else value
            return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
        return now_iso()

    @staticmethod
    def _openclaw_message_id(payload: object) -> str | None:
        if isinstance(payload, dict):
            value = payload.get("id") or payload.get("messageId") or payload.get("requestId")
            return str(value) if value else None
        return None

    @staticmethod
    def _mock_sent_message(*, conversation_id: str, content: str) -> WechatMessage:
        return WechatMessage(
            id=new_id("msg"),
            conversation_id=conversation_id,
            sender="owner",
            direction="outbound",
            content=content,
            status="sent_via_openclaw",
            openclaw_message_id=new_id("ocmsg"),
        )
