from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class OpenClawConnection(BaseModel):
    id: str = "local_openclaw"
    name: str = "本机 OpenClaw"
    gateway_url: str = "ws://localhost:18789"
    gateway_token: str | None = None
    workspace_root: str = "~/.openclaw"
    transport_mode: Literal["gateway_rpc", "mock"] = "gateway_rpc"
    gateway_protocol_version: int = 0
    allow_insecure_tls: bool = False
    disable_device_pairing: bool = False
    wechat_session_filter: str = ""
    list_method: str = "sessions.list"
    history_method: str = "chat.history"
    send_method: str = "chat.send"
    history_limit: int = 80
    enabled: bool = True
    last_checked_at: str | None = None
    last_sync_at: str | None = None


class OpenClawStatus(BaseModel):
    online: bool
    plugin: str = "wechat"
    mode: str = "wechat_transport_only"
    message: str
    checked_at: str
    transport_mode: str = "gateway_rpc"
    sessions_count: int | None = None
    error: str | None = None


class WechatContact(BaseModel):
    id: str = Field(default_factory=lambda: new_id("contact"))
    openclaw_contact_id: str
    display_name: str
    remark: str | None = None
    avatar_url: str | None = None
    last_seen_at: str | None = None


class WechatConversation(BaseModel):
    id: str = Field(default_factory=lambda: new_id("conv"))
    openclaw_conversation_id: str
    contact_id: str
    case_id: str | None = None
    status: Literal["open", "waiting_owner", "closed"] = "open"
    auto_reply_source: Literal["openclaw", "disabled"] = "openclaw"
    last_message_at: str | None = None
    unread_count: int = 0


class WechatMessage(BaseModel):
    id: str = Field(default_factory=lambda: new_id("msg"))
    conversation_id: str
    sender: Literal["wechat_user", "openclaw_auto", "owner", "system"]
    direction: Literal["inbound", "outbound", "internal"]
    content: str
    status: Literal[
        "synced",
        "openclaw_auto_replied",
        "draft",
        "sent_via_openclaw",
        "failed",
        "ignored",
    ] = "synced"
    openclaw_message_id: str | None = None
    created_at: str = Field(default_factory=now_iso)
    raw_payload: dict[str, Any] | None = None


class Case(BaseModel):
    id: str = Field(default_factory=lambda: new_id("case"))
    title: str
    case_type: Literal[
        "contract",
        "labor",
        "marriage",
        "debt",
        "traffic",
        "company",
        "real_estate",
        "criminal",
        "other",
    ] = "other"
    status: Literal[
        "new",
        "collecting_info",
        "analyzing",
        "waiting_user",
        "waiting_owner_review",
        "replied",
        "closed",
    ] = "new"
    summary: str = ""
    wechat_contact_ref: str | None = None
    conversation_ref: str | None = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class CaseTask(BaseModel):
    id: str = Field(default_factory=lambda: new_id("task"))
    case_id: str
    title: str
    description: str = ""
    status: Literal[
        "todo",
        "in_progress",
        "waiting_user",
        "waiting_owner_review",
        "done",
        "blocked",
    ] = "todo"
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    assigned_agent_role: str | None = None
    result_summary: str = ""
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class CaseMemory(BaseModel):
    id: str = Field(default_factory=lambda: new_id("memory"))
    case_id: str
    kind: Literal["fact", "timeline", "evidence", "uncertainty", "note"]
    content: str
    confidence: float = 0.8
    source_ref: str | None = None
    confirmed: bool = False
    created_at: str = Field(default_factory=now_iso)


class LegalAgent(BaseModel):
    id: str = Field(default_factory=lambda: new_id("agent"))
    role: str
    title: str
    description: str
    responsibilities: list[str]
    group: str = "specialist"
    reports_to: str | None = None
    active: bool = True


class AgentDepartment(BaseModel):
    id: str
    title: str
    description: str
    case_types: list[str] = Field(default_factory=list)
    active: bool = True


class AgentGroup(BaseModel):
    id: str
    title: str
    description: str
    agent_roles: list[str] = Field(default_factory=list)
    departments: list[AgentDepartment] = Field(default_factory=list)


class AgentArchitecture(BaseModel):
    dispatcher: LegalAgent
    groups: list[AgentGroup]


class LegalDocument(BaseModel):
    id: str = Field(default_factory=lambda: new_id("doc"))
    case_id: str | None = None
    title: str
    document_type: Literal["contract", "letter", "pleading", "evidence", "other"] = "other"
    current_revision_id: str | None = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class LegalDocumentRevision(BaseModel):
    id: str = Field(default_factory=lambda: new_id("rev"))
    document_id: str
    version_number: int
    content_text: str
    source_filename: str | None = None
    author_type: Literal["owner", "agent", "import"] = "owner"
    change_summary: str = ""
    created_at: str = Field(default_factory=now_iso)


