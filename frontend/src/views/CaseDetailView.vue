<template>
  <PageHeader :title="detail?.case.title ?? '案件'" :description="detail?.case.summary">
    <RouterLink class="button" to="/cases">案件列表</RouterLink>
    <button class="button primary" @click="generateReasoning">生成推理图</button>
    <button v-if="detail" class="button danger" :disabled="deletingId === detail.case.id" @click="deleteCase">
      {{ deletingId === detail.case.id ? "删除中" : confirmingId === detail.case.id ? "确认删除案件" : "删除案件" }}
    </button>
    <button v-if="detail && confirmingId === detail.case.id" class="button" @click="confirmingId = ''">取消</button>
  </PageHeader>

  <section v-if="detail" class="page-content">
    <div class="grid cols-4">
      <StatCard label="任务" :value="detail.tasks.length" />
      <StatCard label="案件记忆" :value="detail.memories.length" />
      <StatCard label="文件" :value="detail.documents.length" />
      <StatCard label="追问" :value="detail.follow_up_questions.length" />
      <StatCard label="回复任务" :value="detail.reply_jobs.length" />
    </div>

    <div class="tabs" style="margin-top: 16px">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="['tab-button', activeTab === tab.key && 'active']"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <section v-if="activeTab === 'overview'" class="grid cols-2" style="margin-top: 16px">
      <section class="panel">
        <h2 class="panel-title">案件概览</h2>
        <p class="panel-subtitle">案件基础信息和业务边界。</p>
        <div class="meta-grid">
          <span>类型</span><strong>{{ caseTypeLabel(detail.case.case_type) }}</strong>
          <span>状态</span><strong>{{ caseStatusLabel(detail.case.status) }}</strong>
          <span>客户会话</span><strong>{{ detail.case.conversation_ref || "未绑定" }}</strong>
          <span>创建时间</span><strong>{{ shortTime(detail.case.created_at) }}</strong>
        </div>
      </section>

      <section class="panel">
        <h2 class="panel-title">新建法律任务</h2>
        <p class="panel-subtitle">检索、审查和撰写任务会沉淀到案件和文档版本。</p>
        <input v-model="taskTitle" class="input" placeholder="任务标题" />
        <select v-model="taskType" class="select" style="margin-top: 10px">
          <option v-for="option in taskTypeOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
        <textarea
          v-model="taskDescription"
          class="textarea"
          placeholder="任务说明、检索问题或撰写要求"
          style="margin-top: 10px"
        />
        <select v-model="taskAgent" class="select" style="margin-top: 10px">
          <option value="">不指定角色</option>
          <option v-for="agent in agents" :key="agent.id" :value="agent.title">
            {{ agent.title }}
          </option>
        </select>
        <select v-model="taskPriority" class="select" style="margin-top: 10px">
          <option value="medium">普通优先级</option>
          <option value="high">高优先级</option>
          <option value="urgent">紧急</option>
          <option value="low">低优先级</option>
        </select>
        <select
          v-if="taskType === 'document_review' || taskType === 'document_drafting'"
          v-model="taskDocumentId"
          class="select"
          style="margin-top: 10px"
        >
          <option value="">不绑定文件</option>
          <option v-for="document in detail.documents" :key="document.id" :value="document.id">
            {{ document.title }}
          </option>
        </select>
        <div class="form-actions">
          <button class="button primary" :disabled="!taskTitle.trim()" @click="createTask">
            添加任务
          </button>
        </div>
      </section>

      <section class="panel full-span">
        <h2 class="panel-title">任务中心</h2>
        <div v-if="actionMessage" class="muted small" style="margin-bottom: 10px">{{ actionMessage }}</div>
        <div class="task-board">
          <section v-for="column in taskStatusColumns" :key="column.key" class="task-column">
            <div class="task-column-head">
              <strong>{{ column.label }}</strong>
              <span class="muted small">{{ tasksByStatus(column.key).length }}</span>
            </div>
            <article v-for="task in tasksByStatus(column.key)" :key="task.id" class="task-card">
              <div class="task-card-head">
                <div>
                  <Badge :tone="taskTypeTone(task.task_type)">{{ taskTypeLabel(task.task_type) }}</Badge>
                  <Badge :tone="taskStatusTone(task.status)" style="margin-left: 6px">
                    {{ taskStatusLabel(task.status) }}
                  </Badge>
                </div>
                <button class="button danger tiny" :disabled="deletingId === task.id" @click="deleteTask(task.id)">
                  {{ deletingId === task.id ? "删除中" : confirmingId === task.id ? "确认删除" : "删除" }}
                </button>
              </div>
              <h3 class="task-card-title">{{ task.title }}</h3>
              <div class="muted small">
                {{ agentTitleLabel(task.assigned_agent_role) }} · {{ priorityLabel(task.priority) }}
              </div>
              <p v-if="task.description" class="muted small">{{ task.description }}</p>
              <p v-if="task.result_summary" class="task-result">{{ task.result_summary }}</p>
              <div v-if="task.blocked_by_task_ids?.length" class="muted small">
                依赖未完成：{{ task.blocked_by_task_ids.length }} 项
              </div>
              <div v-if="task.document_id || task.output_document_id" class="task-links">
                <RouterLink v-if="task.document_id" class="button tiny" :to="`/documents/${task.document_id}`">
                  查看文件
                </RouterLink>
                <a v-if="task.output_document_id" class="button tiny" :href="api.documentExportUrl(task.output_document_id)">
                  导出产物
                </a>
              </div>
              <div v-if="task.research_results?.length" class="research-result-list">
                <article v-for="result in task.research_results.slice(0, 2)" :key="result.id" class="research-result">
                  <strong>{{ result.title }}</strong>
                  <div class="muted small">{{ result.reference }}</div>
                  <ul>
                    <li v-for="point in result.key_points.slice(0, 2)" :key="point">{{ point }}</li>
                  </ul>
                </article>
              </div>
              <textarea
                v-if="task.task_type === 'similar_case_search' || task.task_type === 'regulation_search' || task.task_type === 'document_drafting'"
                v-model="taskExecutionInputs[task.id]"
                class="textarea compact"
                :placeholder="task.task_type === 'document_drafting' ? '可粘贴草稿文本，留空则按案件材料生成' : '可补充检索关键词，留空则按案情生成'"
              />
              <div class="task-actions">
                <button class="button primary tiny" :disabled="processingId === task.id" @click="executeTask(task)">
                  {{ processingId === task.id ? "执行中" : "执行" }}
                </button>
                <button class="button tiny" :disabled="task.status === 'done'" @click="updateTaskStatus(task, 'waiting_owner_review')">
                  待复核
                </button>
                <button class="button tiny" :disabled="task.status === 'done'" @click="updateTaskStatus(task, 'done')">
                  完成
                </button>
              </div>
              <div class="task-comments" v-if="task.comments?.length">
                <div v-for="comment in task.comments.slice(-2)" :key="comment.id" class="muted small">
                  {{ comment.author_label }}：{{ comment.message }}
                </div>
              </div>
              <div class="task-comment-box">
                <input v-model="taskCommentInputs[task.id]" class="input compact" placeholder="记录过程" />
                <button class="button tiny" :disabled="!taskCommentInputs[task.id]?.trim()" @click="addTaskComment(task)">
                  记录
                </button>
              </div>
              <button v-if="confirmingId === task.id" class="button tiny" @click="confirmingId = ''">取消删除</button>
            </article>
            <div v-if="tasksByStatus(column.key).length === 0" class="empty-state compact">暂无任务</div>
          </section>
        </div>
      </section>
    </section>

    <section v-if="activeTab === 'facts'" class="grid cols-2" style="margin-top: 16px">
      <section class="panel">
        <h2 class="panel-title">写入案件记忆</h2>
        <p class="panel-subtitle">事实、时间线、证据和不确定点分开沉淀。</p>
        <select v-model="memoryKind" class="select">
          <option value="fact">事实</option>
          <option value="timeline">时间线</option>
          <option value="evidence">证据</option>
          <option value="uncertainty">不确定点</option>
          <option value="note">备注</option>
        </select>
        <textarea v-model="memoryContent" class="textarea" placeholder="输入要沉淀的内容" style="margin-top: 10px" />
        <div class="form-actions">
          <button class="button primary" :disabled="!memoryContent.trim()" @click="createMemory">
            写入
          </button>
        </div>
      </section>

      <section class="panel">
        <h2 class="panel-title">记忆清单</h2>
        <div v-for="memory in detail.memories" :key="memory.id" class="list-item item-with-action">
          <div>
            <Badge :tone="memory.kind === 'uncertainty' ? 'amber' : memory.kind === 'evidence' ? 'green' : 'blue'">
              {{ memoryKindLabel(memory.kind) }}
            </Badge>
            <div style="margin-top: 8px">{{ memory.content }}</div>
            <div class="muted small">置信度 {{ Math.round(memory.confidence * 100) }}%</div>
          </div>
          <button class="button danger" :disabled="deletingId === memory.id" @click="deleteMemory(memory.id)">
            {{ deletingId === memory.id ? "删除中" : confirmingId === memory.id ? "确认删除" : "删除" }}
          </button>
          <button v-if="confirmingId === memory.id" class="button" @click="confirmingId = ''">取消</button>
        </div>
      </section>
    </section>

    <section v-if="activeTab === 'documents'" class="grid cols-2" style="margin-top: 16px">
      <section class="panel">
        <h2 class="panel-title">上传案件文件</h2>
        <p class="panel-subtitle">支持文本和文档转文本后进入版本库。</p>
        <input v-model="documentTitle" class="input" placeholder="文件标题，可留空使用文件名" />
        <select v-model="documentType" class="select" style="margin-top: 10px">
          <option value="contract">合同</option>
          <option value="letter">函件</option>
          <option value="pleading">文书</option>
          <option value="evidence">证据</option>
          <option value="other">其他</option>
        </select>
        <input class="input file-input" type="file" accept=".txt,.md,.docx" @change="pickDocument" />
        <div class="form-actions">
          <button class="button primary" :disabled="!documentFile" @click="uploadDocument">上传文件</button>
        </div>
      </section>

      <section class="panel">
        <h2 class="panel-title">文件列表</h2>
        <div v-for="document in detail.documents" :key="document.id" class="list-item item-with-action">
          <div>
            <strong>{{ document.title }}</strong>
            <div class="muted small">{{ documentTypeLabel(document.document_type) }}</div>
          </div>
          <a class="button" :href="api.documentExportUrl(document.id)">导出 Word</a>
          <button class="button danger" :disabled="deletingId === document.id" @click="deleteDocument(document.id)">
            {{ deletingId === document.id ? "删除中" : confirmingId === document.id ? "确认删除" : "删除" }}
          </button>
          <button v-if="confirmingId === document.id" class="button" @click="confirmingId = ''">取消</button>
        </div>
        <div v-if="!detail.documents.length" class="empty-state">暂无文件。</div>
      </section>
    </section>

    <section v-if="activeTab === 'workflow'" class="grid cols-2" style="margin-top: 16px">
      <section class="panel">
        <h2 class="panel-title">创建回复任务</h2>
        <p class="panel-subtitle">系统内部生成短回复草稿或长回复文书，不涉及外部终端连接。</p>
        <select v-model="replyMode" class="select">
          <option value="short_reply">短回复草稿</option>
          <option value="long_reply">长回复文书</option>
        </select>
        <input v-model="replyTitle" class="input" placeholder="任务标题，可留空自动生成" style="margin-top: 10px" />
        <select v-model="replyAgent" class="select" style="margin-top: 10px">
          <option value="">不指定角色</option>
          <option v-for="agent in agents" :key="agent.id" :value="agent.title">
            {{ agent.title }}
          </option>
        </select>
        <textarea v-model="replyQuestion" class="textarea" placeholder="用户问题或需要回复的事项" style="margin-top: 10px" />
        <textarea v-model="replySummary" class="textarea" placeholder="案件摘要，可留空使用案件记录自动整理" />
        <div class="form-actions">
          <button class="button primary" @click="createReplyJob">
            创建任务
          </button>
        </div>
      </section>

      <section class="panel">
        <h2 class="panel-title">回复队列</h2>
        <p class="panel-subtitle">长回复会进入推理处理，完成后生成可导出的 Word 文件。</p>
        <div v-for="job in detail.reply_jobs" :key="job.id" class="list-item workflow-item">
          <div class="workflow-item-head">
            <div>
              <Badge :tone="job.mode === 'long_reply' ? 'blue' : 'green'">{{ replyModeLabel(job.mode) }}</Badge>
              <Badge :tone="replyStatusTone(job.status)" style="margin-left: 6px">
                {{ replyStatusLabel(job.status) }}
              </Badge>
              <Badge :tone="job.module_state === 'busy' ? 'red' : 'green'" style="margin-left: 6px">
                {{ job.module_state === "busy" ? "忙碌中" : "空闲中" }}
              </Badge>
              <h3 class="workflow-title">{{ job.title }}</h3>
              <div class="muted small">{{ agentTitleLabel(job.assigned_agent_role) }}</div>
            </div>
            <div class="row-actions">
              <button
                class="button primary"
                :disabled="job.status === 'completed' || processingId === job.id"
                @click="processReplyJob(job.id)"
              >
                {{ processingId === job.id ? "处理中" : job.mode === "long_reply" ? "推理生成" : "刷新草稿" }}
              </button>
              <a v-if="job.output_document_id" class="button" :href="api.documentExportUrl(job.output_document_id)">
                导出 Word
              </a>
              <button class="button danger" :disabled="deletingId === job.id" @click="deleteReplyJob(job.id)">
                {{ deletingId === job.id ? "删除中" : confirmingId === job.id ? "确认删除" : "删除" }}
              </button>
              <button v-if="confirmingId === job.id" class="button" @click="confirmingId = ''">取消</button>
            </div>
          </div>
          <p v-if="job.case_summary" class="muted small">{{ job.case_summary }}</p>
          <pre v-if="job.draft_text" class="draft-preview">{{ job.draft_text }}</pre>
          <div v-if="job.failure_reason" class="muted small">{{ job.failure_reason }}</div>
        </div>
        <div v-if="!detail.reply_jobs.length" class="empty-state">暂无回复任务。</div>
      </section>
    </section>

    <section v-if="activeTab === 'reasoning'" class="grid cols-2" style="margin-top: 16px">
      <section class="panel">
        <h2 class="panel-title">推理图</h2>
        <p class="panel-subtitle">节点和边可审查，追问可以直接发回客户。</p>
        <div v-if="latestRun" class="reasoning-summary">
          <Badge :tone="latestRun.status === 'needs_evidence' ? 'amber' : 'green'">
            {{ reasoningStatusLabel(latestRun.status) }}
          </Badge>
          <p class="muted small">{{ latestRun.output_summary }}</p>
          <p v-if="latestRun.blocked_reason" class="muted small">暂停点：{{ latestRun.blocked_reason }}</p>
          <div class="agent-chip-row">
            <span v-for="item in latestRun.review_focus" :key="item" class="agent-chip">{{ item }}</span>
          </div>
        </div>
        <div v-if="latestRun" class="form-actions" style="margin-bottom: 12px">
          <button class="button danger" :disabled="deletingId === latestRun.id" @click="deleteReasoning(latestRun.id)">
            {{ deletingId === latestRun.id ? "删除中" : confirmingId === latestRun.id ? "确认删除推理图" : "删除推理图" }}
          </button>
          <button v-if="confirmingId === latestRun.id" class="button" @click="confirmingId = ''">取消</button>
        </div>
        <div v-if="latestRun" class="reasoning-canvas">
          <article v-for="node in latestRun.nodes" :key="node.id" class="reasoning-node">
            <Badge :tone="toneFor(node.node_type)">{{ nodeTypeLabel(node.node_type) }}</Badge>
            <h3>{{ node.label }}</h3>
            <p class="muted small">{{ node.content }}</p>
          </article>
        </div>
        <div v-else class="empty-state">尚未生成推理图。</div>
      </section>

      <section class="panel">
        <h2 class="panel-title">追问问题</h2>
        <p class="panel-subtitle">发送动作通过当前聊天通道完成。</p>
        <textarea v-model="followUpContent" class="textarea" placeholder="手动添加追问" />
        <div class="form-actions">
          <button class="button" :disabled="!followUpContent.trim()" @click="createFollowUp">
            添加追问
          </button>
        </div>
        <div v-if="actionMessage" class="muted small" style="margin-bottom: 10px">{{ actionMessage }}</div>
        <div v-for="question in detail.follow_up_questions" :key="question.id" class="list-item follow-up-row">
          <div>
            <strong>{{ question.content }}</strong>
            <div class="muted small">{{ questionStatusLabel(question.status) }} {{ question.failure_reason || "" }}</div>
          </div>
          <div class="row-actions">
            <button
              class="button primary"
              :disabled="!detail.case.conversation_ref || question.status === 'sent_via_openclaw'"
              @click="sendFollowUp(question.id)"
            >
              发送
            </button>
            <button class="button danger" :disabled="deletingId === question.id" @click="deleteFollowUp(question.id)">
              {{ deletingId === question.id ? "删除中" : confirmingId === question.id ? "确认删除" : "删除" }}
            </button>
            <button v-if="confirmingId === question.id" class="button" @click="confirmingId = ''">取消</button>
          </div>
        </div>
      </section>
    </section>

    <section v-if="activeTab === 'chat'" class="panel" style="margin-top: 16px">
      <h2 class="panel-title">关联客户聊天</h2>
      <p class="panel-subtitle">聊天来源为微信桥通道同步。</p>
      <div
        v-for="message in detail.messages"
        :key="message.id"
        :class="['message', message.direction === 'outbound' && 'outbound']"
      >
        <div>{{ message.content }}</div>
        <div class="message-meta">{{ messageLabel(message) }}</div>
      </div>
      <div v-if="!detail.messages.length" class="empty-state">此案件尚未绑定客户聊天。</div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import Badge from "@/components/Badge.vue";
