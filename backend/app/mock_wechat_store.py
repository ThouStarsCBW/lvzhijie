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
            conversations = [self._default_conversation(), *self._family_sample_conversations()]
            self._write_json(self.root / "conversations.json", conversations)
            for conversation in conversations:
                self._ensure_messages_file(conversation["id"])
            for conversation_id, messages in self._family_sample_messages().items():
                self._write_json(self.root / "messages" / f"{conversation_id}.json", messages)
        else:
            self._ensure_family_samples()

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

    def _family_sample_conversations(self) -> list[dict[str, Any]]:
        samples = [
            ("225", "江家属", "校园防卫刑事咨询"),
            ("269", "刘家属", "交通事故刑事责任咨询"),
            ("272", "艾家属", "危险驾驶做局咨询"),
        ]
        conversations = []
        for suffix, display_name, remark in samples:
            conversation_id = f"conv_family_{suffix}"
            contact_id = f"contact_family_{suffix}"
            conversations.append(
                {
                    "id": conversation_id,
                    "openclaw_conversation_id": f"mock_{conversation_id}",
                    "contact_id": contact_id,
                    "case_id": f"case_family_{suffix}",
                    "status": "open",
                    "auto_reply_source": "openclaw",
                    "last_message_at": now_iso(),
                    "unread_count": 0,
                    "contact": {
                        "id": contact_id,
                        "openclaw_contact_id": f"mock_{contact_id}",
                        "display_name": display_name,
                        "remark": remark,
                        "avatar_url": None,
                        "last_seen_at": now_iso(),
                    },
                }
            )
        return conversations

    def _family_sample_messages(self) -> dict[str, list[dict[str, Any]]]:
        samples = {
            "225": [
                (
                    "wechat_user",
                    "inbound",
                    "您好，我是江家属。孩子在学校被十几名同学围住殴打，情急下用随身小折刀反击，现在担心会不会按故意伤害处理。",
                ),
                (
                    "openclaw_auto",
                    "outbound",
                    "我先帮您把关键事实梳理清楚。孩子当时是否被迫到现场、对方人数、受伤情况和警方程序到哪一步了？",
                ),
                (
                    "wechat_user",
                    "inbound",
                    "孩子说上午已经被拉扯和踢打，中午又被带到厕所。对方大约十五人，有人勒住脖子把他摔倒，随后多人一起踢打。",
                ),
                (
                    "wechat_user",
                    "inbound",
                    "孩子手里的折刀是同学平时开药瓶用的小工具，不是管制刀具。对方暂时散开后，又有人从背后打他，他才转身反击。",
                ),
                (
                    "owner",
                    "outbound",
                    "先重点保留被围堵、倒地挨打、对方人数、刀具来源、伤情鉴定、老师处理记录和在场同学证言。",
                ),
            ],
            "269": [
                (
                    "wechat_user",
                    "inbound",
                    "我是刘家属。家里人骑无号牌电动三轮和一辆摩托发生剐蹭，对方乘车人后来抢救无效。交警因为他离开现场认定全责，现在被追究交通肇事。",
                ),
                (
                    "wechat_user",
                    "inbound",
                    "对方摩托超车时对面来了卡车，紧急变向才碰到三轮。我们家人确实没证、车辆没登记、没戴头盔，事故后短暂停留又离开。",
                ),
                (
                    "openclaw_auto",
                    "outbound",
                    "需要区分行政事故责任和刑事责任。请补充事故认定书中事故原因分析、责任结论、证人证言和离开现场是否导致损害扩大。",
                ),
                (
                    "wechat_user",
                    "inbound",
                    "认定书原因部分写对方超车、无证、无牌、未戴头盔是主要原因，我们这边是次要原因，但责任结论又写因为离开现场承担全责。",
                ),
                (
                    "owner",
                    "outbound",
                    "这个样例重点在刑法因果关系。请先把事故原因部分、责任认定部分、现场证人材料和救治时间线整理出来。",
                ),
            ],
            "272": [
                (
                    "wechat_user",
                    "inbound",
                    "我是艾家属。家里人酒后在高速上开车被查，血检超过醉驾标准。后来发现是别人为了换取从宽处理故意做局，让他喝酒再引导上高速并报警。",
                ),
                (
                    "openclaw_auto",
                    "outbound",
                    "先确认醉驾事实、是否被诱导、哪些人安排聚餐和车辆、是否有聊天记录、转账记录或报警时间线。",
                ),
                (
                    "wechat_user",
                    "inbound",
                    "对方有人安排吃饭、陪酒，还说会叫代驾，后来又说换地方玩。家里人本来想住下，对方又说跟车走高速没事。",
                ),
                (
                    "wechat_user",
                    "inbound",
                    "我们想问这种情况下家里人会怎么处理，做局的人是不是也构成危险驾驶共犯。",
                ),
                (
                    "owner",
                    "outbound",
                    "醉驾事实本身仍有刑事风险，但诱导者如果反复欺骗、怂恿并安排路线车辆，可能承担更重的共犯责任。",
                ),
            ],
        }
        result: dict[str, list[dict[str, Any]]] = {}
        for suffix, rows in samples.items():
            conversation_id = f"conv_family_{suffix}"
            result[conversation_id] = []
            for index, (sender, direction, content) in enumerate(rows, start=1):
                status = "synced"
                if sender == "openclaw_auto":
                    status = "openclaw_auto_replied"
                elif sender == "owner":
                    status = "sent_via_openclaw"
                result[conversation_id].append(
                    {
                        "id": f"msg_family_{suffix}_{index}",
                        "conversation_id": conversation_id,
                        "sender": sender,
                        "direction": direction,
                        "type": "text",
                        "content": content,
                        "attachments": [],
                        "status": status,
                        "source": "mock",
                        "openclaw_message_id": None,
                        "created_at": now_iso(),
                        "raw_payload": None,
                    }
                )
        return result

    def _ensure_family_samples(self) -> None:
        conversations = self.list_conversations()
        conversation_ids = {conversation.get("id") for conversation in conversations}
        changed = False
        for conversation in self._family_sample_conversations():
            if conversation["id"] not in conversation_ids:
                conversations.append(conversation)
                conversation_ids.add(conversation["id"])
                changed = True
        if changed:
            self._write_json(self.root / "conversations.json", conversations)

        for conversation_id, messages in self._family_sample_messages().items():
            messages_path = self.root / "messages" / f"{conversation_id}.json"
            if not messages_path.exists():
                self._write_json(messages_path, messages)

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
        source: str | None = None,
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
            "source": source,
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
