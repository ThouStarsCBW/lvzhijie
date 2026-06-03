import type {
  ActivityEvent,
  AgentArchitecture,
  CaseItem,
  CaseMemory,
  CaseTask,
  CaseTaskComment,
  FollowUpQuestion,
  LegalAgent,
  LegalDocument,
  LegalDocumentAnalysis,
  LegalDocumentBranch,
  LegalDocumentDiff,
  LegalDocumentRevision,
  LegalDocumentTree,
  LegalResearchResult,
  LegalResearchRun,
  LegalReplyJob,
  LegalReasoningRun,
  OpenClawConnection,
  OpenClawStatus,
  WechatConversation,
  WechatMessage,
} from "@/types";

export type MockConversation = WechatConversation & {
  contact?: {
    id: string;
    openclaw_contact_id: string;
    display_name: string;
    remark?: string | null;
    avatar_url?: string | null;
    last_seen_at?: string | null;
  } | null;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export function apiAssetUrl(path: string) {
  if (!path) return "";
  if (/^(https?:|data:|blob:)/i.test(path)) return path;
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE.replace(/\/$/, "")}${normalizedPath}`;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const isFormData = options?.body instanceof FormData;
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: isFormData
      ? options?.headers
      : { "Content-Type": "application/json", ...options?.headers },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  summary: () => request<Record<string, unknown>>("/api/dashboard/summary"),
  activity: () => request<ActivityEvent[]>("/api/activity"),

  openclawConnection: () => request<OpenClawConnection>("/api/openclaw/connection"),
  updateOpenclawConnection: (payload: OpenClawConnection) =>
    request<OpenClawConnection>("/api/openclaw/connection", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  openclawStatus: () => request<OpenClawStatus>("/api/openclaw/status"),
  syncOpenclaw: () => request<Record<string, unknown>>("/api/openclaw/sync", { method: "POST" }),

  conversations: () => request<WechatConversation[]>("/api/wechat/conversations"),
  conversationMessages: (conversationId: string) =>
    request<WechatMessage[]>(`/api/wechat/conversations/${conversationId}/messages`),
  deleteWechatConversation: (conversationId: string) =>
    request<Record<string, unknown>>(`/api/wechat/conversations/${conversationId}`, {
      method: "DELETE",
    }),
  sendWechatMessage: (conversationId: string, content: string) =>
    request<WechatMessage>(`/api/wechat/conversations/${conversationId}/send`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),
  createCaseFromConversation: (conversationId: string, title?: string) =>
    request<CaseItem>(`/api/wechat/conversations/${conversationId}/case`, {
      method: "POST",
      body: JSON.stringify({ title, case_type: "other" }),
    }),
  bindConversationToCase: (conversationId: string, caseId: string) =>
    request<CaseItem>(`/api/wechat/conversations/${conversationId}/bind-case`, {
      method: "POST",
      body: JSON.stringify({ case_id: caseId }),
    }),

  cases: () => request<CaseItem[]>("/api/cases"),
  createCase: (payload: { title: string; case_type: string; summary?: string }) =>
    request<CaseItem>("/api/cases", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteCase: (caseId: string) =>
    request<Record<string, unknown>>(`/api/cases/${caseId}`, {
      method: "DELETE",
    }),
  caseDetail: (caseId: string) =>
    request<{
      case: CaseItem;
      tasks: CaseTask[];
      task_comments: CaseTaskComment[];
      research_runs: LegalResearchRun[];
      research_results: LegalResearchResult[];
      memories: CaseMemory[];
      documents: LegalDocument[];
      reasoning_runs: LegalReasoningRun[];
      follow_up_questions: FollowUpQuestion[];
      reply_jobs: LegalReplyJob[];
      messages: WechatMessage[];
    }>(`/api/cases/${caseId}`),
  createTask: (
    caseId: string,
    titleOrPayload:
      | string
      | {
          title: string;
          description?: string;
          task_type?: CaseTask["task_type"];
          status?: string;
          assigned_agent_role?: string | null;
          priority?: string;
          due_at?: string | null;
          depends_on_task_ids?: string[];
          document_id?: string | null;
          base_revision_id?: string | null;
          target_revision_id?: string | null;
          metadata?: Record<string, unknown>;
        },
    assigned_agent_role?: string,
  ) => {
    const payload =
      typeof titleOrPayload === "string"
        ? { title: titleOrPayload, assigned_agent_role }
        : titleOrPayload;
    return request<CaseTask>(`/api/cases/${caseId}/tasks`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  updateTask: (
    caseId: string,
    taskId: string,
    payload: Partial<
      Pick<
        CaseTask,
        | "title"
        | "description"
        | "task_type"
        | "status"
        | "priority"
        | "assigned_agent_role"
        | "due_at"
        | "depends_on_task_ids"
        | "document_id"
        | "base_revision_id"
        | "target_revision_id"
        | "metadata"
        | "result_summary"
      >
    > & { comment?: string },
  ) =>
    request<CaseTask>(`/api/cases/${caseId}/tasks/${taskId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  executeTask: (
    caseId: string,
    taskId: string,
    payload?: {
      query?: string;
      keywords?: string[];
      content_text?: string;
      title?: string;
      document_id?: string | null;
      base_revision_id?: string | null;
      target_revision_id?: string | null;
      change_summary?: string;
    },
  ) =>
    request<CaseTask>(`/api/cases/${caseId}/tasks/${taskId}/execute`, {
      method: "POST",
      body: JSON.stringify(payload ?? {}),
    }),
  taskComments: (caseId: string, taskId: string) =>
    request<CaseTaskComment[]>(`/api/cases/${caseId}/tasks/${taskId}/comments`),
  createTaskComment: (caseId: string, taskId: string, message: string) =>
    request<CaseTaskComment>(`/api/cases/${caseId}/tasks/${taskId}/comments`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  createLegacyTask: (caseId: string, title: string, assigned_agent_role?: string) =>
    request<CaseTask>(`/api/cases/${caseId}/tasks`, {
      method: "POST",
      body: JSON.stringify({ title, assigned_agent_role }),
    }),
  deleteTask: (caseId: string, taskId: string) =>
    request<Record<string, unknown>>(`/api/cases/${caseId}/tasks/${taskId}`, {
      method: "DELETE",
    }),
  createMemory: (caseId: string, kind: string, content: string) =>
    request<CaseMemory>(`/api/cases/${caseId}/memories`, {
      method: "POST",
      body: JSON.stringify({ kind, content }),
    }),
  deleteMemory: (caseId: string, memoryId: string) =>
    request<Record<string, unknown>>(`/api/cases/${caseId}/memories/${memoryId}`, {
      method: "DELETE",
    }),
  createFollowUpQuestion: (caseId: string, content: string) =>
    request<FollowUpQuestion>(`/api/cases/${caseId}/follow-up-questions`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),
  deleteFollowUpQuestion: (caseId: string, questionId: string) =>
    request<Record<string, unknown>>(
      `/api/cases/${caseId}/follow-up-questions/${questionId}`,
      {
        method: "DELETE",
      },
    ),
  createReplyJob: (
    caseId: string,
    payload: {
      mode: "short_reply" | "long_reply";
      title?: string;
      case_summary?: string;
      user_question?: string;
      assigned_agent_role?: string;
    },
  ) =>
    request<LegalReplyJob>(`/api/cases/${caseId}/reply-jobs`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  processReplyJob: (caseId: string, jobId: string) =>
    request<LegalReplyJob>(`/api/cases/${caseId}/reply-jobs/${jobId}/process`, {
      method: "POST",
    }),
  deleteReplyJob: (caseId: string, jobId: string) =>
    request<Record<string, unknown>>(`/api/cases/${caseId}/reply-jobs/${jobId}`, {
      method: "DELETE",
    }),
  sendFollowUpQuestion: (caseId: string, questionId: string, content?: string) =>
    request<{ question: FollowUpQuestion; message: WechatMessage }>(
      `/api/cases/${caseId}/follow-up-questions/${questionId}/send`,
      {
        method: "POST",
        body: JSON.stringify({ content }),
      },
    ),

  agents: () => request<LegalAgent[]>("/api/agents"),
  agentArchitecture: () => request<AgentArchitecture>("/api/agents/architecture"),
  documents: (caseId?: string) => {
    const suffix = caseId ? `?case_id=${encodeURIComponent(caseId)}` : "";
    return request<LegalDocument[]>(`/api/documents${suffix}`);
  },
  deleteReasoningRun: (caseId: string, runId: string) =>
    request<Record<string, unknown>>(`/api/reasoning/cases/${caseId}/runs/${runId}`, {
      method: "DELETE",
    }),
  createDocument: (payload: {
    title: string;
    case_id?: string | null;
    document_type: string;
    content_text: string;
    change_summary?: string;
  }) =>
    request<LegalDocument>("/api/documents", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  uploadDocument: (form: FormData) =>
    request<LegalDocument>("/api/documents/upload", {
      method: "POST",
      body: form,
    }),
  documentDetail: (documentId: string) =>
    request<{ document: LegalDocument; branches: LegalDocumentBranch[]; revisions: LegalDocumentRevision[] }>(
      `/api/documents/${documentId}`,
    ),
  deleteDocument: (documentId: string) =>
    request<Record<string, unknown>>(`/api/documents/${documentId}`, {
      method: "DELETE",
    }),
  createRevision: (documentId: string, payload: { content_text: string; change_summary?: string }) =>
    request<LegalDocumentRevision>(`/api/documents/${documentId}/revisions`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteRevision: (documentId: string, revisionId: string) =>
    request<Record<string, unknown>>(`/api/documents/${documentId}/revisions/${revisionId}`, {
      method: "DELETE",
    }),
  uploadRevision: (documentId: string, form: FormData) =>
    request<LegalDocumentRevision>(`/api/documents/${documentId}/revisions/upload`, {
      method: "POST",
      body: form,
    }),
  documentDiff: (documentId: string, baseRevisionId?: string, targetRevisionId?: string) => {
    const params = new URLSearchParams();
    if (baseRevisionId) params.set("base_revision_id", baseRevisionId);
    if (targetRevisionId) params.set("target_revision_id", targetRevisionId);
    const suffix = params.toString() ? `?${params.toString()}` : "";
    return request<LegalDocumentDiff>(`/api/documents/${documentId}/diff${suffix}`);
  },
  documentExportUrl: (documentId: string) => `${API_BASE}/api/documents/${documentId}/export.docx`,

  documentTree: (documentId: string) =>
    request<LegalDocumentTree>(`/api/documents/${documentId}/tree`),

  createDocumentBranch: (documentId: string, payload: { name: string; base_revision_id: string }) =>
    request<LegalDocumentBranch>(`/api/documents/${documentId}/branches`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  createBranchRevision: (
    documentId: string,
    branchId: string,
    payload: { content_text: string; change_summary?: string; source_filename?: string | null },
  ) =>
    request<LegalDocumentRevision>(`/api/documents/${documentId}/branches/${branchId}/revisions`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  uploadBranchRevision: (documentId: string, branchId: string, form: FormData) =>
    request<LegalDocumentRevision>(`/api/documents/${documentId}/branches/${branchId}/revisions/upload`, {
      method: "POST",
      body: form,
    }),

  analyzeDocumentDiff: (
    documentId: string,
    payload: { base_revision_id: string; target_revision_id: string },
  ) =>
    request<LegalDocumentAnalysis>(`/api/documents/${documentId}/diff/analyze`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  documentDiffExportUrl: (documentId: string, baseRevisionId: string, targetRevisionId: string) => {
    const params = new URLSearchParams({
      base_revision_id: baseRevisionId,
      target_revision_id: targetRevisionId,
    });
    return `${API_BASE}/api/documents/${documentId}/diff/export.docx?${params.toString()}`;
  },

  generateReasoning: (caseId: string) =>
    request<LegalReasoningRun>(`/api/reasoning/cases/${caseId}/generate`, {
      method: "POST",
    }),

  mockWechatConversations: () => request<MockConversation[]>("/api/mock-wechat/conversations"),
  createMockWechatConversation: (payload: {
    display_name: string;
    remark?: string;
    avatar_url?: string | null;
  }) =>
    request<MockConversation>("/api/mock-wechat/conversations", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateMockWechatConversation: (
    conversationId: string,
    payload: Record<string, unknown>,
  ) =>
    request<MockConversation>(
      `/api/mock-wechat/conversations/${conversationId}`,
      {
        method: "PUT",
        body: JSON.stringify(payload),
      },
    ),
  deleteMockWechatConversation: (conversationId: string) =>
    request<Record<string, unknown>>(
      `/api/mock-wechat/conversations/${conversationId}`,
      {
        method: "DELETE",
      },
    ),
  mockWechatMessages: (conversationId: string) =>
    request<WechatMessage[]>(
      `/api/mock-wechat/conversations/${conversationId}/messages`,
    ),
  createMockWechatMessage: (conversationId: string, form: FormData) =>
    request<WechatMessage>(
      `/api/mock-wechat/conversations/${conversationId}/messages`,
      {
        method: "POST",
        body: form,
      },
    ),
  deleteMockWechatMessage: (conversationId: string, messageId: string) =>
    request<Record<string, unknown>>(
      `/api/mock-wechat/conversations/${conversationId}/messages/${messageId}`,
      {
        method: "DELETE",
      },
    ),
};