import PageHeader from "@/components/PageHeader.vue";
import StatCard from "@/components/StatCard.vue";
import { api } from "@/services/api";
import type { CaseTask, LegalAgent } from "@/types";

const props = defineProps<{ id: string }>();
const route = useRoute();
const router = useRouter();
const detail = ref<Awaited<ReturnType<typeof api.caseDetail>> | null>(null);
const agents = ref<LegalAgent[]>([]);
const activeTab = ref(tabFromPath(route.path));
const taskTitle = ref("");
const taskDescription = ref("");
const taskType = ref<CaseTask["task_type"]>("general");
const taskAgent = ref("");
const taskPriority = ref("medium");
const taskDocumentId = ref("");
const taskExecutionInputs = ref<Record<string, string>>({});
const taskCommentInputs = ref<Record<string, string>>({});
const memoryKind = ref("fact");
const memoryContent = ref("");
const documentTitle = ref("");
const documentType = ref("contract");
const documentFile = ref<File | null>(null);
const followUpContent = ref("");
const replyMode = ref<"short_reply" | "long_reply">("short_reply");
const replyTitle = ref("");
const replyAgent = ref("");
const replyQuestion = ref("");
const replySummary = ref("");
const actionMessage = ref("");
const deletingId = ref("");
const confirmingId = ref("");
const processingId = ref("");