class DiffSegment(BaseModel):
    op: Literal["equal", "insert", "delete", "replace"]
    text: str


class ParagraphChange(BaseModel):
    op: Literal["equal", "insert", "delete", "replace"]
    base: str = ""
    target: str = ""


class LegalDocumentDiff(BaseModel):
    id: str = Field(default_factory=lambda: new_id("diff"))
    document_id: str
    base_revision_id: str
    target_revision_id: str
    segments: list[DiffSegment]
    paragraph_changes: list[ParagraphChange]
    risk_summary: list[str]
    created_at: str = Field(default_factory=now_iso)


class ReasoningNode(BaseModel):
    id: str = Field(default_factory=lambda: new_id("node"))
    node_type: Literal[
        "Fact",
        "Evidence",
        "Timeline",
        "Issue",
        "Rule",
        "Analysis",
        "Conclusion",
        "Uncertainty",
        "Question",
    ]
    label: str
    content: str
    confidence: float = 0.8
    source_refs: list[str] = Field(default_factory=list)


class ReasoningEdge(BaseModel):
    id: str = Field(default_factory=lambda: new_id("edge"))
    source: str
    target: str
    relation_type: Literal[
        "supports",
        "contradicts",
        "requires",
        "leads_to",
        "depends_on",
        "uncertain_about",
        "asks",
    ]


class LegalReasoningRun(BaseModel):
    id: str = Field(default_factory=lambda: new_id("reason"))
    case_id: str
    status: Literal["draft", "needs_evidence", "ready_for_review", "confirmed"] = "ready_for_review"
    input_summary: str
    nodes: list[ReasoningNode]
    edges: list[ReasoningEdge]
    follow_up_questions: list[str]
    blocked_reason: str = ""
    review_focus: list[str] = Field(default_factory=list)
    output_summary: str = ""
    created_at: str = Field(default_factory=now_iso)


class FollowUpQuestion(BaseModel):
    id: str = Field(default_factory=lambda: new_id("followup"))
    case_id: str
    reasoning_run_id: str | None = None
    content: str
    status: Literal["draft", "sent_via_openclaw", "failed", "ignored"] = "draft"
    sent_message_id: str | None = None
    failure_reason: str | None = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class ActivityEvent(BaseModel):
    id: str = Field(default_factory=lambda: new_id("event"))
    event_type: str
    title: str
    description: str = ""
    entity_type: str | None = None
    entity_id: str | None = None
    created_at: str = Field(default_factory=now_iso)


class LegalReplyJob(BaseModel):
    id: str = Field(default_factory=lambda: new_id("reply"))
    case_id: str
    mode: Literal["short_reply", "long_reply"] = "long_reply"
    title: str
    case_summary: str = ""
    user_question: str = ""
    status: Literal[
        "queued",
        "reasoning",
        "ready_for_review",
        "completed",
        "failed",
    ] = "queued"
    module_state: Literal["idle", "busy"] = "idle"
    assigned_agent_role: str | None = None
    draft_text: str = ""
    output_document_id: str | None = None
    failure_reason: str | None = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class SendMessageRequest(BaseModel):
    content: str


class SendFollowUpRequest(BaseModel):
    content: str | None = None


class CreateCaseFromConversationRequest(BaseModel):
    title: str | None = None
    case_type: Case.model_fields["case_type"].annotation = "other"


class BindConversationCaseRequest(BaseModel):
    case_id: str


class DocumentCreateRequest(BaseModel):
    case_id: str | None = None
    title: str
    document_type: LegalDocument.model_fields["document_type"].annotation = "other"
    content_text: str
    source_filename: str | None = None
    change_summary: str = "Initial version"


class RevisionCreateRequest(BaseModel):
    content_text: str
    source_filename: str | None = None
    author_type: LegalDocumentRevision.model_fields["author_type"].annotation = "owner"
    change_summary: str = ""


class CaseCreateRequest(BaseModel):
    title: str
    case_type: Case.model_fields["case_type"].annotation = "other"
    summary: str = ""
    wechat_contact_ref: str | None = None
    conversation_ref: str | None = None


class TaskCreateRequest(BaseModel):
    title: str
    description: str = ""
    assigned_agent_role: str | None = None
    priority: CaseTask.model_fields["priority"].annotation = "medium"


class MemoryCreateRequest(BaseModel):
    kind: CaseMemory.model_fields["kind"].annotation
    content: str
    confidence: float = 0.8
    source_ref: str | None = None
    confirmed: bool = False


class ReplyJobCreateRequest(BaseModel):
    mode: LegalReplyJob.model_fields["mode"].annotation = "long_reply"
    title: str | None = None
    case_summary: str = ""
    user_question: str = ""
    assigned_agent_role: str | None = None
