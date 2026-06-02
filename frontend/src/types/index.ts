export type OpenClawStatus = {
  online: boolean;
  plugin: string;
  mode: string;
  message: string;
  checked_at: string;
  transport_mode: string;
  sessions_count?: number | null;
  error?: string | null;
};

export type OpenClawConnection = {
  id: string;
  name: string;
  gateway_url: string;
  gateway_token?: string | null;
  workspace_root: string;
  transport_mode: "gateway_rpc" | "mock";
  gateway_protocol_version: number;
  allow_insecure_tls: boolean;
  disable_device_pairing: boolean;
  wechat_session_filter: string;
  list_method: string;
  history_method: string;
  send_method: string;
  history_limit: number;
  enabled: boolean;
  last_checked_at?: string | null;
  last_sync_at?: string | null;
};

export type WechatContact = {
  id: string;
  openclaw_contact_id: string;
  display_name: string;
  remark?: string | null;
  last_seen_at?: string | null;
};

export type WechatConversation = {
  id: string;
  openclaw_conversation_id: string;
  contact_id: string;
  case_id?: string | null;
  status: string;
  auto_reply_source: string;
  last_message_at?: string | null;
  unread_count: number;
  contact?: WechatContact | null;
};

export type WechatAttachment = {
  name: string;
  url: string;
  mime_type?: string | null;
  size?: number | null;
};

export type WechatMessage = {
  id: string;
  conversation_id: string;
  sender: "wechat_user" | "openclaw_auto" | "owner" | "system";
  direction: "inbound" | "outbound" | "internal";
  type?: "text" | "image" | "file" | "mixed";
  content: string;
  attachments?: WechatAttachment[];
  status: string;
  created_at: string;
};

export type CaseItem = {
  id: string;
  title: string;
  case_type: string;
  status: string;
  summary: string;
  wechat_contact_ref?: string | null;
  conversation_ref?: string | null;
  created_at: string;
  updated_at: string;
};

export type CaseTask = {
  id: string;
  case_id: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  assigned_agent_role?: string | null;
  result_summary: string;
};

export type CaseMemory = {
  id: string;
  case_id: string;
  kind: string;
  content: string;
  confidence: number;
  confirmed: boolean;
};

export type LegalAgent = {
  id: string;
  role: string;
  title: string;
  description: string;
  responsibilities: string[];
  group: string;
  reports_to?: string | null;
  active: boolean;
};

export type AgentDepartment = {
  id: string;
  title: string;
  description: string;
  case_types: string[];
  active: boolean;
};

export type AgentGroup = {
  id: string;
  title: string;
  description: string;
  agent_roles: string[];
  departments: AgentDepartment[];
};

export type AgentArchitecture = {
  dispatcher: LegalAgent;
  groups: AgentGroup[];
};

export type LegalDocument = {
  id: string;
  case_id?: string | null;
  title: string;
  document_type: string;
  current_revision_id?: string | null;
  default_branch_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type LegalDocumentRevision = {
  id: string;
  document_id: string;
  version_number: number;
  content_text: string;
  source_filename?: string | null;
  author_type: "owner" | "agent" | "import";
  change_summary: string;
  branch_id?: string | null;
  parent_revision_id?: string | null;
  created_from_revision_id?: string | null;
  short_hash?: string | null;
  created_at: string;
};

export type LegalDocumentBranch = {
  id: string;
  document_id: string;
  name: string;
  head_revision_id?: string | null;
  base_revision_id?: string | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
};

export type DiffSegment = {
  op: "equal" | "insert" | "delete" | "replace";
  text: string;
};

export type LegalDocumentDiff = {
  id: string;
  document_id: string;
  base_revision_id: string;
  target_revision_id: string;
  segments: DiffSegment[];
  paragraph_changes: Array<{
    op: "equal" | "insert" | "delete" | "replace";
    base: string;
    target: string;
  }>;
  risk_summary: string[];
};

export type ReasoningNode = {
  id: string;
  node_type: string;
  label: string;
  content: string;
  confidence: number;
  source_refs: string[];
};

export type ReasoningEdge = {
  id: string;
  source: string;
  target: string;
  relation_type: string;
};

export type LegalReasoningRun = {
  id: string;
  case_id: string;
  status: string;
  input_summary: string;
  nodes: ReasoningNode[];
  edges: ReasoningEdge[];
  follow_up_questions: string[];
  blocked_reason: string;
  review_focus: string[];
  output_summary: string;
  created_at: string;
};

export type LegalReplyJob = {
  id: string;
  case_id: string;
  mode: "short_reply" | "long_reply";
  title: string;
  case_summary: string;
  user_question: string;
  status: "queued" | "reasoning" | "ready_for_review" | "completed" | "failed";
  module_state: "idle" | "busy";
  assigned_agent_role?: string | null;
  draft_text: string;
  output_document_id?: string | null;
  failure_reason?: string | null;
  created_at: string;
  updated_at: string;
};

export type FollowUpQuestion = {
  id: string;
  case_id: string;
  reasoning_run_id?: string | null;
  content: string;
  status: "draft" | "sent_via_openclaw" | "failed" | "ignored";
  sent_message_id?: string | null;
  failure_reason?: string | null;
  created_at: string;
  updated_at: string;
};

export type ActivityEvent = {
  id: string;
  event_type: string;
  title: string;
  description: string;
  created_at: string;
};

export type LegalDocumentTreeRevision = {
  id: string;
  label: string;
  version_number: number;
  short_hash?: string | null;
  parent_revision_id?: string | null;
  change_summary: string;
  source_filename?: string | null;
  created_at: string;
};

export type LegalDocumentTreeBranch = LegalDocumentBranch & {
  revisions: LegalDocumentTreeRevision[];
};

export type LegalDocumentTree = {
  document: LegalDocument;
  branches: LegalDocumentTreeBranch[];
};

export type LegalDocumentAnalysis = {
  id: string;
  document_id: string;
  base_revision_id: string;
  target_revision_id: string;
  source: "llm" | "rule_fallback";
  risk_level: "low" | "medium" | "high";
  ambiguities: string[];
  stealth_changes: string[];
  risk_points: string[];
  suggestions: string[];
  manual_review_checklist: string[];
  created_at: string;
};