const taskTypeOptions: Array<{ value: CaseTask["task_type"]; label: string }> = [
  { value: "general", label: "通用任务" },
  { value: "similar_case_search", label: "类案检索" },
  { value: "regulation_search", label: "法规检索" },
  { value: "document_review", label: "文档审查" },
  { value: "document_drafting", label: "文档撰写" },
  { value: "client_reply", label: "客户回复" },
  { value: "reasoning", label: "案件推理" },
];

const taskStatusColumns = [
  { key: "todo", label: "待办" },
  { key: "in_progress", label: "进行中" },
  { key: "waiting_owner_review", label: "待复核" },
  { key: "done", label: "已完成" },
  { key: "blocked", label: "受阻" },
];

const tabs = [
  { key: "overview", label: "总览" },
  { key: "facts", label: "事实/证据" },
  { key: "documents", label: "文件" },
  { key: "workflow", label: "回复工作流" },
  { key: "reasoning", label: "推理/追问" },
  { key: "chat", label: "聊天" },
];

const latestRun = computed(() => {
  const runs = detail.value?.reasoning_runs ?? [];
  return runs.length ? runs[runs.length - 1] : null;
});

async function load() {
  detail.value = await api.caseDetail(props.id);
}

async function withDelete(id: string, action: () => Promise<void>) {
  deletingId.value = id;
  try {
    await action();
    confirmingId.value = "";
  } finally {
    deletingId.value = "";
  }
}

