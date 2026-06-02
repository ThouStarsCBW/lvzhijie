from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

import app.main as main
from app.models import OpenClawConnection
from app.store import JsonStore


@pytest.fixture()
def client(tmp_path) -> TestClient:
    main.store = JsonStore(tmp_path / "store.json")
    return TestClient(main.app)


def test_seed_contains_complete_law_firm_agents(client: TestClient) -> None:
    agents = client.get("/api/agents").json()
    roles = {agent["role"] for agent in agents}
    assert {
        "dispatch_agent",
        "core_business_agent",
        "client_service_agent",
        "compliance_review_agent",
        "archive_management_agent",
        "managing_lawyer",
        "reception_lawyer",
        "case_secretary",
        "handling_lawyer",
        "contract_reviewer",
        "litigation_strategist",
        "legal_researcher",
        "quality_control",
        "drafting_lawyer",
    } <= roles


def test_agent_architecture_exposes_dispatcher_and_departments(client: TestClient) -> None:
    architecture = client.get("/api/agents/architecture")

    assert architecture.status_code == 200
    payload = architecture.json()
    assert payload["dispatcher"]["role"] == "dispatch_agent"
    core = next(group for group in payload["groups"] if group["id"] == "core_business")
    assert any(department["title"] == "刑事法律事务部" for department in core["departments"])
    assert any(department["title"] == "劳动法律事务部" for department in core["departments"])
    client_service = next(group for group in payload["groups"] if group["id"] == "client_service")
    compliance = next(group for group in payload["groups"] if group["id"] == "compliance_review")
    archive = next(group for group in payload["groups"] if group["id"] == "archive_management")
    assert {department["title"] for department in client_service["departments"]} >= {"法律咨询", "接案报价", "投诉处理"}
    assert {department["title"] for department in compliance["departments"]} >= {"收案审批", "利益冲突审查", "风险评估"}
    assert {department["title"] for department in archive["departments"]} >= {"案卷归档", "档案查询"}


def test_upload_revision_and_diff_flow(client: TestClient) -> None:
    created = client.post(
        "/api/documents/upload",
        data={"title": "付款合同", "document_type": "contract", "change_summary": "上传初始版本"},
        files={"file": ("contract-v1.txt", "甲方应在验收后7日内付款。违约金每日万分之三。", "text/plain")},
    )
    assert created.status_code == 200
    document_id = created.json()["id"]

    revision = client.post(
        f"/api/documents/{document_id}/revisions/upload",
        data={"change_summary": "上传第二版"},
        files={"file": ("contract-v2.md", "甲方应在验收后30日内付款。违约金每日万分之一。", "text/markdown")},
    )
    assert revision.status_code == 200

    diff = client.get(f"/api/documents/{document_id}/diff")
    assert diff.status_code == 200
    payload = diff.json()
    assert payload["segments"]
    assert payload["paragraph_changes"]
    assert any("付款" in risk or "违约" in risk for risk in payload["risk_summary"])

    exported = client.get(f"/api/documents/{document_id}/export.docx")
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert exported.content.startswith(b"PK")


def test_delete_document_removes_revisions_and_diffs(client: TestClient) -> None:
    created = client.post(
        "/api/documents",
        json={
            "title": "可删除文件",
            "document_type": "contract",
            "content_text": "第一版文本。",
        },
    )
    assert created.status_code == 200
    document_id = created.json()["id"]
    assert client.post(
        f"/api/documents/{document_id}/revisions",
        json={"content_text": "第二版文本。"},
    ).status_code == 200
    assert client.get(f"/api/documents/{document_id}/diff").status_code == 200

    deleted = client.delete(f"/api/documents/{document_id}")

    assert deleted.status_code == 200
    assert client.get(f"/api/documents/{document_id}").status_code == 404
    assert all(item["id"] != document_id for item in client.get("/api/documents").json())


def test_delete_case_cascades_owned_rows_and_unbinds_conversation(client: TestClient) -> None:
    created = client.post(
        "/api/cases",
        json={"title": "待删除案件", "case_type": "debt", "summary": "会产生关联数据。"},
    )
    assert created.status_code == 200
    case_id = created.json()["id"]
    assert client.post(f"/api/cases/{case_id}/tasks", json={"title": "待删任务"}).status_code == 200
    assert client.post(
        f"/api/cases/{case_id}/memories",
        json={"kind": "fact", "content": "待删事实"},
    ).status_code == 200
    assert client.post(
        f"/api/cases/{case_id}/follow-up-questions",
        json={"content": "待删追问"},
    ).status_code == 200
    assert client.post(
        "/api/documents",
        json={
            "case_id": case_id,
            "title": "待删关联文件",
            "document_type": "evidence",
            "content_text": "证据文本。",
        },
    ).status_code == 200
    assert client.post("/api/wechat/conversations/conv_demo/bind-case", json={"case_id": case_id}).status_code == 200

    deleted = client.delete(f"/api/cases/{case_id}")

    assert deleted.status_code == 200
    assert client.get(f"/api/cases/{case_id}").status_code == 404
    conversations = client.get("/api/wechat/conversations").json()
    demo = next(item for item in conversations if item["id"] == "conv_demo")
    assert demo["case_id"] is None


