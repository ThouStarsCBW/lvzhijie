from __future__ import annotations

from io import BytesIO
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
import pytest

import app.main as main
from app.mock_wechat_store import MockWechatStore
from app.models import OpenClawConnection
from app.store import JsonStore


@pytest.fixture()
def client(tmp_path) -> TestClient:
    main.store = JsonStore(tmp_path / "store.json")
    main.mock_wechat = MockWechatStore(tmp_path / "mock_wechat")
    # Replace the static mount for assets so it points to tmp_path
    main.app.routes[:] = [
        r for r in main.app.routes
        if not (getattr(r, "path", None) == "/mock-wechat-assets")
    ]
    main.app.mount(
        "/mock-wechat-assets",
        StaticFiles(directory=tmp_path / "mock_wechat" / "assets"),
        name="mock-wechat-assets-test",
    )
    return TestClient(main.app)


def test_list_conversations_has_default_demo(client: TestClient) -> None:
    response = client.get("/api/mock-wechat/conversations")
    assert response.status_code == 200
    conversations = response.json()
    assert len(conversations) >= 1
    demo = next(c for c in conversations if c["id"] == "conv_demo")
    assert demo["contact"]["display_name"] == "演示客户"


def test_create_conversation(client: TestClient) -> None:
    response = client.post(
        "/api/mock-wechat/conversations",
        json={"display_name": "新客户", "remark": "测试备注"},
    )
    assert response.status_code == 200
    conv = response.json()
    assert conv["contact"]["display_name"] == "新客户"
    assert conv["contact"]["remark"] == "测试备注"
    assert conv["id"].startswith("conv_")
    # Verify it appears in list
    conversations = client.get("/api/mock-wechat/conversations").json()
    assert any(c["id"] == conv["id"] for c in conversations)