function armDelete(id: string) {
  if (confirmingId.value !== id) {
    confirmingId.value = id;
    return false;
  }
  return true;
}

async function deleteCase() {
  if (!detail.value) return;
  if (!armDelete(detail.value.case.id)) return;
  await withDelete(detail.value.case.id, async () => {
    await api.deleteCase(props.id);
    await router.push("/cases");
  });
}

async function generateReasoning() {
  await api.generateReasoning(props.id);
  activeTab.value = "reasoning";
  await load();
}

async function createTask() {
  if (!taskTitle.value.trim()) return;
  await api.createTask(props.id, {
    title: taskTitle.value.trim(),
    description: taskDescription.value.trim(),
    task_type: taskType.value,
    assigned_agent_role: taskAgent.value || undefined,
    priority: taskPriority.value,
    document_id: taskDocumentId.value || undefined,
    metadata:
      taskType.value === "similar_case_search" || taskType.value === "regulation_search"
        ? { query: taskDescription.value.trim() }
        : {},
  });
  taskTitle.value = "";
  taskDescription.value = "";
  taskType.value = "general";
  taskAgent.value = "";
  taskPriority.value = "medium";
  taskDocumentId.value = "";
  await load();
}

function tasksByStatus(status: string) {
  return (detail.value?.tasks ?? []).filter((task) => task.status === status);
}

