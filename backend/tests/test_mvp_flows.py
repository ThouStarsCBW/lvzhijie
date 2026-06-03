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


def test_task_center_executes_research_review_and_drafting(client: TestClient) -> None:
    similar_task = client.post(
        "/api/cases/case_demo/tasks",
        json={
            "title": "检索拖欠工资类案",
            "task_type": "similar_case_search",
            "description": "拖欠工资和被迫离职",
            "assigned_agent_role": "法律检索 Agent",
        },
    )
    assert similar_task.status_code == 200
    similar_task_id = similar_task.json()["id"]

    executed_similar = client.post(f"/api/cases/case_demo/tasks/{similar_task_id}/execute", json={})
    assert executed_similar.status_code == 200
    assert executed_similar.json()["status"] == "waiting_owner_review"

    regulation_task = client.post(
        "/api/cases/case_demo/tasks",
        json={
            "title": "检索劳动法规",
            "task_type": "regulation_search",
            "description": "工资支付和劳动仲裁时效",
            "assigned_agent_role": "法律检索 Agent",
        },
    )
    regulation_task_id = regulation_task.json()["id"]
    assert client.post(f"/api/cases/case_demo/tasks/{regulation_task_id}/execute", json={}).status_code == 200

    doc_resp = client.post(
        "/api/documents",
        json={
            "case_id": "case_demo",
            "title": "任务中心审查合同",
            "document_type": "contract",
            "content_text": "甲方应在7日内付款，违约金每日万分之三。",
        },
    )
    assert doc_resp.status_code == 200
    document_id = doc_resp.json()["id"]
    first_rev_id = client.get(f"/api/documents/{document_id}").json()["revisions"][0]["id"]
    second_rev = client.post(
        f"/api/documents/{document_id}/revisions",
        json={"content_text": "甲方应在30日内付款，违约金每日万分之一。", "change_summary": "付款和违约金调整"},
    )
    assert second_rev.status_code == 200
    second_rev_id = second_rev.json()["id"]

    review_task = client.post(
        "/api/cases/case_demo/tasks",
        json={
            "title": "审查合同版本差异",
            "task_type": "document_review",
            "document_id": document_id,
            "base_revision_id": first_rev_id,
            "target_revision_id": second_rev_id,
            "assigned_agent_role": "合同审查律师 Agent",
        },
    )
    review_task_id = review_task.json()["id"]
    executed_review = client.post(f"/api/cases/case_demo/tasks/{review_task_id}/execute", json={})
    assert executed_review.status_code == 200
    assert executed_review.json()["metadata"]["analysis_id"]
    assert "风险" in executed_review.json()["result_summary"]

    drafting_task = client.post(
        "/api/cases/case_demo/tasks",
        json={
            "title": "起草劳动争议意见",
            "task_type": "document_drafting",
            "document_id": document_id,
            "assigned_agent_role": "文书起草 Agent",
        },
    )
    drafting_task_id = drafting_task.json()["id"]
    executed_drafting = client.post(
        f"/api/cases/case_demo/tasks/{drafting_task_id}/execute",
        json={"content_text": "劳动争议处理意见草稿。"},
    )
    assert executed_drafting.status_code == 200
    drafting_payload = executed_drafting.json()
    assert drafting_payload["output_document_id"] == document_id
    assert drafting_payload["output_revision_id"]

    detail = client.get("/api/cases/case_demo").json()
    assert detail["research_runs"]
    assert detail["research_results"]
    enriched = next(task for task in detail["tasks"] if task["id"] == similar_task_id)
    assert enriched["comments"]
    assert enriched["research_results"]


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


# ---- Section 14: Version Control Tests ----


def test_upload_creates_main_branch_automatically(client: TestClient) -> None:
    """14.1: Upload file automatically creates main branch."""
    resp = client.post(
        "/api/documents/upload",
        data={"title": "测试合同", "document_type": "contract", "change_summary": "上传初始版本"},
        files={"file": ("contract.txt", "甲方应在验收后7日内付款。", "text/plain")},
    )
    assert resp.status_code == 200
    document_id = resp.json()["id"]

    detail = client.get(f"/api/documents/{document_id}").json()
    assert "branches" in detail
    branches = detail["branches"]
    main_branch = next((b for b in branches if b["name"] == "main"), None)
    assert main_branch is not None
    assert main_branch["is_default"] is True

    revisions = detail["revisions"]
    assert len(revisions) >= 1
    assert revisions[0]["branch_id"] == main_branch["id"]


