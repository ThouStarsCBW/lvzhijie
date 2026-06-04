<template>
  <div class="flowchart-shell">
    <div class="flowchart-legend">
      <span v-for="item in statusLegend" :key="item.status" :class="['flowchart-legend-item', `is-${item.status}`]">
        {{ item.label }}
      </span>
    </div>

    <div class="flowchart-stage">
      <div v-if="renderError" class="empty-state">{{ renderError }}</div>
      <div v-else ref="chartEl" class="flowchart-svg" v-html="svgMarkup" />
    </div>

    <div class="reasoning-node-list">
      <button
        v-for="node in run.nodes"
        :key="node.id"
        type="button"
        :class="['reasoning-node', `is-${node.status || 'probable'}`, selectedNodeId === node.id && 'is-selected']"
        @click="selectedNodeId = node.id"
      >
        <span class="node-meta">
          {{ nodeTypeLabel(node.node_type) }} · {{ nodeStatusLabel(node.status) }}
        </span>
        <strong>{{ node.label }}</strong>
        <span class="muted small">{{ node.content }}</span>
      </button>
    </div>

    <div v-if="selectedNode" class="flowchart-inspector">
      <div>
        <span class="node-meta">{{ nodeTypeLabel(selectedNode.node_type) }}</span>
        <h3>{{ selectedNode.label }}</h3>
      </div>
      <p>{{ selectedNode.content }}</p>
      <div class="agent-chip-row">
        <span class="agent-chip">{{ nodeStatusLabel(selectedNode.status) }}</span>
        <span class="agent-chip">置信度 {{ Math.round(selectedNode.confidence * 100) }}%</span>
        <span v-for="ref in selectedNode.source_refs" :key="ref" class="agent-chip">{{ ref }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import mermaid from "mermaid";
import { computed, nextTick, ref, watch } from "vue";

import type { LegalReasoningRun, ReasoningEdge, ReasoningNode } from "@/types";

const props = defineProps<{
  run: LegalReasoningRun;
}>();

mermaid.initialize({
  startOnLoad: false,
  securityLevel: "strict",
  theme: "base",
  themeVariables: {
    fontFamily: "Inter, Microsoft YaHei, system-ui, sans-serif",
    primaryColor: "#eff6ff",
    primaryBorderColor: "#2563eb",
    primaryTextColor: "#172554",
    lineColor: "#64748b",
    tertiaryColor: "#f8fafc",
  },
});

const chartEl = ref<HTMLElement | null>(null);
const svgMarkup = ref("");
const renderError = ref("");
const selectedNodeId = ref("");

const statusLegend = [
  { status: "verified", label: "已证实" },
  { status: "probable", label: "合理推断" },
  { status: "unverified", label: "无法证实" },
  { status: "missing", label: "待补全" },
  { status: "conflict", label: "证据冲突" },
];

const selectedNode = computed(() => {
  return props.run.nodes.find((node) => node.id === selectedNodeId.value) ?? props.run.nodes[0] ?? null;
});

function cleanLabel(value: string) {
  return value
    .replace(/\s+/g, " ")
    .slice(0, 96)
    .replaceAll('"', "'")
    .replaceAll("[", "【")
    .replaceAll("]", "】")
    .replaceAll("|", "｜");
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

function nodeTypeLabel(type: string) {
  return {
    Conclusion: "结论",
    Uncertainty: "不确定点",
    Question: "问题",
    Issue: "争点",
    Fact: "事实",
    Evidence: "证据",
    Timeline: "时间线",
    Rule: "规则",
    Analysis: "分析",
  }[type] ?? type;
}

function nodeStatusLabel(status?: string) {
  return {
    verified: "已证实",
    probable: "合理推断",
    unverified: "无法证实",
    missing: "待补全",
    conflict: "证据冲突",
  }[status || "probable"] ?? status ?? "合理推断";
}

function buildClientMermaid(nodes: ReasoningNode[], edges: ReasoningEdge[]) {
  const nodeIds = new Set(nodes.map((node) => node.id));
  const lines = ["flowchart TD"];
  for (const node of nodes) {
    const status = node.status || "probable";
    lines.push(`  ${node.id}["${cleanLabel(`${nodeTypeLabel(node.node_type)}：${node.label}<br/>${nodeStatusLabel(status)}`)}"]`);
  }
  for (const edge of edges) {
    if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) continue;
    lines.push(`  ${edge.source} -->|${cleanLabel(edge.label || relationLabel(edge.relation_type))}| ${edge.target}`);
  }
  lines.push(
    "  classDef verified fill:#dcfce7,stroke:#16a34a,color:#14532d",
    "  classDef probable fill:#dbeafe,stroke:#2563eb,color:#1e3a8a",
    "  classDef unverified fill:#fef3c7,stroke:#d97706,color:#78350f",
    "  classDef missing fill:#f1f5f9,stroke:#64748b,stroke-dasharray:5 4,color:#334155",
    "  classDef conflict fill:#fee2e2,stroke:#dc2626,color:#7f1d1d",
  );
  for (const node of nodes) {
    lines.push(`  class ${node.id} ${node.status || "probable"}`);
  }
  return lines.join("\n");
}

async function renderChart() {
  renderError.value = "";
  svgMarkup.value = "";
  await nextTick();
  const source = props.run.mermaid_source || buildClientMermaid(props.run.nodes, props.run.edges);
  if (!source.trim()) {
    renderError.value = "暂无可渲染的推理图。";
    return;
  }
  try {
    const id = `reasoning-flowchart-${props.run.id}-${Date.now()}`;
    const result = await mermaid.render(id, source);
    svgMarkup.value = result.svg;
    selectedNodeId.value = props.run.nodes[0]?.id ?? "";
  } catch {
    renderError.value = "推理图渲染失败，已保留节点列表供复核。";
  }
}

watch(() => props.run, renderChart, { deep: true, immediate: true });
</script>