def test_update_conversation(client: TestClient) -> None:
    # Create a conversation first
    created = client.post(
        "/api/mock-wechat/conversations",
        json={"display_name": "待更新", "remark": "旧备注"},
    ).json()
    conv_id = created["id"]
    
    # Update it
    response = client.put(
        f"/api/mock-wechat/conversations/{conv_id}",
        json={"display_name": "已更新", "remark": "新备注", "unread_count": 5},
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["contact"]["display_name"] == "已更新"
    assert updated["contact"]["remark"] == "新备注"
    assert updated["unread_count"] == 5


def test_delete_conversation(client: TestClient) -> None:
    # Create a conversation
    created = client.post(
        "/api/mock-wechat/conversations",
        json={"display_name": "待删除"},
    ).json()
    conv_id = created["id"]
    
    # Delete it
    response = client.delete(f"/api/mock-wechat/conversations/{conv_id}")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    
    # Verify it's gone
    conversations = client.get("/api/mock-wechat/conversations").json()
    assert not any(c["id"] == conv_id for c in conversations)


def test_list_messages_empty_for_new_conversation(client: TestClient) -> None:
    # Create a conversation
    conv = client.post(
        "/api/mock-wechat/conversations",
        json={"display_name": "空消息"},
    ).json()
    
    # List messages
    response = client.get(f"/api/mock-wechat/conversations/{conv['id']}/messages")
    assert response.status_code == 200
    assert response.json() == []


def test_append_text_message(client: TestClient) -> None:
    # Use default demo conversation
    conv_id = "conv_demo"
    
    # Send a text message
    response = client.post(
        f"/api/mock-wechat/conversations/{conv_id}/messages",
        data={"sender": "wechat_user", "content": "你好，我想咨询法律问题"},
    )
    assert response.status_code == 200
    msg = response.json()
    assert msg["content"] == "你好，我想咨询法律问题"
    assert msg["sender"] == "wechat_user"
    assert msg["direction"] == "inbound"
    assert msg["type"] == "text"
    assert msg["status"] == "synced"
    
    # Verify it appears in list
    messages = client.get(f"/api/mock-wechat/conversations/{conv_id}/messages").json()
    assert len(messages) == 1
    assert messages[0]["id"] == msg["id"]


def test_append_message_with_file_attachment(client: TestClient) -> None:
    conv_id = "conv_demo"
    
    # Create a file-like object
    file_content = b"PDF content here"
    files = {"files": ("test.pdf", BytesIO(file_content), "application/pdf")}
    
    response = client.post(
        f"/api/mock-wechat/conversations/{conv_id}/messages",
        data={"sender": "owner", "content": "请查看合同"},
        files=files,
    )
    assert response.status_code == 200
    msg = response.json()
    assert msg["content"] == "请查看合同"
    assert msg["sender"] == "owner"
    assert msg["direction"] == "outbound"
    assert msg["type"] == "mixed"  # text + file
    assert len(msg["attachments"]) == 1
    att = msg["attachments"][0]
    assert att["name"] == "test.pdf"
    assert att["mime_type"] == "application/pdf"
    assert att["size"] == len(file_content)
    assert att["url"].startswith("/mock-wechat-assets/")


def test_append_image_only_message(client: TestClient) -> None:
    conv_id = "conv_demo"
    
    # Create an image file
    image_content = b"PNG image data"
    files = {"files": ("photo.png", BytesIO(image_content), "image/png")}
    
    response = client.post(
        f"/api/mock-wechat/conversations/{conv_id}/messages",
        data={"sender": "wechat_user", "content": ""},
        files=files,
    )
    assert response.status_code == 200
    msg = response.json()
    assert msg["content"] == ""
    assert msg["type"] == "image"
    assert len(msg["attachments"]) == 1
    assert msg["attachments"][0]["mime_type"] == "image/png"


def test_delete_message(client: TestClient) -> None:
    conv_id = "conv_demo"
    
    # Add a message
    msg = client.post(
        f"/api/mock-wechat/conversations/{conv_id}/messages",
        data={"sender": "wechat_user", "content": "待删除消息"},
    ).json()
    msg_id = msg["id"]
    
    # Delete it
    response = client.delete(f"/api/mock-wechat/conversations/{conv_id}/messages/{msg_id}")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    
    # Verify it's gone
    messages = client.get(f"/api/mock-wechat/conversations/{conv_id}/messages").json()
    assert not any(m["id"] == msg_id for m in messages)


def test_sync_to_json_store_when_mock_mode(client: TestClient) -> None:
    # Set transport mode to mock
    connection = OpenClawConnection(transport_mode="mock")
    assert client.put("/api/openclaw/connection", json=connection.model_dump()).status_code == 200
    
    # Add some mock data
    client.post(
        "/api/mock-wechat/conversations",
        json={"display_name": "同步测试"},
    )
    client.post(
        "/api/mock-wechat/conversations/conv_demo/messages",
        data={"sender": "wechat_user", "content": "同步消息"},
    )
    
    # Trigger sync via openclaw sync endpoint
    response = client.post("/api/openclaw/sync")
    assert response.status_code == 200
    stats = response.json()
    assert stats["sessions"] >= 2  # demo + new one
    assert stats["messages"] >= 1
    
    # Verify data is in store
    conversations = client.get("/api/wechat/conversations").json()
    assert len(conversations) >= 2
    messages = client.get("/api/wechat/conversations/conv_demo/messages").json()
    assert any(m["content"] == "同步消息" for m in messages)


def test_wechat_conversations_endpoint_includes_mock_data(client: TestClient) -> None:
    # Set mock mode
    connection = OpenClawConnection(transport_mode="mock")
    client.put("/api/openclaw/connection", json=connection.model_dump())
    
    # Add mock conversation
    client.post(
        "/api/mock-wechat/conversations",
        json={"display_name": "微信接口测试"},
    )
    
    # The wechat conversations endpoint should include mock data after sync
    response = client.get("/api/wechat/conversations")
    assert response.status_code == 200
    conversations = response.json()
    assert any(c.get("contact", {}).get("display_name") == "微信接口测试" for c in conversations)


def test_wechat_send_endpoint_in_mock_mode(client: TestClient) -> None:
    # Set mock mode
    connection = OpenClawConnection(transport_mode="mock")
    client.put("/api/openclaw/connection", json=connection.model_dump())
    
    # Use the wechat send endpoint
    response = client.post(
        "/api/wechat/conversations/conv_demo/send",
        json={"content": "通过微信接口发送"},
    )
    assert response.status_code == 200
    msg = response.json()
    assert msg["content"] == "通过微信接口发送"
    assert msg["sender"] == "owner"
    assert msg["direction"] == "outbound"
    
    # Verify it's in mock store
    mock_messages = client.get("/api/mock-wechat/conversations/conv_demo/messages").json()
    assert any(m["content"] == "通过微信接口发送" for m in mock_messages)


def test_assets_are_served(client: TestClient) -> None:
    conv_id = "conv_demo"
    
    # Upload a file
    file_content = b"Hello, World!"
    files = {"files": ("hello.txt", BytesIO(file_content), "text/plain")}
    msg = client.post(
        f"/api/mock-wechat/conversations/{conv_id}/messages",
        data={"sender": "owner", "content": ""},
        files=files,
    ).json()
    
    # Get the asset URL
    asset_url = msg["attachments"][0]["url"]
    assert asset_url.startswith("/mock-wechat-assets/")
    
    # Serve the asset
    response = client.get(asset_url)
    assert response.status_code == 200
    assert response.content == file_content