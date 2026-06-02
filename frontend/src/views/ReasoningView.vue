<template>
  <PageHeader title="推理分析" description="独立法律推理模块：生成可审查推理图和待追问问题。">
    <select v-model="selectedCaseId" class="select" style="width: 260px">
      <option v-for="item in cases" :key="item.id" :value="item.id">{{ item.title }}</option>
    </select>
    <button class="button primary" :disabled="!selectedCaseId" @click="generate">生成</button>
  </PageHeader>
  <section class="page-content">
    <div v-if="run" class="grid cols-2">
      <section class="panel">
        <h2 class="panel-title">推理图</h2>
        <p class="panel-subtitle">节点是结构化推理摘要，不展示模型内部长链思考。</p>
        <div class="reasoning-summary">
          <Badge :tone="run.status === 'needs_evidence' ? 'amber' : 'green'">
            {{ reasoningStatusLabel(run.status) }}
          </Badge>
          <p class="muted small">{{ run.output_summary }}</p>
          <p v-if="run.blocked_reason" class="muted small">暂停点：{{ run.blocked_reason }}</p>
          <div class="agent-chip-row">
            <span v-for="item in run.review_focus" :key="item" class="agent-chip">{{ item }}</span>
          </div>
        </div>
        <div class="reasoning-canvas">
          <article v-for="node in run.nodes" :key="node.id" class="reasoning-node">
            <Badge :tone="toneFor(node.node_type)">{{ nodeTypeLabel(node.node_type) }}</Badge>
            <h3>{{ node.label }}</h3>
            <p class="muted small">{{ node.content }}</p>
            <div class="small">置信度 {{ Math.round(node.confidence * 100) }}%</div>
          </article>
        </div>
      </section>
      <section class="panel">
        <h2 class="panel-title">待追问问题</h2>
        <p class="panel-subtitle">可以一键发送到当前聊天通道。</p>
        <div v-if="actionMessage" class="muted small" style="margin-bottom: 10px">{{ actionMessage }}</div>
        <div v-for="question in detail?.follow_up_questions ?? []" :key="question.id" class="list-item follow-up-row">
          <div>
            <strong>{{ question.content }}</strong>
            <div class="muted small">{{ questionStatusLabel(question.status) }} {{ question.failure_reason || "" }}</div>
          </div>
          <button
            class="button primary"
            :disabled="!detail?.case.conversation_ref || question.status === 'sent_via_openclaw'"
            @click="sendFollowUp(question.id)"
          >
            发送
          </button>
        </div>
        <h2 class="panel-title" style="margin-top: 20px">边关系</h2>
        <div v-for="edge in run.edges" :key="edge.id" class="list-item small">
          {{ edge.source }} → {{ edge.target }} · {{ relationLabel(edge.relation_type) }}
        </div>
      </section>
    </div>
    <section v-else class="panel">
      <h2 class="panel-title">尚未生成</h2>
        <p class="panel-subtitle">选择案件后生成第一版推理图。</p>
    </section>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from "vue";

import Badge from "@/components/Badge.vue";
import PageHeader from "@/components/PageHeader.vue";
import { api } from "@/services/api";
import type { CaseItem, LegalReasoningRun } from "@/types";

const cases = ref<CaseItem[]>([]);
const selectedCaseId = ref("");
const run = ref<LegalReasoningRun | null>(null);
const detail = ref<Awaited<ReturnType<typeof api.caseDetail>> | null>(null);
const actionMessage = ref("");

async function generate() {
  if (!selectedCaseId.value) return;
  run.value = await api.generateReasoning(selectedCaseId.value);
  detail.value = await api.caseDetail(selectedCaseId.value);
}

async function loadDetail() {
  actionMessage.value = "";
  detail.value = selectedCaseId.value ? await api.caseDetail(selectedCaseId.value) : null;
  const runs = detail.value?.reasoning_runs ?? [];
  run.value = runs.length ? runs[runs.length - 1] : null;
}

async function sendFollowUp(questionId: string) {
  if (!selectedCaseId.value) return;
  try {
    const result = await api.sendFollowUpQuestion(selectedCaseId.value, questionId);
    actionMessage.value =
      result.question.status === "sent_via_openclaw"
        ? "追问已写入当前聊天通道。"
        : `发送失败：${result.question.failure_reason || "请检查聊天通道配置"}`;
  } catch (error) {
    actionMessage.value = error instanceof Error ? error.message : "发送失败";
  }
  detail.value = await api.caseDetail(selectedCaseId.value);
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

function questionStatusLabel(status: string) {
  return {
    pending: "待发送",
    sent_via_openclaw: "已通过微信桥发送",
    failed: "发送失败",
  }[status] ?? status;
}

function relationLabel(type: string) {
  return {
    supports: "支持",
    contradicts: "矛盾",
    depends_on: "依赖",
    requires: "需要",
    leads_to: "导向",
    uncertain_about: "不确定",
    asks: "追问",
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

function toneFor(type: string): "blue" | "green" | "amber" | "red" | "slate" {
  if (type === "Conclusion") return "green";
  if (type === "Uncertainty" || type === "Question") return "amber";
  if (type === "Issue") return "blue";
  return "slate";
}

onMounted(async () => {
  cases.value = await api.cases();
  selectedCaseId.value = cases.value[0]?.id ?? "";
  await loadDetail();
});

watch(selectedCaseId, loadDetail);
</script>