async function updateTaskStatus(task: CaseTask, status: string) {
  processingId.value = task.id;
  actionMessage.value = "";
  try {
    await api.updateTask(props.id, task.id, { status });
    await load();
  } catch (error) {
    actionMessage.value = error instanceof Error ? error.message : "任务状态更新失败";
  } finally {
    processingId.value = "";
  }
}

async function executeTask(task: CaseTask) {
  processingId.value = task.id;
  actionMessage.value = "";
  const input = taskExecutionInputs.value[task.id]?.trim();
  try {
    await api.executeTask(props.id, task.id, {
      query:
        task.task_type === "similar_case_search" || task.task_type === "regulation_search"
          ? input || undefined
          : undefined,
      content_text: task.task_type === "document_drafting" ? input || undefined : undefined,
      title: task.task_type === "document_drafting" ? task.title : undefined,
      document_id: task.document_id || undefined,
      base_revision_id: task.base_revision_id || undefined,
      target_revision_id: task.target_revision_id || undefined,
    });
    taskExecutionInputs.value[task.id] = "";
    await load();
  } catch (error) {
    actionMessage.value = error instanceof Error ? error.message : "任务执行失败";
  } finally {
    processingId.value = "";
  }
}

async function addTaskComment(task: CaseTask) {
  const message = taskCommentInputs.value[task.id]?.trim();
  if (!message) return;
  await api.createTaskComment(props.id, task.id, message);
  taskCommentInputs.value[task.id] = "";
  await load();
}

