from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from fastapi import UploadFile

from app.models import (
    WechatAttachment,
    WechatContact,
    WechatConversation,
    WechatMessage,
    new_id,
    now_iso,
)


class MockWechatStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "messages").mkdir(exist_ok=True)
        (self.root / "assets").mkdir(exist_ok=True)
        if not (self.root / "conversations.json").exists():
            self._write_json(self.root / "conversations.json", [self._default_conversation()])

    def _default_conversation(self) -> dict[str, Any]:
        conversation_id = "conv_demo"
        return {
            "id": conversation_id,
            "openclaw_conversation_id": f"mock_{conversation_id}",
            "contact_id": "contact_demo",
            "case_id": None,
            "status": "open",
            "auto_reply_source": "openclaw",
            "last_message_at": now_iso(),
            "unread_count": 0,
            "contact": {
                "id": "contact_demo",
                "openclaw_contact_id": "mock_contact_demo",
                "display_name": "演示客户",
                "remark": "演示会话",
                "avatar_url": None,
                "last_seen_at": now_iso(),
            },
        }

    def _read_json(self, path: Path) -> Any:
        if not path.exists():
            return []
        try:
            text = path.read_text(encoding="utf-8")
            if not text.strip():
                return []
            return json.loads(text)
        except (json.JSONDecodeError, OSError):
            return []

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _safe_filename(self, filename: str) -> str:
        name = Path(filename).name
        name = re.sub(r'[<>:"/\\|?*#%]', "_", name)
        if not name:
            name = "upload.bin"
        return name

    def _ensure_messages_file(self, conversation_id: str) -> Path:
        path = self.root / "messages" / f"{conversation_id}.json"
        if not path.exists():
            self._write_json(path, [])
        return path

    def list_conversations(self) -> list[dict[str, Any]]:
        conversations = self._read_json(self.root / "conversations.json")
        if not isinstance(conversations, list):
            return []
        return conversations

    def create_conversation(self, display_name: str, remark: str = "", avatar_url: str | None = None) -> dict[str, Any]:
        conversation_id = new_id("conv")
        contact_id = new_id("contact")
        conversation = {
            "id": conversation_id,
            "openclaw_conversation_id": f"mock_{conversation_id}",
            "contact_id": contact_id,
            "case_id": None,
            "status": "open",
            "auto_reply_source": "openclaw",
            "last_message_at": now_iso(),
            "unread_count": 0,
            "contact": {
                "id": contact_id,
                "openclaw_contact_id": f"mock_{contact_id}",
                "display_name": display_name,
                "remark": remark,
                "avatar_url": avatar_url,
                "last_seen_at": now_iso(),
            },
        }
        conversations = self.list_conversations()
        conversations.append(conversation)
        self._write_json(self.root / "conversations.json", conversations)
        self._ensure_messages_file(conversation_id)
        return conversation

    def update_conversation(self, conversation_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        conversations = self.list_conversations()
        for conversation in conversations:
            if conversation["id"] == conversation_id:
                for key, value in payload.items():
                    if key == "contact" and isinstance(value, dict):
                        contact = conversation.get("contact", {})
                        contact.update(value)
                        conversation["contact"] = contact
                    else:
                        conversation[key] = value
                if "contact" in conversation and isinstance(conversation["contact"], dict):
                    conversation["contact"]["last_seen_at"] = now_iso()
                self._write_json(self.root / "conversations.json", conversations)
                return conversation
        return None

    def delete_conversation(self, conversation_id: str) -> bool:
        conversations = self.list_conversations()
        new_conversations = [c for c in conversations if c["id"] != conversation_id]
        if len(new_conversations) == len(conversations):
            return False
        self._write_json(self.root / "conversations.json", new_conversations)
        messages_path = self.root / "messages" / f"{conversation_id}.json"
        if messages_path.exists():
            messages_path.unlink()
        return True

    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        path = self._ensure_messages_file(conversation_id)
        messages = self._read_json(path)
        if not isinstance(messages, list):
            return []
        return messages

    def append_message(
        self,
        conversation_id: str,
        sender: str,
        content: str,
        attachments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if sender not in {"wechat_user", "owner"}:
            direction = "internal"
        elif sender == "wechat_user":
            direction = "inbound"
        else:
            direction = "outbound"

        if sender == "wechat_user":
            status = "synced"
        elif sender == "owner":
            status = "sent_via_openclaw"
        else:
            status = "synced"

        attachment_list = attachments or []
        has_images = any(
            (a.get("mime_type") or "").startswith("image/") for a in attachment_list
        )
        has_files = any(
            not (a.get("mime_type") or "").startswith("image/") for a in attachment_list
        )

        if not attachment_list:
            msg_type = "text"
        elif has_images and has_files:
            msg_type = "mixed"
        elif has_images and (not content or not content.strip()):
            msg_type = "image"
        elif has_files and (not content or not content.strip()):
            msg_type = "file"
        elif has_images or has_files:
            msg_type = "mixed"
        else:
            msg_type = "file"

        message_id = new_id("msg")
        message = {
            "id": message_id,
            "conversation_id": conversation_id,
            "sender": sender,
            "direction": direction,
            "type": msg_type,
            "content": content or "",
            "attachments": attachment_list,
            "status": status,
            "openclaw_message_id": None,
            "created_at": now_iso(),
            "raw_payload": None,
        }

        messages = self.list_messages(conversation_id)
        messages.append(message)
        self._write_json(self.root / "messages" / f"{conversation_id}.json", messages)

        conversations = self.list_conversations()
        for conversation in conversations:
            if conversation["id"] == conversation_id:
                conversation["last_message_at"] = message["created_at"]
                break
        self._write_json(self.root / "conversations.json", conversations)

        return message

    def delete_message(self, conversation_id: str, message_id: str) -> bool:
        messages = self.list_messages(conversation_id)
        new_messages = [m for m in messages if m["id"] != message_id]
        if len(new_messages) == len(messages):
            return False
        self._write_json(self.root / "messages" / f"{conversation_id}.json", new_messages)
        return True

    async def save_upload(self, upload: UploadFile) -> dict[str, Any]:
        original_name = upload.filename or "upload.bin"
        safe_name = self._safe_filename(original_name)
        unique_prefix = f"asset_{uuid4().hex[:12]}_"
        saved_name = f"{unique_prefix}{safe_name}"
        content = await upload.read()
        file_path = self.root / "assets" / saved_name
        file_path.write_bytes(content)
        return {
            "name": original_name,
            "url": f"/mock-wechat-assets/{quote(saved_name)}",
            "mime_type": upload.content_type,
            "size": len(content),
        }

    def sync_to_json_store(self, store: Any) -> None:
        mock_conversations = self.list_conversations()
        existing_contacts = {c.get("id"): c for c in store.data.get("wechat_contacts", [])}
        existing_conversations = {c.get("id"): c for c in store.data.get("wechat_conversations", [])}
        existing_messages = {m.get("id"): m for m in store.data.get("wechat_messages", [])}

        for conv in mock_conversations:
            contact_data = conv.get("contact")
            if contact_data and contact_data.get("id"):
                existing_contacts[contact_data["id"]] = contact_data

            conversation_data = {
                "id": conv["id"],
                "openclaw_conversation_id": conv.get("openclaw_conversation_id", f"mock_{conv['id']}"),
                "contact_id": conv.get("contact_id", ""),
                "case_id": conv.get("case_id"),
                "status": conv.get("status", "open"),
                "auto_reply_source": conv.get("auto_reply_source", "openclaw"),
                "last_message_at": conv.get("last_message_at"),
                "unread_count": conv.get("unread_count", 0),
            }
            existing_conversations[conv["id"]] = conversation_data

            messages = self.list_messages(conv["id"])
            for msg in messages:
                existing_messages[msg["id"]] = msg

        store.data["wechat_contacts"] = list(existing_contacts.values())
        store.data["wechat_conversations"] = list(existing_conversations.values())
        store.data["wechat_messages"] = list(existing_messages.values())
        store.save()
