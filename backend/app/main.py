from __future__ import annotations

import json
import os
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from docx import Document as DocxDocument
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.diffing import build_char_diff, build_paragraph_diff, summarize_legal_risks
from app.models import (
    ActivityEvent,
    AgentArchitecture,
    AgentDepartment,
    AgentGroup,
    BindConversationCaseRequest,
    Case,
    CaseCreateRequest,
    CaseMemory,
    CaseTask,
    CreateCaseFromConversationRequest,
    DocumentCreateRequest,
    FollowUpQuestion,
    LegalAgent,
    LegalDocument,
    LegalDocumentDiff,
    LegalDocumentRevision,
    LegalReplyJob,
    LegalReasoningRun,
    MemoryCreateRequest,
    MockConversationCreateRequest,
    MockConversationUpdateRequest,
    OpenClawConnection,
    ReasoningEdge,
    ReasoningNode,
    RevisionCreateRequest,
    ReplyJobCreateRequest,
    SendFollowUpRequest,
    SendMessageRequest,
    TaskCreateRequest,
    WechatContact,
    WechatConversation,
    WechatMessage,
    now_iso,
)
from app.mock_wechat_store import MockWechatStore
from app.openclaw_adapter import OpenClawWechatAdapter
from app.store import JsonStore

app = FastAPI(title="Lvzhijie Legal Workspace API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = JsonStore(Path(__file__).parent / "data" / "store.json")
mock_wechat = MockWechatStore(Path(__file__).parent / "data" / "mock_wechat")

app.mount(
    "/mock-wechat-assets",
    StaticFiles(directory=Path(__file__).parent / "data" / "mock_wechat" / "assets"),
    name="mock-wechat-assets",
)


def connection() -> OpenClawConnection:
    return OpenClawConnection.model_validate(store.data["openclaw_connection"])


def using_mock_wechat() -> bool:
    return connection().transport_mode == "mock"


def sync_mock_wechat_if_needed() -> None:
    if using_mock_wechat():
        mock_wechat.sync_to_json_store(store)


def record(event_type: str, title: str, description: str = "", **refs: str | None) -> None:
    store.add(
        "activity_events",
        ActivityEvent(
            event_type=event_type,
            title=title,
            description=description,
            entity_type=refs.get("entity_type"),
            entity_id=refs.get("entity_id"),
        ),
    )


def delete_document_rows(document_id: str) -> None:
    store.remove_where("legal_document_revisions", lambda row: row.get("document_id") == document_id)
    store.remove_where("legal_document_diffs", lambda row: row.get("document_id") == document_id)
    store.delete("legal_documents", document_id)


def delete_wechat_conversation_rows(conversation: WechatConversation) -> dict[str, object]:
    removed_messages = store.remove_where(
        "wechat_messages",
        lambda row: row.get("conversation_id") == conversation.id,
    )
    for case in store.list("cases", Case):
        if case.conversation_ref == conversation.id or case.id == conversation.case_id:
            case.conversation_ref = None
            case.wechat_contact_ref = None
            case.updated_at = now_iso()
            store.update("cases", case)
    deleted = store.delete("wechat_conversations", conversation.id)
    remaining_contact_refs = {
        item.get("contact_id")
        for item in store.data.get("wechat_conversations", [])
        if isinstance(item, dict)
    }
    if conversation.contact_id not in remaining_contact_refs:
        store.delete("wechat_contacts", conversation.contact_id)
    return {"deleted": deleted, "messages": removed_messages}


async def read_legal_file_text(upload: UploadFile) -> str:
    filename = upload.filename or "upload.txt"
    suffix = Path(filename).suffix.lower()
    content = await upload.read()
    if suffix == ".docx":
        document = DocxDocument(BytesIO(content))
        parts = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
        for table in document.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))
        return "\n".join(parts)
    if suffix in {".txt", ".md", ""}:
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        return content.decode("utf-8", errors="replace")
    raise HTTPException(status_code=415, detail="Only .txt, .md and .docx files are supported")


CASE_TYPE_LABELS = {
    "contract": "合同纠纷",
    "labor": "劳动争议",
    "marriage": "婚姻家事",
    "debt": "债权债务",
    "traffic": "交通事故",
    "company": "公司商事",
    "real_estate": "房产纠纷",
    "criminal": "刑事法律事务",
    "other": "综合法律咨询",
}

CASE_RULE_HINTS = {
    "contract": "重点核对合同成立、生效、履行、违约、解除和争议解决条款。",
    "labor": "重点核对劳动关系、工资标准、欠薪期间、解除事实、仲裁时效和证据材料。",
    "marriage": "重点核对身份关系、共同财产、债务来源、子女抚养和财产处分证据。",
    "debt": "重点核对借贷合意、款项交付、还款约定、催收记录和诉讼时效。",
    "traffic": "重点核对事故责任、伤情损失、保险信息、医疗票据和误工证明。",
    "company": "重点核对公司决议、股东权利、交易文件、履行记录和内部审批。",
    "real_estate": "重点核对合同、产权状态、付款节点、交付验收和违约责任。",
    "criminal": "重点核对涉嫌罪名、行为事实、主观状态、证据来源和程序节点。",
    "other": "重点核对法律关系、请求基础、证据来源、时效和可执行路径。",
}

CASE_TYPE_VALUES = set(CASE_TYPE_LABELS)

CASE_TYPE_KEYWORDS = {
    "labor": ["工资", "劳动", "入职", "离职", "公司拖欠", "仲裁", "社保", "工伤", "解除"],
    "contract": ["合同", "违约", "履行", "验收", "定金", "条款", "付款期限"],
    "debt": ["借款", "欠款", "还钱", "转账", "债务", "借条", "催收"],
    "marriage": ["离婚", "抚养", "夫妻", "婚姻", "财产分割", "继承"],
    "traffic": ["交通事故", "追尾", "保险", "交警", "责任认定", "伤残"],
    "company": ["股东", "公司", "股权", "合伙", "章程", "分红", "决议"],
    "real_estate": ["房屋", "房产", "买房", "租房", "物业", "交房", "产权"],
    "criminal": ["刑事", "拘留", "取保", "立案", "诈骗", "寻衅滋事", "派出所"],
}

CORE_DEPARTMENTS = [
    AgentDepartment(
        id="criminal_department",
        title="刑事法律事务部",
        description="处理刑事咨询、控告申诉、取保候审与辩护策略。",
        case_types=["criminal"],
    ),
    AgentDepartment(
        id="civil_commercial_department",
        title="民商法律事务部",
        description="处理合同、债权债务、公司商事和一般民事争议。",
        case_types=["contract", "debt", "company"],
    ),
    AgentDepartment(
        id="traffic_department",
        title="交通法律事务部",
        description="处理交通事故责任、赔偿项目、保险理赔和调解诉讼。",
        case_types=["traffic"],
    ),
    AgentDepartment(
        id="ip_department",
        title="知识产权法律事务部",
        description="处理著作权、商标、商业秘密和知识产权合同风险。",
        case_types=["other"],
    ),
    AgentDepartment(
        id="marriage_wealth_department",
        title="婚姻家事与财富传承法律事务部",
        description="处理婚姻家事、继承、财富规划和家族财产安排。",
        case_types=["marriage"],
    ),
    AgentDepartment(
        id="tax_department",
        title="财税法律事务部",
        description="处理财税合规、交易税负、发票风险和税务争议。",
        case_types=["company", "other"],
    ),
    AgentDepartment(
        id="labor_department",
        title="劳动法律事务部",
        description="处理劳动合同、欠薪、解除、工伤和劳动仲裁。",
        case_types=["labor"],
    ),
]

