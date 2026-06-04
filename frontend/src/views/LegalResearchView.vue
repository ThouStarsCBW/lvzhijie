<template>
  <PageHeader title="类案与法规检索" description="围绕案件事实生成类案、法规和裁判规则检索方向。">
    <button class="button" @click="load">刷新</button>
    <RouterLink v-if="selectedCaseId" class="button primary" :to="`/cases/${selectedCaseId}/tasks`">
      查看任务中心
    </RouterLink>
  </PageHeader>

  <section class="page-content">
    <section class="grid cols-2">
      <section class="panel">
        <h2 class="panel-title">发起检索</h2>
        <p class="panel-subtitle">检索会作为案件任务创建，并把结果沉淀回案件。</p>

        <select v-model="selectedCaseId" class="select">
          <option value="">选择案件</option>
          <option v-for="item in cases" :key="item.id" :value="item.id">
            {{ item.title }}
          </option>
        </select>

        <div class="search-mode-tabs">
          <button
            v-for="item in modes"
            :key="item.value"
            :class="['button', searchMode === item.value && 'primary']"
            @click="searchMode = item.value"
          >
            {{ item.label }}
          </button>
        </div>

        <textarea
          v-model="query"
          class="textarea"
          placeholder="输入争议焦点、案情摘要、关键词或希望核验的问题"
        />
        <input
          v-model="keywordInput"
          class="input"
          placeholder="可选关键词，用空格、顿号或逗号分隔"
        />

        <div class="form-actions">
          <button class="button primary" :disabled="!selectedCaseId || running" @click="runSearch">
            {{ running ? "检索中" : "创建并执行检索任务" }}
          </button>
        </div>
        <div v-if="actionMessage" class="muted small">{{ actionMessage }}</div>
      </section>

      <section class="panel">
        <h2 class="panel-title">当前案件</h2>
        <p class="panel-subtitle">检索上下文来自案件摘要、记忆、文件和任务记录。</p>
        <div v-if="selectedCase" class="case-summary">
          <Badge tone="blue">{{ caseTypeLabel(selectedCase.case_type) }}</Badge>
          <h3>{{ selectedCase.title }}</h3>
          <p>{{ selectedCase.summary || "暂无摘要。" }}</p>
        </div>
        <div v-else class="empty-state">请选择一个案件。</div>
      </section>
    </section>

    <section class="grid cols-2" style="margin-top: 16px">
      <section class="panel">
        <h2 class="panel-title">检索任务</h2>
        <div v-for="task in searchTasks" :key="task.id" class="list-item research-task">
          <div>
            <Badge :tone="task.task_type === 'similar_case_search' ? 'blue' : 'green'">
              {{ taskTypeLabel(task.task_type) }}
            </Badge>
            <Badge :tone="taskStatusTone(task.status)" style="margin-left: 6px">
              {{ taskStatusLabel(task.status) }}
            </Badge>
            <h3>{{ task.title }}</h3>
            <p class="muted small">{{ task.result_summary || task.description }}</p>
          </div>
          <RouterLink class="button" :to="`/cases/${task.case_id}/tasks`">打开</RouterLink>
        </div>
        <div v-if="!searchTasks.length" class="empty-state">暂无检索任务。</div>
      </section>

      <section class="panel">
        <h2 class="panel-title">检索结果</h2>
        <article v-for="result in filteredResults" :key="result.id" class="research-card">
          <div class="research-card-head">
            <Badge :tone="result.result_type === 'similar_case' ? 'blue' : 'green'">
              {{ resultTypeLabel(result.result_type) }}
            </Badge>
            <span class="muted small">相关度 {{ Math.round(result.relevance_score * 100) }}%</span>
          </div>
          <h3>{{ result.title }}</h3>
          <p class="muted small">
            {{ result.source }} · {{ result.court_or_authority || "未知发布/裁判机构" }} · {{ result.reference }}
          </p>
          <ul>
            <li v-for="point in result.key_points" :key="point">{{ point }}</li>
          </ul>
          <div v-if="result.result_type === 'regulation' && result.external_id" class="form-actions">
            <button class="button" :disabled="loadingLawDetailId === result.id" @click="loadLawDetail(result)">
              {{ loadingLawDetailId === result.id ? "加载中" : "查看法规原文" }}
            </button>
          </div>
          <pre v-if="lawDetails[result.id]" class="law-detail">{{ lawDetails[result.id] }}</pre>
        </article>
        <div v-if="!filteredResults.length" class="empty-state">暂无检索结果。</div>
      </section>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import Badge from "@/components/Badge.vue";
import PageHeader from "@/components/PageHeader.vue";
import { api } from "@/services/api";
import type { CaseItem, CaseTask, LegalResearchResult } from "@/types";