def test_create_branch(client: TestClient) -> None:
    """14.2: Create a new branch from existing revision."""
    resp = client.post(
        "/api/documents",
        json={"title": "分支测试", "document_type": "contract", "content_text": "初始版本文本。"},
    )
    assert resp.status_code == 200
    document_id = resp.json()["id"]

    detail = client.get(f"/api/documents/{document_id}").json()
    first_revision_id = detail["revisions"][0]["id"]

    branch_resp = client.post(
        f"/api/documents/{document_id}/branches",
        json={"name": "client-edits", "base_revision_id": first_revision_id},
    )
    assert branch_resp.status_code == 200
    branch = branch_resp.json()
    assert branch["name"] == "client-edits"
    assert branch["head_revision_id"] == first_revision_id
    assert branch["base_revision_id"] == first_revision_id
    assert branch["is_default"] is False


def test_upload_revision_to_branch(client: TestClient) -> None:
    """14.3: Upload a new revision to a specific branch."""
    resp = client.post(
        "/api/documents",
        json={"title": "分支上传测试", "document_type": "contract", "content_text": "初始版本。"},
    )
    assert resp.status_code == 200
    document_id = resp.json()["id"]

    detail = client.get(f"/api/documents/{document_id}").json()
    base_rev_id = detail["revisions"][0]["id"]

    branch_resp = client.post(
        f"/api/documents/{document_id}/branches",
        json={"name": "test-branch", "base_revision_id": base_rev_id},
    )
    assert branch_resp.status_code == 200
    branch_id = branch_resp.json()["id"]

    upload_resp = client.post(
        f"/api/documents/{document_id}/branches/{branch_id}/revisions/upload",
        files={"file": ("v2.txt", "分支上的新版本内容。", "text/plain")},
        data={"change_summary": "分支上传"},
    )
    assert upload_resp.status_code == 200
    new_rev = upload_resp.json()
    assert new_rev["branch_id"] == branch_id
    assert new_rev["parent_revision_id"] == base_rev_id

    tree = client.get(f"/api/documents/{document_id}/tree").json()
    branch_in_tree = next(b for b in tree["branches"] if b["id"] == branch_id)
    assert any(r["id"] == new_rev["id"] for r in branch_in_tree["revisions"])


def test_cross_branch_diff(client: TestClient) -> None:
    """14.4: Cross-branch diff between different branches."""
    resp = client.post(
        "/api/documents/upload",
        data={"title": "跨分支对比", "document_type": "contract", "change_summary": "初始"},
        files={"file": ("v1.txt", "甲方应在验收后7日内付款。", "text/plain")},
    )
    assert resp.status_code == 200
    document_id = resp.json()["id"]

    detail = client.get(f"/api/documents/{document_id}").json()
    main_rev1_id = detail["revisions"][0]["id"]
    main_branch_id = detail["branches"][0]["id"]

    # Create branch A from v1
    branch_resp = client.post(
        f"/api/documents/{document_id}/branches",
        json={"name": "branch-a", "base_revision_id": main_rev1_id},
    )
    assert branch_resp.status_code == 200
    branch_a_id = branch_resp.json()["id"]

    # Upload v2 to branch A
    upload_a = client.post(
        f"/api/documents/{document_id}/branches/{branch_a_id}/revisions/upload",
        files={"file": ("v2a.txt", "甲方应在验收后14日内付款。违约金每日万分之二。", "text/plain")},
        data={"change_summary": "分支A版本"},
    )
    assert upload_a.status_code == 200
    branch_a_rev_id = upload_a.json()["id"]

    # Upload v3 to main
    upload_main = client.post(
        f"/api/documents/{document_id}/branches/{main_branch_id}/revisions/upload",
        files={"file": ("v3.txt", "甲方应在验收后30日内付款。违约金每日万分之一。", "text/plain")},
        data={"change_summary": "主分支版本"},
    )
    assert upload_main.status_code == 200
    main_rev3_id = upload_main.json()["id"]

    # Cross-branch diff
    diff = client.get(
        f"/api/documents/{document_id}/diff",
        params={"base_revision_id": branch_a_rev_id, "target_revision_id": main_rev3_id},
    )
    assert diff.status_code == 200
    assert diff.json()["segments"]


