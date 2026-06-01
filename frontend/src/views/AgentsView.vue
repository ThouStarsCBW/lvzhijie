<template>
  <PageHeader title="律所智能体" description="调度智能体统一分派，四类智能体组承接案件、服务、合规和档案能力。" />
  <section class="page-content">
    <section v-if="architecture" class="panel architecture-panel">
      <div class="architecture-root">
        <Badge tone="blue">调度</Badge>
        <h2>{{ agentDisplayTitle(architecture.dispatcher.title) }}</h2>
        <p class="muted small">{{ architecture.dispatcher.description }}</p>
      </div>
      <div class="architecture-line"></div>
      <div class="architecture-groups">
        <article v-for="group in architecture.groups" :key="group.id" class="architecture-group">
          <Badge :tone="groupTone(group.id)">{{ groupTitle(group.title) }}</Badge>
          <h3>{{ agentDisplayTitle(group.title) }}</h3>
          <p class="muted small">{{ group.description }}</p>
          <div class="agent-chip-row">
            <span v-for="role in group.agent_roles" :key="role" class="agent-chip">
              {{ agentTitle(role) }}
            </span>
          </div>
          <div v-if="group.departments.length" class="department-grid">
            <div v-for="department in group.departments" :key="department.id" class="department-item">
              <strong>{{ department.title }}</strong>
              <span>{{ department.description }}</span>
            </div>
          </div>
        </article>
      </div>
    </section>

    <div class="grid cols-3">
      <article v-for="agent in agents" :key="agent.id" class="panel">
        <Badge :tone="agent.active ? groupTone(agent.group) : 'slate'">{{ roleLabel(agent.role) }}</Badge>
        <h2 class="panel-title" style="margin-top: 12px">{{ agentDisplayTitle(agent.title) }}</h2>
        <p class="panel-subtitle">{{ agent.description }}</p>
        <div v-if="agent.reports_to" class="muted small" style="margin-bottom: 8px">
          上级：{{ agentTitle(agent.reports_to) }}
        </div>
        <ul>
          <li v-for="item in agent.responsibilities" :key="item">{{ item }}</li>
        </ul>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import Badge from "@/components/Badge.vue";
import PageHeader from "@/components/PageHeader.vue";
import { api } from "@/services/api";
import type { AgentArchitecture, LegalAgent } from "@/types";

const agents = ref<LegalAgent[]>([]);
const architecture = ref<AgentArchitecture | null>(null);
const agentByRole = computed(() => Object.fromEntries(agents.value.map((agent) => [agent.role, agent])));

onMounted(async () => {
  [agents.value, architecture.value] = await Promise.all([api.agents(), api.agentArchitecture()]);
});

function roleLabel(role: string) {
  return {
    managing_lawyer: "主任律师",
    dispatch_agent: "调度",
    core_business_agent: "核心业务",
    client_service_agent: "客户服务",
    compliance_review_agent: "合规审查",
    archive_management_agent: "档案管理",
    reception_lawyer: "客户接待",
    case_secretary: "案件秘书",
    handling_lawyer: "承办律师",
    contract_reviewer: "合同审查",
    litigation_strategist: "诉讼策略",
    legal_researcher: "法律检索",
    quality_control: "风险质控",
    drafting_lawyer: "文书起草",
  }[role] ?? role;
}

function groupTitle(title: string) {
  return title.replaceAll("Agent", "").trim();
}

function agentTitle(role: string) {
  const title = agentByRole.value[role]?.title;
  return title ? agentDisplayTitle(title) : role;
}

function agentDisplayTitle(title: string) {
  return title.replace(/\s*Agent/g, "智能体");
}

function groupTone(group: string): "blue" | "green" | "amber" | "red" | "slate" {
  if (group === "core_business" || group === "orchestration") return "blue";
  if (group === "client_service") return "green";
  if (group === "compliance_review") return "amber";
  if (group === "archive_management") return "slate";
  if (group === "dispatcher") return "blue";
  return "slate";
}
</script>