const cases = ref<CaseItem[]>([]);
const selectedCaseId = ref("");
const detail = ref<Awaited<ReturnType<typeof api.caseDetail>> | null>(null);
const searchMode = ref<"similar_case_search" | "regulation_search">("similar_case_search");
const query = ref("");
const keywordInput = ref("");
const running = ref(false);
const actionMessage = ref("");
const lawDetails = ref<Record<string, string>>({});
const loadingLawDetailId = ref("");

const modes = [
  { value: "similar_case_search" as const, label: "类案检索" },
  { value: "regulation_search" as const, label: "法规检索" },
];

const selectedCase = computed(() => cases.value.find((item) => item.id === selectedCaseId.value) ?? null);

const searchTasks = computed(() =>
  (detail.value?.tasks ?? []).filter((task) =>
    ["similar_case_search", "regulation_search"].includes(task.task_type),
  ),
);

const filteredResults = computed(() => {
  const expectedType = searchMode.value === "similar_case_search" ? "similar_case" : "regulation";
  return (detail.value?.research_results ?? []).filter((result) => result.result_type === expectedType);
});

async function load() {
  cases.value = await api.cases();
  if (!selectedCaseId.value && cases.value.length) {
    selectedCaseId.value = cases.value[0].id;
  }
  await loadDetail();
}

async function loadDetail() {
  if (!selectedCaseId.value) {
    detail.value = null;
    return;
  }
  detail.value = await api.caseDetail(selectedCaseId.value);
}

function keywordList() {
  return keywordInput.value
    .split(/[\s,，、]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

async function runSearch() {
  if (!selectedCaseId.value) return;
  running.value = true;
  actionMessage.value = "";
  const taskType = searchMode.value;
  const label = taskType === "similar_case_search" ? "类案检索" : "法规检索";
  const searchQuery = query.value.trim() || selectedCase.value?.summary || selectedCase.value?.title || "";
  try {
    const task = await api.createTask(selectedCaseId.value, {
      title: `${label}：${searchQuery.slice(0, 32) || selectedCase.value?.title || "案件检索"}`,
      description: searchQuery,
      task_type: taskType,
      assigned_agent_role: "法律检索 Agent",
      priority: "medium",
      metadata: { query: searchQuery, keywords: keywordList() },
    });
    const executed = await api.executeTask(selectedCaseId.value, task.id, {
      query: searchQuery,
      keywords: keywordList(),
    });
    if (executed.status === "blocked") {
      actionMessage.value = executed.result_summary || `${label}真实 API 调用失败，请查看任务中心。`;
      await loadDetail();
      return;
    }
    actionMessage.value = `${label}任务已创建并执行，结果已写回案件。`;
    query.value = "";
    keywordInput.value = "";
    await loadDetail();
  } catch (error) {
    actionMessage.value = error instanceof Error ? error.message : "检索失败";
  } finally {
    running.value = false;
  }
}

async function loadLawDetail(result: LegalResearchResult) {
  if (!result.external_id) return;
  loadingLawDetailId.value = result.id;
  try {
    const detail = await api.lawDetail(result.external_id);
    lawDetails.value = {
      ...lawDetails.value,
      [result.id]: detail.body?.law_detail_content || detail.body?.title || detail.msg || "未返回法规原文。",
    };
  } catch (error) {
    lawDetails.value = {
      ...lawDetails.value,
      [result.id]: error instanceof Error ? error.message : "法规详情获取失败",
    };
  } finally {
    loadingLawDetailId.value = "";
  }
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

function taskTypeLabel(type: CaseTask["task_type"]) {
  return type === "similar_case_search" ? "类案检索" : "法规检索";
}

function taskStatusLabel(status: string) {
  return {
    todo: "待办",
    in_progress: "进行中",
    waiting_owner_review: "待复核",
    done: "已完成",
    blocked: "受阻",
  }[status] ?? status;
}

function taskStatusTone(status: string): "blue" | "green" | "amber" | "red" | "slate" {
  if (status === "done") return "green";
  if (status === "waiting_owner_review") return "amber";
  if (status === "blocked") return "red";
  if (status === "in_progress") return "blue";
  return "slate";
}

function resultTypeLabel(type: string) {
  return type === "similar_case" ? "类案" : "法规";
}

watch(selectedCaseId, loadDetail);
onMounted(load);
</script>

<style scoped>
.search-mode-tabs {
  display: flex;
  gap: 8px;
  margin: 10px 0;
}

.case-summary h3,
.research-task h3,
.research-card h3 {
  margin: 8px 0 4px;
  font-size: 16px;
}

.research-card {
  display: grid;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
}

.research-card + .research-card {
  margin-top: 10px;
}

.research-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.research-card ul {
  margin: 0;
  padding-left: 18px;
  line-height: 1.6;
}

.law-detail {
  max-height: 260px;
  overflow: auto;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface-muted);
  white-space: pre-wrap;
  line-height: 1.6;
}
</style>
