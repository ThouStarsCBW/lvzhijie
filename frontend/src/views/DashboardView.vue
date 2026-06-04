<template>
  <PageHeader title="总览" description="核心法律能力集成在同一个个人法律智能工作台内。">
    <button class="button" @click="load">刷新</button>
    <RouterLink class="button primary" to="/wechat">进入客户工作台</RouterLink>
  </PageHeader>

  <section class="page-content">
    <section class="mission-surface">
      <div>
        <Badge :tone="openclawOnline ? 'green' : 'amber'">
          {{ openclawOnline ? "微信桥已连接" : "微信桥待配置" }}
        </Badge>
        <h2>律智界指挥台</h2>
        <p>
          微信桥只负责消息通道，案件、文件、推理和律所智能体全部在本系统内独立运行。
        </p>
      </div>
      <div class="mission-metrics">
        <div>
          <strong>{{ numberOf("conversations") }}</strong>
          <span>客户会话</span>
        </div>
        <div>
          <strong>{{ numberOf("open_cases") }}</strong>
          <span>未关闭案件</span>
        </div>
        <div>
          <strong>{{ numberOf("documents") }}</strong>
          <span>法律文件</span>
        </div>
        <div>
          <strong>{{ numberOf("queued_reply_jobs") }}</strong>
          <span>待处理回复</span>
        </div>
      </div>
    </section>

    <section class="core-grid" aria-label="核心功能">
      <RouterLink v-for="module in modules" :key="module.title" :to="module.to" class="module-panel">
        <div class="module-topline">
          <component :is="module.icon" class="module-icon" />
          <Badge :tone="module.tone">{{ module.status }}</Badge>
        </div>
        <h2>{{ module.title }}</h2>
        <p>{{ module.description }}</p>
        <div class="module-footer">
          <span>{{ module.metric }}</span>
          <span>{{ module.action }}</span>
        </div>
      </RouterLink>
    </section>

    <section class="panel" style="margin-top: 16px">
      <h2 class="panel-title">最近活动</h2>
      <p class="panel-subtitle">客户同步、建案、文件版本和推理生成在这里汇总。</p>
      <div v-for="event in activity.slice(0, 5)" :key="event.id" class="list-item compact">
        <strong>{{ localizeText(event.title) }}</strong>
        <div class="muted small">{{ localizeText(event.description || event.event_type) }}</div>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Bot, FileDiff, GitBranch, MessageCircle, Search } from "lucide-vue-next";

import Badge from "@/components/Badge.vue";
import PageHeader from "@/components/PageHeader.vue";
import { api } from "@/services/api";
import type { ActivityEvent } from "@/types";

const summary = ref<Record<string, unknown>>({});
const activity = ref<ActivityEvent[]>([]);

const openclaw = computed(() => summary.value.openclaw as Record<string, unknown> | undefined);
const openclawOnline = computed(() => Boolean(openclaw.value?.online));
const openclawMessage = computed(() => String(openclaw.value?.message ?? "尚未检查"));
type BadgeTone = "blue" | "green" | "amber" | "red" | "slate";

const modules = computed(() => [
  {
    title: "1. 客户接入",
    description: "读取客户会话、同步聊天、电脑端通过微信桥发消息。",
    metric: `${numberOf("conversations")} 个会话 / ${numberOf("messages")} 条消息`,
    status: openclawOnline.value ? "已连接" : "待配置",
    tone: (openclawOnline.value ? "green" : "amber") as BadgeTone,
    action: "打开客户工作台",
    to: "/wechat",
    icon: MessageCircle,
  },
  {
    title: "2. 法律文件版本控制",
    description: "上传文本和文档，维护版本历史，逐字比对并提示合同风险。",
    metric: `${numberOf("documents")} 份文件`,
    status: "版本管理",
    tone: "blue" as BadgeTone,
    action: "查看文件库",
    to: "/documents",
    icon: FileDiff,
  },
  {
    title: "3. 类案与法规检索",
    description: "以案件事实为上下文生成类案、法规和裁判规则检索方向。",
    metric: `${numberOf("research_runs")} 次检索 / ${numberOf("research_results")} 条结果`,
    status: "法律检索",
    tone: "blue" as BadgeTone,
    action: "进入检索中心",
    to: "/research",
    icon: Search,
  },
  {
    title: "4. 案件管理与推理分析",
    description: "以案件为业务容器，沉淀事实、证据、任务、推理图、追问和回复工作流。",
    metric: `${numberOf("cases")} 个案件 / ${numberOf("reasoning_runs")} 次推理 / ${numberOf("reply_jobs")} 个回复任务`,
    status: "案件中枢",
    tone: "green" as BadgeTone,
    action: "进入案件中心",
    to: "/cases",
    icon: GitBranch,
  },
  {
    title: "5. 仿律所智能体协同",
    description: "主任律师、接待、秘书、承办、合同审查、诉讼策略等角色协同。",
    metric: "9 个律所角色",
    status: "角色协同",
    tone: "slate" as BadgeTone,
    action: "查看智能体",
    to: "/agents",
    icon: Bot,
  },
]);

function numberOf(key: string) {
  return Number(summary.value[key] ?? 0);
}

async function load() {
  summary.value = await api.summary();
  activity.value = await api.activity();
}

function localizeText(value: unknown) {
  return String(value ?? "")
    .replaceAll("OpenClaw", "微信桥")
    .replaceAll("Gateway", "网关")
    .replaceAll("wechat.synced", "客户已同步")
    .replaceAll("case.created", "案件已创建")
    .replaceAll("conversation", "会话")
    .replaceAll("case", "案件");
}

onMounted(load);
</script>