async function deleteTask(taskId: string) {
  if (!armDelete(taskId)) return;
  await withDelete(taskId, async () => {
    await api.deleteTask(props.id, taskId);
    await load();
  });
}

async function createMemory() {
  if (!memoryContent.value.trim()) return;
  await api.createMemory(props.id, memoryKind.value, memoryContent.value.trim());
  memoryContent.value = "";
  await load();
}

async function deleteMemory(memoryId: string) {
  if (!armDelete(memoryId)) return;
  await withDelete(memoryId, async () => {
    await api.deleteMemory(props.id, memoryId);
    await load();
  });
}

function pickDocument(event: Event) {
  const input = event.target as HTMLInputElement;
  documentFile.value = input.files?.[0] ?? null;
}

async function uploadDocument() {
  if (!documentFile.value) return;
  const form = new FormData();
  form.append("file", documentFile.value);
  form.append("case_id", props.id);
  form.append("document_type", documentType.value);
  if (documentTitle.value.trim()) form.append("title", documentTitle.value.trim());
  form.append("change_summary", "案件文件上传");
  await api.uploadDocument(form);
  documentFile.value = null;
  documentTitle.value = "";
  await load();
}

async function deleteDocument(documentId: string) {
  if (!armDelete(documentId)) return;
  await withDelete(documentId, async () => {
    await api.deleteDocument(documentId);
    await load();
  });
}

async function createReplyJob() {
  if (!detail.value) return;
  await api.createReplyJob(props.id, {
    mode: replyMode.value,
    title: replyTitle.value.trim() || undefined,
    case_summary: replySummary.value.trim() || undefined,
    user_question: replyQuestion.value.trim() || undefined,
    assigned_agent_role: replyAgent.value || undefined,
  });
  replyTitle.value = "";
  replyQuestion.value = "";
  replySummary.value = "";
  await load();
}