CLIENT_SERVICE_DEPARTMENTS = [
    AgentDepartment(
        id="legal_consultation_service",
        title="法律咨询",
        description="承接初步法律咨询、问题识别、沟通口径和下一步材料清单。",
        case_types=["other"],
    ),
    AgentDepartment(
        id="intake_quote_service",
        title="接案报价",
        description="根据案件类型、工作量、风险和交付范围形成接案与报价建议。",
        case_types=["contract", "labor", "marriage", "debt", "traffic", "company", "real_estate", "criminal", "other"],
    ),
    AgentDepartment(
        id="complaint_handling_service",
        title="投诉处理",
        description="记录客户投诉、识别服务问题、推动内部处理和反馈闭环。",
        case_types=["other"],
    ),
]

COMPLIANCE_REVIEW_DEPARTMENTS = [
    AgentDepartment(
        id="case_acceptance_approval",
        title="收案审批",
        description="审查案件是否满足收案条件、材料基础、服务边界和人工复核要求。",
        case_types=["contract", "labor", "marriage", "debt", "traffic", "company", "real_estate", "criminal", "other"],
    ),
    AgentDepartment(
        id="conflict_check",
        title="利益冲突审查",
        description="核查客户、相对方、关联主体和既有案件之间的潜在利益冲突。",
        case_types=["contract", "labor", "marriage", "debt", "traffic", "company", "real_estate", "criminal", "other"],
    ),
    AgentDepartment(
        id="risk_assessment",
        title="风险评估",
        description="评估事实不确定性、证据缺口、合规风险、声誉风险和对外表述边界。",
        case_types=["contract", "labor", "marriage", "debt", "traffic", "company", "real_estate", "criminal", "other"],
    ),
]

ARCHIVE_MANAGEMENT_DEPARTMENTS = [
    AgentDepartment(
        id="case_file_archiving",
        title="案卷归档",
        description="归档案件材料、版本文书、证据目录、推理记录和过程留痕。",
        case_types=["contract", "labor", "marriage", "debt", "traffic", "company", "real_estate", "criminal", "other"],
    ),
    AgentDepartment(
        id="archive_search",
        title="档案查询",
        description="按案件、客户、文件类型、时间线和证据标签查询历史档案。",
        case_types=["contract", "labor", "marriage", "debt", "traffic", "company", "real_estate", "criminal", "other"],
    ),
]


def case_type_label(case_type: str) -> str:
    return CASE_TYPE_LABELS.get(case_type, "综合法律咨询")


def case_rule_hint(case_type: str) -> str:
    return CASE_RULE_HINTS.get(case_type, CASE_RULE_HINTS["other"])


def first_sentence(value: str, fallback: str = "暂未形成摘要。") -> str:
    text = " ".join(value.split())
    if not text:
        return fallback
    for marker in ("。", "；", ";", "."):
        if marker in text:
            return text.split(marker, 1)[0] + marker
    return text[:120]


def message_plaintext(message: WechatMessage) -> str:
    attachment_names = "、".join(attachment.name for attachment in message.attachments)
    content = message.content.strip()
    if attachment_names:
        return f"{content} [附件：{attachment_names}]" if content else f"[附件：{attachment_names}]"
    return content


def build_conversation_transcript(messages: list[WechatMessage]) -> str:
    sender_labels = {
        "wechat_user": "客户",
        "openclaw_auto": "微信桥自动回复",
        "owner": "我方",
        "system": "系统",
    }
    lines = []
    for message in messages:
        text = message_plaintext(message).strip()
        if not text:
            continue
        sender = sender_labels.get(message.sender, message.sender)
        lines.append(f"{message.created_at} {sender}：{text}")
    return "\n".join(lines)


def infer_case_type_from_text(text: str) -> str:
    scores: dict[str, int] = {}
    for case_type, keywords in CASE_TYPE_KEYWORDS.items():
        scores[case_type] = sum(1 for keyword in keywords if keyword in text)
    best_type, best_score = max(scores.items(), key=lambda item: item[1])
    return best_type if best_score > 0 else "other"


def fallback_case_analysis(
    *,
    contact: WechatContact | None,
    messages: list[WechatMessage],
    requested_title: str | None = None,
    requested_case_type: str | None = None,
) -> dict[str, object]:
    message_texts = [message_plaintext(message) for message in messages if message_plaintext(message).strip()]
    inbound_texts = [
        message_plaintext(message)
        for message in messages
        if message.direction == "inbound" and message_plaintext(message).strip()
    ]
    transcript_text = " ".join(message_texts)
    inferred_type = requested_case_type if requested_case_type in CASE_TYPE_VALUES else infer_case_type_from_text(transcript_text)
    display_name = contact.display_name if contact else "微信用户"
    title = requested_title or f"{display_name}{case_type_label(inferred_type)}咨询"
    summary_source = " ".join(inbound_texts or message_texts)
    facts = [text[:160] for text in inbound_texts[:5]]
    evidences = []
    for message in messages:
        for attachment in message.attachments:
            evidences.append(f"客户或我方上传附件：{attachment.name}")
    uncertainties = [
        "需进一步确认关键时间节点、证据来源和客户的最终处理目标。",
        f"需按{case_type_label(inferred_type)}方向核对请求基础、时效和可证明材料。",
    ]
    return {
        "title": title[:80],
        "case_type": inferred_type,
        "summary": first_sentence(summary_source, "由微信会话创建，暂未形成充分案情摘要。")[:500],
        "facts": facts or ["已从微信会话创建案件，需继续补充事实。"],
        "evidence": evidences,
        "uncertainties": uncertainties,
        "suggested_tasks": [
            "整理完整时间线",
            "核对证据材料",
            "明确客户诉求和处理路径",
        ],
    }