def test_reasoning_creates_followups_and_mock_send(client: TestClient) -> None:
    connection = OpenClawConnection(transport_mode="mock")
    assert client.put("/api/openclaw/connection", json=connection.model_dump()).status_code == 200

    generated = client.post("/api/reasoning/cases/case_demo/generate")
    assert generated.status_code == 200

    detail = client.get("/api/cases/case_demo").json()
    questions = detail["follow_up_questions"]
    assert len(questions) >= 3

    sent = client.post(f"/api/cases/case_demo/follow-up-questions/{questions[0]['id']}/send", json={})
    assert sent.status_code == 200
    payload = sent.json()
    assert payload["question"]["status"] == "sent_via_openclaw"
    assert payload["message"]["status"] == "sent_via_openclaw"


def test_create_case_from_conversation_summarizes_chat_without_llm(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LVZHIJIE_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    response = client.post("/api/wechat/conversations/conv_demo/case", json={})

    assert response.status_code == 200
    created = response.json()
    assert created["conversation_ref"] == "conv_demo"
    assert created["wechat_contact_ref"] == "contact_demo"
    assert created["case_type"] == "labor"
    assert "张先生" in created["title"]
    assert "拖欠" in created["summary"]
    detail = client.get(f"/api/cases/{created['id']}").json()
    memories = detail["memories"]
    assert any(memory["kind"] == "fact" and "工资" in memory["content"] for memory in memories)
    assert any(memory["kind"] == "uncertainty" for memory in memories)
    assert detail["tasks"]
    conversations = client.get("/api/wechat/conversations").json()
    demo = next(item for item in conversations if item["id"] == "conv_demo")
    assert demo["case_id"] == created["id"]


def test_reply_workflow_creates_short_and_long_outputs(client: TestClient) -> None:
    short_job = client.post(
        "/api/cases/case_demo/reply-jobs",
        json={
            "mode": "short_reply",
            "title": "短回复草稿",
            "user_question": "公司欠薪怎么办？",
            "assigned_agent_role": "客户服务 Agent",
        },
    )
    assert short_job.status_code == 200
    assert short_job.json()["status"] == "ready_for_review"
    assert short_job.json()["draft_text"]

    long_job = client.post(
        "/api/cases/case_demo/reply-jobs",
        json={
            "mode": "long_reply",
            "title": "长回复推理",
            "assigned_agent_role": "文书起草 Agent",
        },
    )
    assert long_job.status_code == 200
    assert long_job.json()["status"] == "queued"

    processed = client.post(f"/api/cases/case_demo/reply-jobs/{long_job.json()['id']}/process")
    assert processed.status_code == 200
    payload = processed.json()
    assert payload["status"] == "completed"
    assert payload["module_state"] == "idle"
    assert payload["output_document_id"]
    detail = client.get("/api/cases/case_demo").json()
    assert any(job["id"] == payload["id"] for job in detail["reply_jobs"])
    assert any(document["id"] == payload["output_document_id"] for document in detail["documents"])


def test_bind_existing_case_to_wechat_conversation(client: TestClient) -> None:
    created = client.post(
        "/api/cases",
        json={"title": "手动案件", "case_type": "debt", "summary": "待绑定微信会话。"},
    )
    case_id = created.json()["id"]

    bound = client.post("/api/wechat/conversations/conv_demo/bind-case", json={"case_id": case_id})
    assert bound.status_code == 200
    assert bound.json()["conversation_ref"] == "conv_demo"

    conversations = client.get("/api/wechat/conversations").json()
    demo = next(item for item in conversations if item["id"] == "conv_demo")
    assert demo["case_id"] == case_id


def test_delete_wechat_conversation_removes_messages_and_unbinds_case(client: TestClient) -> None:
    assert client.get("/api/wechat/conversations/conv_demo/messages").json()

    deleted = client.delete("/api/wechat/conversations/conv_demo")

    assert deleted.status_code == 200
    payload = deleted.json()
    assert payload["ok"] is True
    assert payload["messages"] >= 1
    conversations = client.get("/api/wechat/conversations").json()
    assert all(item["id"] != "conv_demo" for item in conversations)
    assert client.get("/api/wechat/conversations/conv_demo/messages").json() == []
    case = client.get("/api/cases/case_demo").json()["case"]
    assert case["conversation_ref"] is None
    assert case["wechat_contact_ref"] is None