async function processReplyJob(jobId: string) {
  processingId.value = jobId;
  try {
    await api.processReplyJob(props.id, jobId);
    await load();
  } finally {
    processingId.value = "";
  }
}

async function deleteReplyJob(jobId: string) {
  if (!armDelete(jobId)) return;
  await withDelete(jobId, async () => {
    await api.deleteReplyJob(props.id, jobId);
    await load();
  });
}

async function createFollowUp() {
  if (!followUpContent.value.trim()) return;
  await api.createFollowUpQuestion(props.id, followUpContent.value.trim());
  followUpContent.value = "";
  await load();
}

async function deleteFollowUp(questionId: string) {
  if (!armDelete(questionId)) return;
  await withDelete(questionId, async () => {
    await api.deleteFollowUpQuestion(props.id, questionId);
    await load();
  });
}

async function deleteReasoning(runId: string) {
  if (!armDelete(runId)) return;
  await withDelete(runId, async () => {
    await api.deleteReasoningRun(props.id, runId);
    await load();
  });
}

async function sendFollowUp(questionId: string) {
  try {
    const result = await api.sendFollowUpQuestion(props.id, questionId);
    actionMessage.value =
      result.question.status === "sent_via_openclaw"
        ? "追问已写入当前聊天通道。"
        : `发送失败：${result.question.failure_reason || "请检查聊天通道配置"}`;
  } catch (error) {
    actionMessage.value = error instanceof Error ? error.message : "发送失败";
  }
  await load();
}

function caseTypeLabel(type: string) {
  return {
    contract: "合同纠纷",
    labor: "劳动争议",
    marriage: "婚姻家事",
    debt: "债权债务",
    traffic: "交通事故",
    company: "公司商事",
    real_estate: "房产纠纷",
    criminal: "刑事咨询",
    other: "其他",
  }[type] ?? type;
}

function caseStatusLabel(status: string) {
  return {
    open: "进行中",
    collecting_info: "信息收集中",
    closed: "已关闭",
  }[status] ?? status;
}

function taskStatusLabel(status: string) {
  return {
    todo: "待办",
    in_progress: "进行中",
    doing: "进行中",
    waiting_user: "等客户",
    waiting_owner_review: "待复核",
    done: "已完成",
    blocked: "受阻",
  }[status] ?? status;
}

function taskStatusTone(status: string): "blue" | "green" | "amber" | "red" | "slate" {
  if (status === "done") return "green";
  if (status === "in_progress") return "blue";
  if (status === "waiting_owner_review" || status === "waiting_user") return "amber";
  if (status === "blocked") return "red";
  return "slate";
}

function taskTypeLabel(type: string) {
  return {
    general: "通用",
    similar_case_search: "类案检索",
    regulation_search: "法规检索",
    document_review: "文档审查",
    document_drafting: "文档撰写",
    client_reply: "客户回复",
    reasoning: "案件推理",
  }[type] ?? type;
}

function taskTypeTone(type: string): "blue" | "green" | "amber" | "red" | "slate" {
  if (type === "similar_case_search" || type === "regulation_search") return "blue";
  if (type === "document_review") return "amber";
  if (type === "document_drafting") return "green";
  return "slate";
}

function priorityLabel(priority: string) {
  return {
    low: "低优先级",
    medium: "普通优先级",
    normal: "普通优先级",
    high: "高优先级",
    urgent: "紧急",
  }[priority] ?? priority;
}

function memoryKindLabel(kind: string) {
  return {
    fact: "事实",
    timeline: "时间线",
    evidence: "证据",
    uncertainty: "不确定点",
    note: "备注",
  }[kind] ?? kind;
}

function documentTypeLabel(type: string) {
  return {
    contract: "合同",
    letter: "函件",
    pleading: "文书",
    evidence: "证据",
    other: "其他",
  }[type] ?? type;
}

function replyModeLabel(mode: string) {
  return {
    short_reply: "短回复",
    long_reply: "长回复",
  }[mode] ?? mode;
}

function replyStatusLabel(status: string) {
  return {
    queued: "排队中",
    reasoning: "推理中",
    ready_for_review: "待复核",
    completed: "已完成",
    failed: "失败",
  }[status] ?? status;
}