def extract_json_object(text: str) -> dict[str, Any] | None:
    value = text.strip()
    if not value:
        return None
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    start = value.find("{")
    end = value.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(value[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def normalize_case_analysis(raw: dict[str, Any], fallback: dict[str, object]) -> dict[str, object]:
    case_type = str(raw.get("case_type") or fallback["case_type"])
    if case_type not in CASE_TYPE_VALUES:
        case_type = str(fallback["case_type"])

    def string_list(key: str, fallback_key: str) -> list[str]:
        value = raw.get(key)
        if isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
            return items[:8]
        return list(fallback.get(fallback_key, []))[:8]  # type: ignore[arg-type]

    return {
        "title": (str(raw.get("title") or fallback["title"]).strip() or str(fallback["title"]))[:80],
        "case_type": case_type,
        "summary": (str(raw.get("summary") or fallback["summary"]).strip() or str(fallback["summary"]))[:800],
        "facts": string_list("facts", "facts"),
        "evidence": string_list("evidence", "evidence"),
        "uncertainties": string_list("uncertainties", "uncertainties"),
        "suggested_tasks": string_list("suggested_tasks", "suggested_tasks"),
    }


async def analyze_conversation_for_case(
    *,
    contact: WechatContact | None,
    messages: list[WechatMessage],
    requested_title: str | None,
    requested_case_type: str | None,
) -> dict[str, object]:
    fallback = fallback_case_analysis(
        contact=contact,
        messages=messages,
        requested_title=requested_title,
        requested_case_type=requested_case_type,
    )
    api_key = os.getenv("LVZHIJIE_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return fallback

    transcript = build_conversation_transcript(messages)
    if not transcript:
        return fallback
    base_url = (os.getenv("LVZHIJIE_LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("LVZHIJIE_LLM_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
    prompt = f"""请根据以下微信咨询聊天记录，生成一份案件建档 JSON。
只能输出 JSON 对象，不要输出 Markdown。
JSON 字段必须包含：
- title: 80字以内案件标题
- case_type: 只能是 contract, labor, marriage, debt, traffic, company, real_estate, criminal, other 之一
- summary: 300字以内案件摘要
- facts: 已掌握事实数组
- evidence: 证据或附件数组
- uncertainties: 仍需追问或核验的不确定点数组
- suggested_tasks: 后续办理任务数组

联系人：{contact.display_name if contact else "微信用户"}
聊天记录：
{transcript[:12000]}
"""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是律所案件接待助手，负责把客户微信咨询整理为结构化案件建档信息。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    request = Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=25) as response:
            body = response.read().decode("utf-8")
    except (OSError, URLError, TimeoutError):
        return fallback
    parsed_response = extract_json_object(body)
    choices = parsed_response.get("choices") if parsed_response else None
    content = ""
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(message, dict):
            content = str(message.get("content") or "")
    raw_analysis = extract_json_object(content)
    if raw_analysis is None:
        return fallback
    return normalize_case_analysis(raw_analysis, fallback)


def latest_document_revision(document_id: str) -> LegalDocumentRevision | None:
    revisions = sorted(
        store.filter("legal_document_revisions", LegalDocumentRevision, document_id=document_id),
        key=lambda item: item.version_number,
    )
    return revisions[-1] if revisions else None


def build_docx_stream(title: str, content: str) -> BytesIO:
    document = DocxDocument()
    document.add_heading(title, level=1)
    for block in content.split("\n"):
        line = block.strip()
        if not line:
            continue
        if line.endswith("：") and len(line) <= 24:
            document.add_heading(line[:-1], level=2)
        else:
            document.add_paragraph(line)
    stream = BytesIO()
    document.save(stream)
    stream.seek(0)
    return stream


def create_text_document(
    *,
    case_id: str | None,
    title: str,
    document_type: str,
    content_text: str,
    source_filename: str | None = None,
    change_summary: str = "",
    author_type: str = "agent",
) -> LegalDocument:
    normalized_type = document_type if document_type in {"contract", "letter", "pleading", "evidence", "other"} else "other"
    document = LegalDocument(case_id=case_id, title=title, document_type=normalized_type)  # type: ignore[arg-type]
    revision = LegalDocumentRevision(
        document_id=document.id,
        version_number=1,
        content_text=content_text,
        source_filename=source_filename,
        author_type=author_type,  # type: ignore[arg-type]
        change_summary=change_summary,
    )
    document.current_revision_id = revision.id
    store.add("legal_documents", document)
    store.add("legal_document_revisions", revision)
    return document


def case_memories(case_id: str) -> list[CaseMemory]:
    return sorted(
        store.filter("case_memories", CaseMemory, case_id=case_id),
        key=lambda item: item.created_at,
    )


def case_documents(case_id: str) -> list[LegalDocument]:
    return sorted(
        store.filter("legal_documents", LegalDocument, case_id=case_id),
        key=lambda item: item.updated_at,
        reverse=True,
    )


def case_messages(case: Case) -> list[WechatMessage]:
    if not case.conversation_ref:
        return []
    return sorted(
        store.filter("wechat_messages", WechatMessage, conversation_id=case.conversation_ref),
        key=lambda item: item.created_at,
    )


def infer_case_summary(case: Case, memories: list[CaseMemory], messages: list[WechatMessage]) -> str:
    if case.summary.strip():
        return case.summary.strip()
    if memories:
        return "；".join(memory.content for memory in memories[:3])
    inbound = [message.content for message in messages if message.direction == "inbound"]
    return first_sentence(" ".join(inbound), "该案件仍处于信息收集阶段。")


def build_short_reply(case: Case, payload: ReplyJobCreateRequest, memories: list[CaseMemory]) -> str:
    facts = [memory.content for memory in memories if memory.kind in {"fact", "timeline", "evidence"}][:2]
    missing = [memory.content for memory in memories if memory.kind == "uncertainty"][:2]
    fact_text = "；".join(facts) if facts else "目前信息还不足，需要先补齐关键事实。"
    missing_text = "；".join(missing) if missing else "建议继续补充时间节点、证据材料和您的处理目标。"
    question = payload.user_question.strip() or "您提交的咨询问题"
    return (
        f"关于“{question[:80]}”，我先按{case_type_label(case.case_type)}方向为您做初步梳理："
        f"{fact_text} "
        f"下一步请优先补充：{missing_text} "
        "在材料完整前，当前意见仅作为初步判断，正式处理建议经过人工复核。"
    )


def build_long_reply_content(
    case: Case,
    job: LegalReplyJob,
    memories: list[CaseMemory],
    documents: list[LegalDocument],
    latest_run: LegalReasoningRun | None,
) -> str:
    facts = [memory.content for memory in memories if memory.kind in {"fact", "timeline", "evidence"}]
    uncertainties = [memory.content for memory in memories if memory.kind == "uncertainty"]
    document_lines = []
    for document in documents[:5]:
        revision = latest_document_revision(document.id)
        hint = revision.change_summary if revision else "暂无版本摘要"
        document_lines.append(f"- {document.title}：{hint}")
    followups = latest_run.follow_up_questions if latest_run else []
    facts_text = "\n".join(f"- {item}" for item in facts) or "- 暂无已确认事实，建议先完成事实访谈。"
    uncertainty_text = "\n".join(f"- {item}" for item in uncertainties) or "- 暂未登记重大不确定点。"
    document_text = "\n".join(document_lines) or "- 暂无案件文件。"
    followup_text = "\n".join(f"- {item}" for item in followups[:5]) or "- 请补充关键时间节点、证据材料和处理目标。"
    return f"""法律意见摘要：
案件名称：{case.title}
案件类型：{case_type_label(case.case_type)}
任务标题：{job.title}

一、案件摘要：
{job.case_summary or infer_case_summary(case, memories, case_messages(case))}

二、已掌握事实与证据：
{facts_text}

三、关联文件：
{document_text}

四、初步法律分析：
{case_rule_hint(case.case_type)}
结合现有材料，当前更适合形成阶段性意见，而非直接输出最终结论。需要把事实、证据和诉求目标对应到法律要件后，再决定协商、函件、投诉、仲裁或诉讼路径。

五、风险与不确定点：
{uncertainty_text}

六、建议追问/补充材料：
{followup_text}

七、人工复核提示：
本文件由系统根据案件记录生成，应由律师或办案人员复核事实来源、法律依据、证据完整性和表述边界后再对外使用。
"""


def build_agent_architecture() -> AgentArchitecture:
    agents = store.list("legal_agents", LegalAgent)
    by_role = {agent.role: agent for agent in agents}
    dispatcher = by_role.get("dispatch_agent") or by_role.get("managing_lawyer")
    if not dispatcher:
        raise HTTPException(status_code=500, detail="Agent architecture is not initialized")
    return AgentArchitecture(
        dispatcher=dispatcher,
        groups=[
            AgentGroup(
                id="core_business",
                title="核心业务 Agent",
                description="承接专业法律判断、深度推理和文书交付。",
                agent_roles=[
                    "core_business_agent",
                    "managing_lawyer",
                    "handling_lawyer",
                    "litigation_strategist",
                    "legal_researcher",
                    "drafting_lawyer",
                ],
                departments=CORE_DEPARTMENTS,
            ),
            AgentGroup(
                id="client_service",
                title="客户服务 Agent",
                description="负责法律咨询、接案报价、投诉处理和客户沟通节奏。",
                agent_roles=["client_service_agent", "reception_lawyer"],
                departments=CLIENT_SERVICE_DEPARTMENTS,
            ),
            AgentGroup(
                id="compliance_review",
                title="合规审查 Agent",
                description="负责收案审批、利益冲突审查、风险评估和人工复核点。",
                agent_roles=["compliance_review_agent", "quality_control", "contract_reviewer"],
                departments=COMPLIANCE_REVIEW_DEPARTMENTS,
            ),
            AgentGroup(
                id="archive_management",
                title="档案管理 Agent",
                description="负责案卷归档、档案查询、证据目录、文件版本和过程留痕。",
                agent_roles=["archive_management_agent", "case_secretary"],
                departments=ARCHIVE_MANAGEMENT_DEPARTMENTS,
            ),
        ],
    )


@app.get("/api/health")
async def health() -> dict[str, object]:
    return {"ok": True, "service": "lvzhijie-backend"}


@app.get("/api/dashboard/summary")
async def dashboard_summary() -> dict[str, object]:
    cases = store.list("cases", Case)
    conversations = store.list("wechat_conversations", WechatConversation)
    messages = store.list("wechat_messages", WechatMessage)
    documents = store.list("legal_documents", LegalDocument)
    runs = store.list("legal_reasoning_runs", LegalReasoningRun)
    reply_jobs = store.list("reply_jobs", LegalReplyJob)
    return {
        "cases": len(cases),
        "open_cases": len([case for case in cases if case.status != "closed"]),
        "conversations": len(conversations),
        "unread": sum(item.unread_count for item in conversations),
        "messages": len(messages),
        "documents": len(documents),
        "reasoning_runs": len(runs),
        "reply_jobs": len(reply_jobs),
        "queued_reply_jobs": len([job for job in reply_jobs if job.status in {"queued", "reasoning"}]),
        "openclaw": (await OpenClawWechatAdapter(connection()).get_status()).model_dump(),
    }


@app.get("/api/activity")
async def list_activity() -> list[ActivityEvent]:
    return sorted(
        store.list("activity_events", ActivityEvent),
        key=lambda item: item.created_at,
        reverse=True,
    )


@app.get("/api/openclaw/connection")
async def get_openclaw_connection() -> OpenClawConnection:
    return connection()


@app.put("/api/openclaw/connection")
async def update_openclaw_connection(payload: OpenClawConnection) -> OpenClawConnection:
    payload.last_checked_at = now_iso()
    store.upsert_single("openclaw_connection", payload)
    record("openclaw.connection.updated", "更新 OpenClaw 微信通道配置")
    return payload


@app.get("/api/openclaw/status")
async def openclaw_status() -> dict[str, object]:
    status = await OpenClawWechatAdapter(connection()).get_status()
    updated = connection()
    updated.last_checked_at = status.checked_at
    store.upsert_single("openclaw_connection", updated)
    return status.model_dump()


@app.post("/api/openclaw/sync")
async def sync_openclaw_messages() -> dict[str, object]:
    if using_mock_wechat():
        mock_wechat.sync_to_json_store(store)
        conversations = mock_wechat.list_conversations()
        total_messages = sum(
            len(mock_wechat.list_messages(c["id"])) for c in conversations
        )
        return {
            "ok": True,
            "sessions": len(conversations),
            "messages": total_messages,
            "errors": [],
            "last_sync_at": now_iso(),
        }

    adapter = OpenClawWechatAdapter(connection())
    synced_sessions = 0
    synced_messages = 0
    errors: list[str] = []
    try:
        sessions = await adapter.list_sessions()
    except Exception as exc:  # noqa: BLE001 - sync should report, not crash the workspace
        errors.append(str(exc))
        sessions = []

    contacts = store.list("wechat_contacts", WechatContact)
    conversations = store.list("wechat_conversations", WechatConversation)
    messages = store.list("wechat_messages", WechatMessage)
    contacts_by_openclaw = {item.openclaw_contact_id: item for item in contacts}
    conversations_by_openclaw = {item.openclaw_conversation_id: item for item in conversations}
    existing_message_keys = {
        _message_dedupe_key(message)
        for message in messages
    }

    for raw_session in sessions:
        session_key = adapter.session_key(raw_session)
        label = adapter.session_label(raw_session)
        contact = contacts_by_openclaw.get(session_key)
        if contact is None:
            contact = WechatContact(
                openclaw_contact_id=session_key,
                display_name=label,
                remark="OpenClaw 微信会话",
                last_seen_at=now_iso(),
            )
            store.add("wechat_contacts", contact)
            contacts_by_openclaw[session_key] = contact
        else:
            contact.display_name = label or contact.display_name
            contact.last_seen_at = now_iso()
            store.update("wechat_contacts", contact)

        conversation = conversations_by_openclaw.get(session_key)
        if conversation is None:
            conversation = WechatConversation(
                openclaw_conversation_id=session_key,
                contact_id=contact.id,
                status="open",
                auto_reply_source="openclaw",
            )
            store.add("wechat_conversations", conversation)
            conversations_by_openclaw[session_key] = conversation
        synced_sessions += 1

        try:
            history = await adapter.get_session_history(session_key)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{session_key}: {exc}")
            continue
        for raw_message in history:
            normalized = adapter.normalize_history_message(
                raw_message,
                conversation_id=conversation.id,
            )
            key = _message_dedupe_key(normalized)
            if key in existing_message_keys or not normalized.content.strip():
                continue
            store.add("wechat_messages", normalized)
            existing_message_keys.add(key)
            synced_messages += 1
            conversation.last_message_at = normalized.created_at
        store.update("wechat_conversations", conversation)

    updated = connection()
    updated.last_sync_at = now_iso()
    store.upsert_single("openclaw_connection", updated)
    record(
        "wechat.sync",
        "同步 OpenClaw 微信聊天记录",
        f"会话 {synced_sessions} 个，消息 {synced_messages} 条。",
    )
    return {
        "ok": not errors,
        "sessions": synced_sessions,
        "messages": synced_messages,
        "errors": errors,
        "last_sync_at": updated.last_sync_at,
    }


@app.get("/api/openclaw/sessions")
async def list_openclaw_sessions() -> dict[str, object]:
    adapter = OpenClawWechatAdapter(connection())
    try:
        sessions = await adapter.list_sessions()
        return {"ok": True, "sessions": sessions}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "sessions": [], "error": str(exc)}


@app.get("/api/wechat/conversations")
async def list_wechat_conversations() -> list[dict[str, object]]:
    sync_mock_wechat_if_needed()
    contacts = {item.id: item for item in store.list("wechat_contacts", WechatContact)}
    conversations = store.list("wechat_conversations", WechatConversation)
    return [
        {
            **conversation.model_dump(),
            "contact": contacts.get(conversation.contact_id).model_dump()
            if contacts.get(conversation.contact_id)
            else None,
        }
        for conversation in sorted(
            conversations,
            key=lambda item: item.last_message_at or "",
            reverse=True,
        )
    ]


@app.get("/api/wechat/conversations/{conversation_id}/messages")
async def get_wechat_messages(conversation_id: str) -> list[WechatMessage]:
    sync_mock_wechat_if_needed()
    return sorted(
        store.filter("wechat_messages", WechatMessage, conversation_id=conversation_id),
        key=lambda item: item.created_at,
    )


@app.delete("/api/wechat/conversations/{conversation_id}")
async def delete_wechat_conversation(conversation_id: str) -> dict[str, object]:
    sync_mock_wechat_if_needed()
    conversation = store.get("wechat_conversations", conversation_id, WechatConversation)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if using_mock_wechat():
        mock_wechat.delete_conversation(conversation_id)
    result = delete_wechat_conversation_rows(conversation)
    record(
        "wechat.conversation.deleted",
        "删除微信会话",
        conversation.openclaw_conversation_id,
        entity_type="conversation",
        entity_id=conversation_id,
    )
    return {"ok": True, **result}


@app.post("/api/wechat/conversations/{conversation_id}/send")
async def send_wechat_message(conversation_id: str, payload: SendMessageRequest) -> WechatMessage:
    conversation = store.get("wechat_conversations", conversation_id, WechatConversation)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if using_mock_wechat():
        new_msg = mock_wechat.append_message(
            conversation_id=conversation_id,
            sender="owner",
            content=payload.content,
        )
        message = WechatMessage.model_validate(new_msg)
        mock_wechat.sync_to_json_store(store)
        record(
            "wechat.sent_mock",
            "通过演示模式发送微信消息",
            payload.content[:120],
            entity_type="conversation",
            entity_id=conversation_id,
        )
        return message
    message = await OpenClawWechatAdapter(connection()).send_wechat_message(
        conversation_id=conversation.openclaw_conversation_id,
        content=payload.content,
    )
    message.conversation_id = conversation_id
    conversation.last_message_at = message.created_at
    store.add("wechat_messages", message)
    store.update("wechat_conversations", conversation)
    record(
        "wechat.sent_via_openclaw",
        "通过 OpenClaw 发送微信消息",
        payload.content[:120],
        entity_type="conversation",
        entity_id=conversation_id,
    )
    return message


def _message_dedupe_key(message: WechatMessage) -> str:
    if message.openclaw_message_id:
        return f"oc:{message.conversation_id}:{message.openclaw_message_id}"
    return (
        f"fp:{message.conversation_id}:{message.sender}:"
        f"{message.created_at}:{message.content[:160]}"
    )


@app.post("/api/wechat/conversations/{conversation_id}/case")
async def create_case_from_conversation(
    conversation_id: str,
    payload: CreateCaseFromConversationRequest,
) -> Case:
    sync_mock_wechat_if_needed()
    conversation = store.get("wechat_conversations", conversation_id, WechatConversation)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.case_id:
        existing_case = store.get("cases", conversation.case_id, Case)
        if existing_case:
            return existing_case
    contact = store.get("wechat_contacts", conversation.contact_id, WechatContact)
    messages = sorted(
        store.filter("wechat_messages", WechatMessage, conversation_id=conversation_id),
        key=lambda item: item.created_at,
    )
    analysis = await analyze_conversation_for_case(
        contact=contact,
        messages=messages,
        requested_title=payload.title,
        requested_case_type=payload.case_type if payload.case_type != "other" else None,
    )
    case = Case(
        title=str(analysis["title"]),
        case_type=analysis["case_type"],  # type: ignore[arg-type]
        status="collecting_info",
        summary=str(analysis["summary"]),
        wechat_contact_ref=conversation.contact_id,
        conversation_ref=conversation.id,
    )
    conversation.case_id = case.id
    store.add("cases", case)
    store.update("wechat_conversations", conversation)
    if using_mock_wechat():
        mock_wechat.update_conversation(conversation.id, {"case_id": case.id})
    for content in analysis.get("facts", []):
        store.add(
            "case_memories",
            CaseMemory(case_id=case.id, kind="fact", content=str(content), source_ref=conversation.id),
        )
    for content in analysis.get("evidence", []):
        store.add(
            "case_memories",
            CaseMemory(case_id=case.id, kind="evidence", content=str(content), source_ref=conversation.id),
        )
    for content in analysis.get("uncertainties", []):
        store.add(
            "case_memories",
            CaseMemory(case_id=case.id, kind="uncertainty", content=str(content), source_ref=conversation.id),
        )
    for title in analysis.get("suggested_tasks", [])[:5]:
        store.add(
            "case_tasks",
            CaseTask(
                case_id=case.id,
                title=str(title),
                assigned_agent_role="案件秘书 Agent",
            ),
        )
    record("case.created", "从微信会话创建案件", case.title, entity_type="case", entity_id=case.id)
    return case


@app.post("/api/wechat/conversations/{conversation_id}/bind-case")
async def bind_conversation_to_case(
    conversation_id: str,
    payload: BindConversationCaseRequest,
) -> Case:
    sync_mock_wechat_if_needed()
    conversation = store.get("wechat_conversations", conversation_id, WechatConversation)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    case = store.get("cases", payload.case_id, Case)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    conversation.case_id = case.id
    case.conversation_ref = conversation.id
    case.wechat_contact_ref = conversation.contact_id
    case.updated_at = now_iso()
    store.update("wechat_conversations", conversation)
    store.update("cases", case)
    if using_mock_wechat():
        mock_wechat.update_conversation(conversation.id, {"case_id": case.id})
    record("case.bound_wechat", "绑定微信会话到案件", case.title, entity_type="case", entity_id=case.id)
    return case


@app.get("/api/cases")
async def list_cases() -> list[Case]:
    return sorted(store.list("cases", Case), key=lambda item: item.updated_at, reverse=True)


@app.post("/api/cases")
async def create_case(payload: CaseCreateRequest) -> Case:
    case = Case(**payload.model_dump())
    store.add("cases", case)
    record("case.created", "创建案件", case.title, entity_type="case", entity_id=case.id)
    return case


@app.get("/api/cases/{case_id}")
async def get_case(case_id: str) -> dict[str, object]:
    case = store.get("cases", case_id, Case)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return {
        "case": case,
        "tasks": store.filter("case_tasks", CaseTask, case_id=case_id),
        "memories": store.filter("case_memories", CaseMemory, case_id=case_id),
        "documents": store.filter("legal_documents", LegalDocument, case_id=case_id),
        "reasoning_runs": store.filter("legal_reasoning_runs", LegalReasoningRun, case_id=case_id),
        "follow_up_questions": store.filter("follow_up_questions", FollowUpQuestion, case_id=case_id),
        "reply_jobs": store.filter("reply_jobs", LegalReplyJob, case_id=case_id),
        "messages": store.filter("wechat_messages", WechatMessage, conversation_id=case.conversation_ref)
        if case.conversation_ref
        else [],
    }


@app.delete("/api/cases/{case_id}")
async def delete_case(case_id: str) -> dict[str, object]:
    case = store.get("cases", case_id, Case)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    for document in store.filter("legal_documents", LegalDocument, case_id=case_id):
        delete_document_rows(document.id)
    store.remove_where("case_tasks", lambda row: row.get("case_id") == case_id)
    store.remove_where("case_memories", lambda row: row.get("case_id") == case_id)
    store.remove_where("legal_reasoning_runs", lambda row: row.get("case_id") == case_id)
    store.remove_where("follow_up_questions", lambda row: row.get("case_id") == case_id)
    store.remove_where("reply_jobs", lambda row: row.get("case_id") == case_id)
    store.remove_where("activity_events", lambda row: row.get("entity_type") == "case" and row.get("entity_id") == case_id)

    for conversation in store.list("wechat_conversations", WechatConversation):
        if conversation.case_id == case_id:
            conversation.case_id = None
            store.update("wechat_conversations", conversation)

    store.delete("cases", case_id)
    record("case.deleted", "删除案件", case.title)
    return {"ok": True}


@app.post("/api/cases/{case_id}/tasks")
async def create_task(case_id: str, payload: TaskCreateRequest) -> CaseTask:
    if not store.get("cases", case_id, Case):
        raise HTTPException(status_code=404, detail="Case not found")
    task = CaseTask(case_id=case_id, **payload.model_dump())
    store.add("case_tasks", task)
    record("case.task.created", "创建案件任务", task.title, entity_type="case", entity_id=case_id)
    return task


@app.delete("/api/cases/{case_id}/tasks/{task_id}")
async def delete_task(case_id: str, task_id: str) -> dict[str, object]:
    task = store.get("case_tasks", task_id, CaseTask)
    if not task or task.case_id != case_id:
        raise HTTPException(status_code=404, detail="Task not found")
    store.delete("case_tasks", task_id)
    record("case.task.deleted", "删除案件任务", task.title, entity_type="case", entity_id=case_id)
    return {"ok": True}


@app.post("/api/cases/{case_id}/memories")
async def create_memory(case_id: str, payload: MemoryCreateRequest) -> CaseMemory:
    if not store.get("cases", case_id, Case):
        raise HTTPException(status_code=404, detail="Case not found")
    memory = CaseMemory(case_id=case_id, **payload.model_dump())
    store.add("case_memories", memory)
    record("case.memory.created", "写入案件记忆", memory.content[:120], entity_type="case", entity_id=case_id)
    return memory


@app.delete("/api/cases/{case_id}/memories/{memory_id}")
async def delete_memory(case_id: str, memory_id: str) -> dict[str, object]:
    memory = store.get("case_memories", memory_id, CaseMemory)
    if not memory or memory.case_id != case_id:
        raise HTTPException(status_code=404, detail="Memory not found")
    store.delete("case_memories", memory_id)
    record("case.memory.deleted", "删除案件记忆", memory.content[:120], entity_type="case", entity_id=case_id)
    return {"ok": True}


@app.get("/api/cases/{case_id}/reply-jobs")
async def list_reply_jobs(case_id: str) -> list[LegalReplyJob]:
    if not store.get("cases", case_id, Case):
        raise HTTPException(status_code=404, detail="Case not found")
    return sorted(
        store.filter("reply_jobs", LegalReplyJob, case_id=case_id),
        key=lambda item: item.created_at,
        reverse=True,
    )


@app.post("/api/cases/{case_id}/reply-jobs")
async def create_reply_job(case_id: str, payload: ReplyJobCreateRequest) -> LegalReplyJob:
    case = store.get("cases", case_id, Case)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    memories = case_memories(case_id)
    messages = case_messages(case)
    mode_label = "短回复" if payload.mode == "short_reply" else "长回复"
    title = payload.title or f"{case.title}{mode_label}任务"
    summary = payload.case_summary.strip() or infer_case_summary(case, memories, messages)
    job = LegalReplyJob(
        case_id=case_id,
        mode=payload.mode,
        title=title,
        case_summary=summary,
        user_question=payload.user_question.strip(),
        assigned_agent_role=payload.assigned_agent_role,
        status="ready_for_review" if payload.mode == "short_reply" else "queued",
        draft_text=build_short_reply(case, payload, memories) if payload.mode == "short_reply" else "",
    )
    store.add("reply_jobs", job)
    record("reply_job.created", "创建回复工作流任务", title, entity_type="case", entity_id=case_id)
    return job


@app.post("/api/cases/{case_id}/reply-jobs/{job_id}/process")
async def process_reply_job(case_id: str, job_id: str) -> LegalReplyJob:
    case = store.get("cases", case_id, Case)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    job = store.get("reply_jobs", job_id, LegalReplyJob)
    if not job or job.case_id != case_id:
        raise HTTPException(status_code=404, detail="Reply job not found")
    if job.mode == "short_reply":
        job.status = "ready_for_review"
        job.module_state = "idle"
        job.updated_at = now_iso()
        if not job.draft_text:
            job.draft_text = build_short_reply(case, ReplyJobCreateRequest.model_validate(job.model_dump()), case_memories(case_id))
        store.update("reply_jobs", job)
        return job

    job.status = "reasoning"
    job.module_state = "busy"
    job.updated_at = now_iso()
    store.update("reply_jobs", job)

    runs = sorted(
        store.filter("legal_reasoning_runs", LegalReasoningRun, case_id=case_id),
        key=lambda item: item.created_at,
    )
    latest_run = runs[-1] if runs else None
    content = build_long_reply_content(
        case,
        job,
        case_memories(case_id),
        case_documents(case_id),
        latest_run,
    )
    document = create_text_document(
        case_id=case_id,
        title=f"{job.title} Word 输出",
        document_type="letter",
        content_text=content,
        source_filename=f"{job.title}.docx",
        change_summary="回复工作流自动生成",
        author_type="agent",
    )
    job.status = "completed"
    job.module_state = "idle"
    job.draft_text = content
    job.output_document_id = document.id
    job.updated_at = now_iso()
    store.update("reply_jobs", job)
    record("reply_job.completed", "长回复推理完成并生成文书", job.title, entity_type="case", entity_id=case_id)
    return job


@app.delete("/api/cases/{case_id}/reply-jobs/{job_id}")
async def delete_reply_job(case_id: str, job_id: str) -> dict[str, object]:
    job = store.get("reply_jobs", job_id, LegalReplyJob)
    if not job or job.case_id != case_id:
        raise HTTPException(status_code=404, detail="Reply job not found")
    store.delete("reply_jobs", job_id)
    record("reply_job.deleted", "删除回复工作流任务", job.title, entity_type="case", entity_id=case_id)
    return {"ok": True}


@app.post("/api/cases/{case_id}/follow-up-questions")
async def create_follow_up_question(case_id: str, payload: SendMessageRequest) -> FollowUpQuestion:
    if not store.get("cases", case_id, Case):
        raise HTTPException(status_code=404, detail="Case not found")
    question = FollowUpQuestion(case_id=case_id, content=payload.content)
    store.add("follow_up_questions", question)
    record("follow_up.created", "创建追问问题", question.content[:120], entity_type="case", entity_id=case_id)
    return question


@app.delete("/api/cases/{case_id}/follow-up-questions/{question_id}")
async def delete_follow_up_question(case_id: str, question_id: str) -> dict[str, object]:
    question = store.get("follow_up_questions", question_id, FollowUpQuestion)
    if not question or question.case_id != case_id:
        raise HTTPException(status_code=404, detail="Follow-up question not found")
    store.delete("follow_up_questions", question_id)
    record("follow_up.deleted", "删除追问问题", question.content[:120], entity_type="case", entity_id=case_id)
    return {"ok": True}


@app.post("/api/cases/{case_id}/follow-up-questions/{question_id}/send")
async def send_follow_up_question(
    case_id: str,
    question_id: str,
    payload: SendFollowUpRequest | None = None,
) -> dict[str, object]:
    case = store.get("cases", case_id, Case)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not case.conversation_ref:
        raise HTTPException(status_code=422, detail="Case is not bound to a WeChat conversation")
    conversation = store.get("wechat_conversations", case.conversation_ref, WechatConversation)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    question = store.get("follow_up_questions", question_id, FollowUpQuestion)
    if not question or question.case_id != case_id:
        raise HTTPException(status_code=404, detail="Follow-up question not found")

    content = (payload.content if payload and payload.content else question.content).strip()
    if not content:
        raise HTTPException(status_code=422, detail="Follow-up content is empty")

    message = await OpenClawWechatAdapter(connection()).send_wechat_message(
        conversation_id=conversation.openclaw_conversation_id,
        content=content,
    )
    message.conversation_id = conversation.id
    store.add("wechat_messages", message)
    conversation.last_message_at = message.created_at
    store.update("wechat_conversations", conversation)

    question.content = content
    question.status = "sent_via_openclaw" if message.status == "sent_via_openclaw" else "failed"
    question.sent_message_id = message.id
    question.failure_reason = (
        str(message.raw_payload.get("error")) if message.raw_payload and message.raw_payload.get("error") else None
    )
    question.updated_at = now_iso()
    store.update("follow_up_questions", question)
    record(
        "follow_up.sent",
        "通过 OpenClaw 发送追问",
        content[:120],
        entity_type="case",
        entity_id=case_id,
    )
    return {"question": question, "message": message}


@app.delete("/api/reasoning/cases/{case_id}/runs/{run_id}")
async def delete_reasoning_run(case_id: str, run_id: str) -> dict[str, object]:
    run = store.get("legal_reasoning_runs", run_id, LegalReasoningRun)
    if not run or run.case_id != case_id:
        raise HTTPException(status_code=404, detail="Reasoning run not found")
    store.delete("legal_reasoning_runs", run_id)
    store.remove_where("follow_up_questions", lambda row: row.get("reasoning_run_id") == run_id)
    record("reasoning.deleted", "删除 AOE 推理图", run.input_summary[:120], entity_type="case", entity_id=case_id)
    return {"ok": True}


@app.get("/api/agents")
async def list_agents() -> list[LegalAgent]:
    return store.list("legal_agents", LegalAgent)


@app.get("/api/agents/architecture")
async def get_agent_architecture() -> AgentArchitecture:
    return build_agent_architecture()


@app.get("/api/documents")
async def list_documents(case_id: str | None = None) -> list[LegalDocument]:
    documents = store.list("legal_documents", LegalDocument)
    if case_id:
        documents = [item for item in documents if item.case_id == case_id]
    return sorted(documents, key=lambda item: item.updated_at, reverse=True)


@app.post("/api/documents")
async def create_document(payload: DocumentCreateRequest) -> LegalDocument:
    document = LegalDocument(
        case_id=payload.case_id,
        title=payload.title,
        document_type=payload.document_type,
    )
    revision = LegalDocumentRevision(
        document_id=document.id,
        version_number=1,
        content_text=payload.content_text,
        source_filename=payload.source_filename,
        change_summary=payload.change_summary,
    )
    document.current_revision_id = revision.id
    store.add("legal_documents", document)
    store.add("legal_document_revisions", revision)
    record("document.created", "创建法律文件", document.title, entity_type="document", entity_id=document.id)
    return document


@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    case_id: str | None = Form(default=None),
    document_type: str = Form(default="other"),
    change_summary: str = Form(default="Initial upload"),
) -> LegalDocument:
    content_text = await read_legal_file_text(file)
    filename = file.filename or "uploaded document"
    if not content_text.strip():
        raise HTTPException(status_code=422, detail="Uploaded document has no readable text")
    normalized_type = document_type if document_type in {"contract", "letter", "pleading", "evidence", "other"} else "other"
    document = LegalDocument(
        case_id=case_id or None,
        title=title or Path(filename).stem,
        document_type=normalized_type,  # type: ignore[arg-type]
    )
    revision = LegalDocumentRevision(
        document_id=document.id,
        version_number=1,
        content_text=content_text,
        source_filename=filename,
        author_type="import",
        change_summary=change_summary,
    )
    document.current_revision_id = revision.id
    store.add("legal_documents", document)
    store.add("legal_document_revisions", revision)
    record("document.uploaded", "上传法律文件", document.title, entity_type="document", entity_id=document.id)
    return document


@app.get("/api/documents/{document_id}")
async def get_document(document_id: str) -> dict[str, object]:
    document = store.get("legal_documents", document_id, LegalDocument)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    revisions = store.filter("legal_document_revisions", LegalDocumentRevision, document_id=document_id)
    return {"document": document, "revisions": sorted(revisions, key=lambda item: item.version_number)}


@app.get("/api/documents/{document_id}/export.docx")
async def export_document_docx(document_id: str) -> StreamingResponse:
    document = store.get("legal_documents", document_id, LegalDocument)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    revision = latest_document_revision(document_id)
    if not revision:
        raise HTTPException(status_code=404, detail="Document revision not found")
    stream = build_docx_stream(document.title, revision.content_text)
    filename = f"legal-document-{document.id}.docx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.delete("/api/documents/{document_id}")
async def delete_document(document_id: str) -> dict[str, object]:
    document = store.get("legal_documents", document_id, LegalDocument)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    delete_document_rows(document_id)
    record("document.deleted", "删除法律文件", document.title, entity_type="document", entity_id=document_id)
    return {"ok": True}


@app.post("/api/documents/{document_id}/revisions")
async def create_revision(document_id: str, payload: RevisionCreateRequest) -> LegalDocumentRevision:
    document = store.get("legal_documents", document_id, LegalDocument)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    revisions = store.filter("legal_document_revisions", LegalDocumentRevision, document_id=document_id)
    revision = LegalDocumentRevision(
        document_id=document_id,
        version_number=len(revisions) + 1,
        **payload.model_dump(),
    )
    document.current_revision_id = revision.id
    document.updated_at = now_iso()
    store.add("legal_document_revisions", revision)
    store.update("legal_documents", document)
    record("document.revision.created", "创建文件新版本", document.title, entity_type="document", entity_id=document.id)
    return revision


@app.delete("/api/documents/{document_id}/revisions/{revision_id}")
async def delete_revision(document_id: str, revision_id: str) -> dict[str, object]:
    document = store.get("legal_documents", document_id, LegalDocument)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    revision = store.get("legal_document_revisions", revision_id, LegalDocumentRevision)
    if not revision or revision.document_id != document_id:
        raise HTTPException(status_code=404, detail="Revision not found")

    store.delete("legal_document_revisions", revision_id)
    store.remove_where(
        "legal_document_diffs",
        lambda row: row.get("document_id") == document_id
        and (row.get("base_revision_id") == revision_id or row.get("target_revision_id") == revision_id),
    )

    revisions = sorted(
        store.filter("legal_document_revisions", LegalDocumentRevision, document_id=document_id),
        key=lambda item: item.version_number,
    )
    if not revisions:
        delete_document_rows(document_id)
        record("document.deleted", "删除法律文件", document.title, entity_type="document", entity_id=document_id)
        return {"ok": True, "deleted_document": True}

    for index, item in enumerate(revisions, start=1):
        if item.version_number != index:
            item.version_number = index
            store.update("legal_document_revisions", item)
    document.current_revision_id = revisions[-1].id
    document.updated_at = now_iso()
    store.update("legal_documents", document)
    record("document.revision.deleted", "删除文件版本", document.title, entity_type="document", entity_id=document_id)
    return {"ok": True, "deleted_document": False}


@app.post("/api/documents/{document_id}/revisions/upload")
async def upload_revision(
    document_id: str,
    file: UploadFile = File(...),
    change_summary: str = Form(default="Uploaded revision"),
) -> LegalDocumentRevision:
    document = store.get("legal_documents", document_id, LegalDocument)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    content_text = await read_legal_file_text(file)
    if not content_text.strip():
        raise HTTPException(status_code=422, detail="Uploaded revision has no readable text")
    revisions = store.filter("legal_document_revisions", LegalDocumentRevision, document_id=document_id)
    revision = LegalDocumentRevision(
        document_id=document_id,
        version_number=len(revisions) + 1,
        content_text=content_text,
        source_filename=file.filename,
        author_type="import",
        change_summary=change_summary,
    )
    document.current_revision_id = revision.id
    document.updated_at = now_iso()
    store.add("legal_document_revisions", revision)
    store.update("legal_documents", document)
    record("document.revision.uploaded", "上传文件新版本", document.title, entity_type="document", entity_id=document.id)
    return revision


@app.get("/api/documents/{document_id}/diff")
async def get_document_diff(
    document_id: str,
    base_revision_id: str | None = Query(default=None),
    target_revision_id: str | None = Query(default=None),
) -> LegalDocumentDiff:
    document = store.get("legal_documents", document_id, LegalDocument)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    revisions = sorted(
        store.filter("legal_document_revisions", LegalDocumentRevision, document_id=document_id),
        key=lambda item: item.version_number,
    )
    if len(revisions) < 2 and not (base_revision_id and target_revision_id):
        raise HTTPException(status_code=422, detail="At least two revisions are required")
    base = store.get("legal_document_revisions", base_revision_id, LegalDocumentRevision) if base_revision_id else revisions[-2]
    target = (
        store.get("legal_document_revisions", target_revision_id, LegalDocumentRevision)
        if target_revision_id
        else revisions[-1]
    )
    if not base or not target:
        raise HTTPException(status_code=404, detail="Revision not found")
    diff = LegalDocumentDiff(
        document_id=document.id,
        base_revision_id=base.id,
        target_revision_id=target.id,
        segments=build_char_diff(base.content_text, target.content_text),
        paragraph_changes=build_paragraph_diff(base.content_text, target.content_text),
        risk_summary=summarize_legal_risks(base.content_text, target.content_text),
    )
    existing = store.filter(
        "legal_document_diffs",
        LegalDocumentDiff,
        document_id=document.id,
        base_revision_id=base.id,
        target_revision_id=target.id,
    )
    if existing:
        return existing[-1]
    store.add("legal_document_diffs", diff)
    return diff


@app.post("/api/reasoning/cases/{case_id}/generate")
async def generate_reasoning(case_id: str) -> LegalReasoningRun:
    case = store.get("cases", case_id, Case)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    memories = case_memories(case_id)
    messages = case_messages(case)
    documents = case_documents(case_id)
    summary = infer_case_summary(case, memories, messages)

    factual_memories = [memory for memory in memories if memory.kind in {"fact", "timeline", "evidence"}]
    uncertainty_memories = [memory for memory in memories if memory.kind == "uncertainty"]
    inbound_messages = [message for message in messages if message.direction == "inbound"]
    nodes: list[ReasoningNode] = []
    edges: list[ReasoningEdge] = []

    source_nodes: list[ReasoningNode] = []
    if factual_memories:
        for index, memory in enumerate(factual_memories[:4], start=1):
            node_type = "Timeline" if memory.kind == "timeline" else "Evidence" if memory.kind == "evidence" else "Fact"
            node = ReasoningNode(
                node_type=node_type,
                label=f"{'时间线' if node_type == 'Timeline' else '证据' if node_type == 'Evidence' else '事实'} {index}",
                content=memory.content,
                confidence=memory.confidence,
                source_refs=[memory.source_ref] if memory.source_ref else [],
            )
            nodes.append(node)
            source_nodes.append(node)
    elif inbound_messages:
        node = ReasoningNode(
            node_type="Fact",
            label="咨询事实",
            content=first_sentence(inbound_messages[0].content, summary),
            confidence=0.58,
            source_refs=[inbound_messages[0].id],
        )
        nodes.append(node)
        source_nodes.append(node)
    else:
        node = ReasoningNode(node_type="Fact", label="案件摘要", content=summary, confidence=0.5)
        nodes.append(node)
        source_nodes.append(node)

    if documents:
        document_node = ReasoningNode(
            node_type="Evidence",
            label="案件文件",
            content="；".join(f"{document.title}（{document.document_type}）" for document in documents[:4]),
            confidence=0.7,
            source_refs=[document.id for document in documents[:4]],
        )
        nodes.append(document_node)
        source_nodes.append(document_node)

    issue = ReasoningNode(
        node_type="Issue",
        label=f"{case_type_label(case.case_type)}争议焦点",
        content=f"需要判断本案在{case_type_label(case.case_type)}框架下的请求基础、关键事实和证明责任。",
        confidence=0.68,
    )
    rule = ReasoningNode(
        node_type="Rule",
        label="法律要件",
        content=case_rule_hint(case.case_type),
        confidence=0.64,
    )
    analysis = ReasoningNode(
        node_type="Analysis",
        label="阶段分析",
        content=f"当前摘要：{summary} 现阶段应先核对事实与证据，再形成可对外使用的法律意见。",
        confidence=0.66,
    )
    conclusion = ReasoningNode(
        node_type="Conclusion",
        label="阶段结论",
        content="可以形成内部阶段性判断；如关键证据未补齐，应先追问并人工复核后再输出正式结论。",
        confidence=0.6,
    )
    nodes.extend([issue, rule, analysis, conclusion])

    for source in source_nodes:
        edges.append(ReasoningEdge(source=source.id, target=issue.id, relation_type="supports"))
    edges.extend(
        [
            ReasoningEdge(source=issue.id, target=rule.id, relation_type="requires"),
            ReasoningEdge(source=rule.id, target=analysis.id, relation_type="supports"),
            ReasoningEdge(source=analysis.id, target=conclusion.id, relation_type="leads_to"),
        ]
    )

    missing_points = [memory.content for memory in uncertainty_memories]
    if not documents:
        missing_points.append("尚未上传可核对的合同、证据或案件材料。")
    if not any(memory.kind == "timeline" for memory in memories):
        missing_points.append("尚未形成完整时间线。")
    if not missing_points:
        missing_points.append("需由人工复核事实来源与对外表述边界。")

    uncertainty_node = ReasoningNode(
        node_type="Uncertainty",
        label="推理暂停点",
        content="；".join(missing_points[:3]),
        confidence=0.88,
    )
    nodes.append(uncertainty_node)
    edges.append(ReasoningEdge(source=analysis.id, target=uncertainty_node.id, relation_type="uncertain_about"))

    follow_up_questions = [
        "请补充关键时间节点，并按发生顺序说明每一步沟通或履行情况。",
        "请列明目前已有证据材料，包括合同、聊天记录、转账/工资流水、通知文件或其他书面材料。",
        "请确认您的目标是协商解决、发送函件、投诉举报，还是准备仲裁/诉讼。",
    ]
    if case.case_type == "labor":
        follow_up_questions.insert(1, "请补充入职时间、劳动合同签订情况、工资标准、欠薪月份和离职沟通证据。")
    elif case.case_type == "criminal":
        follow_up_questions.insert(1, "请补充涉案行为发生时间、地点、参与人员、目前程序阶段和已取得的法律文书。")
    elif case.case_type == "contract":
        follow_up_questions.insert(1, "请补充合同签订时间、履行节点、违约事实、催告记录和争议条款。")

    question_node = ReasoningNode(
        node_type="Question",
        label="下一轮追问",
        content="；".join(follow_up_questions[:4]),
        confidence=0.92,
    )
    nodes.append(question_node)
    edges.append(ReasoningEdge(source=uncertainty_node.id, target=question_node.id, relation_type="asks"))

    needs_evidence = bool(missing_points and missing_points[0] != "需由人工复核事实来源与对外表述边界。")
    run = LegalReasoningRun(
        case_id=case_id,
        status="needs_evidence" if needs_evidence else "ready_for_review",
        input_summary=summary,
        nodes=nodes,
        edges=edges,
        follow_up_questions=follow_up_questions,
        blocked_reason="；".join(missing_points[:3]) if needs_evidence else "",
        review_focus=["事实来源", "证据完整性", "法律依据", "对外表述边界"],
        output_summary=f"已生成{len(nodes)}个节点、{len(edges)}条关系，建议先处理追问后再输出正式意见。",
    )
    store.add("legal_reasoning_runs", run)
    for content in follow_up_questions:
        store.add(
            "follow_up_questions",
            FollowUpQuestion(case_id=case_id, reasoning_run_id=run.id, content=content),
        )
    record("reasoning.generated", "生成 AOE 推理图", case.title, entity_type="case", entity_id=case_id)
    return run


@app.get("/api/mock-wechat/conversations")
async def list_mock_conversations() -> list[dict[str, object]]:
    return mock_wechat.list_conversations()


@app.post("/api/mock-wechat/conversations")
async def create_mock_conversation(payload: MockConversationCreateRequest) -> dict[str, object]:
    return mock_wechat.create_conversation(
        display_name=payload.display_name,
        remark=payload.remark,
        avatar_url=payload.avatar_url,
    )


@app.put("/api/mock-wechat/conversations/{conversation_id}")
async def update_mock_conversation(
    conversation_id: str, payload: MockConversationUpdateRequest
) -> dict[str, object]:
    raw = {k: v for k, v in payload.model_dump().items() if v is not None}
    contact_fields = {}
    update_data: dict[str, object] = {}
    for key, value in raw.items():
        if key in {"display_name", "remark", "avatar_url"}:
            contact_fields[key] = value
        else:
            update_data[key] = value
    if contact_fields:
        update_data["contact"] = contact_fields
    result = mock_wechat.update_conversation(conversation_id, update_data)
    if result is None:
        raise HTTPException(status_code=404, detail="Mock conversation not found")
    return result


@app.delete("/api/mock-wechat/conversations/{conversation_id}")
async def delete_mock_conversation(conversation_id: str) -> dict[str, object]:
    conversation = store.get("wechat_conversations", conversation_id, WechatConversation)
    if not mock_wechat.delete_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Mock conversation not found")
    if conversation:
        delete_wechat_conversation_rows(conversation)
    return {"ok": True}


@app.get("/api/mock-wechat/conversations/{conversation_id}/messages")
async def list_mock_messages(conversation_id: str) -> list[dict[str, object]]:
    return mock_wechat.list_messages(conversation_id)


@app.post("/api/mock-wechat/conversations/{conversation_id}/messages")
async def create_mock_message(
    conversation_id: str,
    sender: str = Form(...),
    content: str = Form(default=""),
    files: list[UploadFile] | None = File(default=None),
) -> dict[str, object]:
    if sender not in {"wechat_user", "owner"}:
        raise HTTPException(status_code=422, detail="sender must be wechat_user or owner")
    uploads = files or []
    if not content.strip() and not uploads:
        raise HTTPException(status_code=422, detail="Message content or files are required")
    attachments = []
    for upload in uploads:
        attachment = await mock_wechat.save_upload(upload)
        attachments.append(attachment)
    new_msg = mock_wechat.append_message(
        conversation_id=conversation_id,
        sender=sender,
        content=content,
        attachments=attachments,
    )
    mock_wechat.sync_to_json_store(store)
    return new_msg


@app.delete("/api/mock-wechat/conversations/{conversation_id}/messages/{message_id}")
async def delete_mock_message(conversation_id: str, message_id: str) -> dict[str, object]:
    if not mock_wechat.delete_message(conversation_id, message_id):
        raise HTTPException(status_code=404, detail="Mock message not found")
    return {"ok": True}