def test_export_diff_docx(client: TestClient) -> None:
    """14.5: Export diff as Word document with red/green markers."""
    resp = client.post(
        "/api/documents",
        json={"title": "Word导出测试", "document_type": "contract", "content_text": "原始文本内容。"},
    )
    assert resp.status_code == 200
    document_id = resp.json()["id"]

    detail = client.get(f"/api/documents/{document_id}").json()
    rev1_id = detail["revisions"][0]["id"]
    main_branch_id = detail["branches"][0]["id"]

    upload_resp = client.post(
        f"/api/documents/{document_id}/branches/{main_branch_id}/revisions",
        json={"content_text": "修改后的新版本文本内容。", "change_summary": "修改版本"},
    )
    assert upload_resp.status_code == 200
    rev2_id = upload_resp.json()["id"]

    exported = client.get(
        f"/api/documents/{document_id}/diff/export.docx",
        params={"base_revision_id": rev1_id, "target_revision_id": rev2_id},
    )
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert exported.content.startswith(b"PK")


def test_ai_analysis_fallback_without_key(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """14.6: AI analysis falls back to rule-based when no API key."""
    monkeypatch.delenv("LVZHIJIE_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    resp = client.post(
        "/api/documents",
        json={"title": "AI分析测试", "document_type": "contract", "content_text": "甲方应付款。违约金每日万分之三。"},
    )
    assert resp.status_code == 200
    document_id = resp.json()["id"]

    detail = client.get(f"/api/documents/{document_id}").json()
    rev1_id = detail["revisions"][0]["id"]
    main_branch_id = detail["branches"][0]["id"]

    upload_resp = client.post(
        f"/api/documents/{document_id}/branches/{main_branch_id}/revisions",
        json={"content_text": "甲方应30日内付款。违约金每日万分之一。", "change_summary": "修改"},
    )
    assert upload_resp.status_code == 200
    rev2_id = upload_resp.json()["id"]

    analysis = client.post(
        f"/api/documents/{document_id}/diff/analyze",
        json={"base_revision_id": rev1_id, "target_revision_id": rev2_id},
    )
    assert analysis.status_code == 200
    result = analysis.json()
    assert result["source"] == "rule_fallback"
    assert len(result["risk_points"]) > 0
    assert len(result["manual_review_checklist"]) > 0


def test_delete_document_cascades_branches_and_analyses(client: TestClient) -> None:
    """14.7: Deleting a document cascades branches and analyses."""
    resp = client.post(
        "/api/documents",
        json={"title": "级联删除测试", "document_type": "contract", "content_text": "测试文本。"},
    )
    assert resp.status_code == 200
    document_id = resp.json()["id"]

    detail = client.get(f"/api/documents/{document_id}").json()
    rev1_id = detail["revisions"][0]["id"]
    main_branch_id = detail["branches"][0]["id"]

    # Create a branch
    branch_resp = client.post(
        f"/api/documents/{document_id}/branches",
        json={"name": "temp-branch", "base_revision_id": rev1_id},
    )
    assert branch_resp.status_code == 200

    # Upload another revision for analysis
    upload_resp = client.post(
        f"/api/documents/{document_id}/branches/{main_branch_id}/revisions",
        json={"content_text": "新版本文本。", "change_summary": "新版本"},
    )
    assert upload_resp.status_code == 200
    rev2_id = upload_resp.json()["id"]

    # Create analysis
    import os
    os.environ.pop("LVZHIJIE_LLM_API_KEY", None)
    os.environ.pop("OPENAI_API_KEY", None)
    analysis_resp = client.post(
        f"/api/documents/{document_id}/diff/analyze",
        json={"base_revision_id": rev1_id, "target_revision_id": rev2_id},
    )
    assert analysis_resp.status_code == 200

    # Delete document
    deleted = client.delete(f"/api/documents/{document_id}")
    assert deleted.status_code == 200
    assert client.get(f"/api/documents/{document_id}").status_code == 404

    # Verify tree has no branches for this document
    tree_resp = client.get(f"/api/documents/{document_id}/tree")
    assert tree_resp.status_code == 404