function replyStatusTone(status: string): "blue" | "green" | "amber" | "red" | "slate" {
  if (status === "completed" || status === "ready_for_review") return "green";
  if (status === "reasoning") return "blue";
  if (status === "failed") return "red";
  if (status === "queued") return "amber";
  return "slate";
}

function nodeTypeLabel(type: string) {
  return {
    Conclusion: "结论",
    Uncertainty: "不确定点",
    Question: "问题",
    Issue: "争点",
    Fact: "事实",
    Evidence: "证据",
    Rule: "规则",
    Analysis: "分析",
  }[type] ?? type;
}

function reasoningStatusLabel(status: string) {
  return {
    draft: "草稿",
    needs_evidence: "等待补证",
    ready_for_review: "待复核",
    confirmed: "已确认",
  }[status] ?? status;
}

function questionStatusLabel(status: string) {
  return {
    pending: "待发送",
    sent_via_openclaw: "已通过微信桥发送",
    failed: "发送失败",
  }[status] ?? status;
}

function senderLabel(sender: string) {
  return {
    wechat_user: "客户",
    openclaw_auto: "微信桥自动回复",
    owner: "电脑端",
    system: "系统",
  }[sender] ?? sender;
}

function messageStatusLabel(status: string) {
  return {
    synced: "已同步",
    sent: "已发送",
    openclaw_auto_replied: "微信桥已自动回复",
    pending: "待发送",
    failed: "发送失败",
    sent_via_openclaw: "已通过微信桥发送",
  }[status] ?? status;
}

function messageLabel(message: { sender: string; status: string; source?: string | null }): string {
  if (message.sender === "wechat_user") return "客户消息";
  if (message.sender === "owner") {
    if (message.source === "mock") return "AI短回复";
    if (message.source === "manual") return "人工回复";
    return "人工回复";
  }
  return `${senderLabel(message.sender)} · ${messageStatusLabel(message.status)}`;
}

function agentTitleLabel(value?: string | null) {
  return value ? value.replaceAll("Agent", "智能体") : "未分配";
}

function toneFor(type: string): "blue" | "green" | "amber" | "red" | "slate" {
  if (type === "Conclusion") return "green";
  if (type === "Uncertainty" || type === "Question") return "amber";
  if (type === "Issue") return "blue";
  return "slate";
}

function shortTime(value: string) {
  return new Date(value).toLocaleString();
}

function tabFromPath(path: string) {
  if (path.endsWith("/chat")) return "chat";
  if (path.endsWith("/tasks")) return "overview";
  if (path.endsWith("/memory")) return "facts";
  if (path.endsWith("/documents")) return "documents";
  if (path.endsWith("/workflow")) return "workflow";
  if (path.endsWith("/reasoning")) return "reasoning";
  return "overview";
}

onMounted(async () => {
  await Promise.all([load(), api.agents().then((items) => (agents.value = items))]);
});
</script>

<style scoped>
.task-board {
  display: grid;
  grid-template-columns: repeat(5, minmax(180px, 1fr));
  gap: 12px;
  align-items: start;
}

.task-column {
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px;
  background: var(--surface);
}

.task-column-head,
.task-card-head,
.task-actions,
.task-links,
.task-comment-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.task-card {
  display: grid;
  gap: 8px;
  margin-top: 10px;
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
}

.task-card-title {
  margin: 0;
  font-size: 15px;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.task-result {
  margin: 0;
  padding: 8px;
  border-radius: 6px;
  background: var(--surface-muted);
  font-size: 13px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.research-result-list {
  display: grid;
  gap: 8px;
}

.research-result {
  padding: 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
}

.research-result ul {
  margin: 6px 0 0;
  padding-left: 18px;
  font-size: 12px;
  line-height: 1.5;
}

.textarea.compact {
  min-height: 72px;
}

.input.compact {
  min-width: 0;
}

.button.tiny {
  padding: 6px 8px;
  font-size: 12px;
  line-height: 1.2;
}

.empty-state.compact {
  margin-top: 10px;
  padding: 12px;
}

@media (max-width: 1200px) {
  .task-board {
    grid-template-columns: repeat(2, minmax(220px, 1fr));
  }
}

@media (max-width: 720px) {
  .task-board {
    grid-template-columns: 1fr;
  }
}
</style>
