<template>
  <PageHeader
    :title="selectedAgent ? agentDisplayTitle(selectedAgent.title) : '智能体会话'"
    :description="selectedAgent?.description || '选择一个律所智能体开展内部协同。'"
  >
    <RouterLink class="button" to="/agents">
      <ArrowLeft class="button-icon" />
      返回
    </RouterLink>
    <button class="button" type="button" @click="showChannels = true">
      <Cable class="button-icon" />
      通道
    </button>
  </PageHeader>

  <section class="page-content">
    <div class="agent-chat-workbench">
      <aside class="panel agent-list-panel">
        <h2 class="panel-title">律所智能体</h2>
        <p class="panel-subtitle">按角色进入对应会话。</p>
        <div class="agent-list">
          <RouterLink
            v-for="agent in agents"
            :key="agent.id"
            :to="`/agents/${agent.id}`"
            :class="['agent-list-link', agent.id === selectedAgent?.id && 'active']"
          >
            <Bot class="agent-list-icon" />
            <span>
              <strong>{{ agentDisplayTitle(agent.title) }}</strong>
              <small>{{ roleLabel(agent.role) }}</small>
            </span>
          </RouterLink>
        </div>
      </aside>

      <main class="panel agent-chat-panel">
        <div v-if="selectedAgent" class="agent-chat-head">
          <div>
            <Badge :tone="groupTone(selectedAgent.group)">{{ roleLabel(selectedAgent.role) }}</Badge>
            <h2>{{ agentDisplayTitle(selectedAgent.title) }}</h2>
            <p>{{ selectedAgent.description }}</p>
          </div>
          <Badge v-if="latestAgentMessage" :tone="sourceTone(latestAgentMessage.source)">
            {{ sourceLabel(latestAgentMessage.source) }}
          </Badge>
        </div>

        <div ref="messageListRef" class="agent-message-list">
          <div v-if="loadingMessages" class="empty-state">正在读取会话...</div>
          <div v-else-if="!messages.length" class="empty-state">暂无对话。</div>
          <template v-else>
            <article
              v-for="message in messages"
              :key="message.id"
              :class="['agent-message', message.sender === 'user' ? 'outbound' : 'inbound']"
            >
              <div class="agent-message-author">
                <span>{{ message.sender === "user" ? "我" : agentDisplayTitle(selectedAgent?.title || "智能体") }}</span>
                <small>{{ formatTime(message.created_at) }}</small>
              </div>
              <div class="message-text">{{ message.content }}</div>
              <div v-if="message.sender === 'agent'" class="agent-message-meta">
                <Badge :tone="sourceTone(message.source)">{{ sourceLabel(message.source) }}</Badge>
                <span v-if="message.model">{{ message.model }}</span>
              </div>
              <div
                v-if="message.sender === 'agent' && message.retrieved_contexts.length"
                class="agent-contexts"
              >
                <div class="agent-contexts-title">
                  <Database class="button-icon" />
                  本地资料依据
                </div>
                <div
                  v-for="context in message.retrieved_contexts"
                  :key="context.id"
                  class="agent-context-item"
                >
                  <div>
                    <strong>{{ context.title }}</strong>
                    <Badge tone="slate">{{ sourceTypeLabel(context.source_type) }}</Badge>
                  </div>
                  <p>{{ context.excerpt }}</p>
                </div>
              </div>
            </article>
          </template>
        </div>

        <form class="agent-composer" @submit.prevent="sendMessage">
          <textarea
            v-model="draft"
            class="textarea agent-input"
            :disabled="sending || !selectedAgent"
            placeholder="输入要咨询或分派给智能体的问题"
          />
          <button
            class="button primary agent-send-button"
            type="submit"
            :disabled="sending || !draft.trim() || !selectedAgent"
          >
            <Send class="button-icon" />
            {{ sending ? "发送中" : "发送" }}
          </button>
        </form>
        <p v-if="feedback" class="agent-feedback">{{ feedback }}</p>
      </main>
    </div>
  </section>

  <Teleport to="body">
    <div v-if="showChannels" class="channel-backdrop" @click.self="showChannels = false">
      <section class="channel-modal" role="dialog" aria-modal="true">
        <button class="channel-close" type="button" aria-label="关闭" @click="showChannels = false">
          <X class="channel-icon" />
        </button>
        <div v-if="channelApplyNotice" class="channel-success-pop" role="status">
          {{ channelApplyNotice }}
        </div>
        <div class="channel-picker">
          <button class="channel-select" type="button" @click="showChannelOptions = !showChannelOptions">
            <span>{{ activeSetupChannel || "选择通讯工具" }}</span>
            <ChevronDown class="channel-icon" />
          </button>
          <div v-if="showChannelOptions" class="channel-options">
            <button
              v-for="channel in setupChannels"
              :key="channel"
              type="button"
              :class="['channel-option', activeSetupChannel === channel && 'checked']"
              @click="selectSetupChannel(channel)"
            >
              <span class="channel-radio">
                <span v-if="activeSetupChannel === channel"></span>
              </span>
              <span>{{ channel }}</span>
            </button>
          </div>
        </div>

        <section v-if="activeSetupChannel" class="channel-config">
          <div class="channel-config-tabs">
            <button
              :class="['channel-config-tab', configMode === 'quick' && 'active']"
              type="button"
              @click="configMode = 'quick'"
            >
              快捷配置
            </button>
            <button
              :class="['channel-config-tab', configMode === 'manual' && 'active']"
              type="button"
              @click="configMode = 'manual'"
            >
              手动配置
            </button>
          </div>
          <div v-if="configMode === 'quick'" class="channel-qr-panel">
            <div class="channel-qr-code" aria-label="模拟二维码">
              <span v-for="index in 49" :key="index" :class="['channel-qr-cell', qrCellClass(index)]"></span>
            </div>
            <p>{{ activeSetupChannel }}扫码授权接入</p>
          </div>
          <template v-else>
            <input
              class="channel-config-input"
              :value="configValue('appId')"
              :placeholder="`${activeSetupChannel}机器人的App ID`"
              @input="updateConfigValue('appId', $event)"
            />
            <div class="channel-secret-row">
              <input
                class="channel-config-input"
                :type="showSecret ? 'text' : 'password'"
                :value="configValue('appSecret')"
                :placeholder="`${activeSetupChannel}机器人的App Secret`"
                @input="updateConfigValue('appSecret', $event)"
              />
              <button class="channel-secret-toggle" type="button" @click="showSecret = !showSecret">
                <EyeOff class="channel-icon" />
              </button>
            </div>
          </template>
          <button class="channel-auth" type="button" @click="applyChannelConfig">
            添加并应用
          </button>
        </section>

        <p class="channel-copy">接入即时通信工具，成为你的专属助理。</p>
        <div class="channel-divider"></div>
        <h3 class="channel-title">已接入通道</h3>
        <div class="channel-list">
          <article v-for="channel in connectedChannels" :key="channel.name" class="channel-card">
            <div
              class="channel-row"
              role="button"
              tabindex="0"
              @click="toggleConnectedChannel(channel.name)"
              @keydown.enter.prevent="toggleConnectedChannel(channel.name)"
              @keydown.space.prevent="toggleConnectedChannel(channel.name)"
            >
              <div class="channel-name">
                <ChevronDown v-if="expandedConnectedChannel === channel.name" class="channel-icon" />
                <ChevronRight v-else class="channel-icon" />
                <strong>{{ channel.name }}</strong>
              </div>
              <div class="channel-status">
                <span class="channel-dot"></span>
                <span>已接入</span>
                <span class="channel-separator"></span>
                <button
                  class="channel-delete"
                  type="button"
                  :aria-label="`移除${channel.name}`"
                  @click.stop
                >
                  <Trash2 class="channel-icon" />
                </button>
              </div>
            </div>
            <div v-if="expandedConnectedChannel === channel.name" class="channel-detail">
              <template v-if="channel.kind === 'credentials'">
                <p>appId： {{ channel.appId }}</p>
                <p>{{ channel.secretLabel }}： {{ channel.secret }}</p>
              </template>
              <p v-else>{{ channel.detail }}</p>
            </div>
          </article>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  ArrowLeft,
  Bot,
  Cable,
  ChevronDown,
  ChevronRight,
  Database,
  EyeOff,
  Send,
  Trash2,
  X,
} from "lucide-vue-next";

import Badge from "@/components/Badge.vue";
import PageHeader from "@/components/PageHeader.vue";
import { api } from "@/services/api";
import type { AgentChatMessage, AgentRetrievedContext, LegalAgent } from "@/types";

const route = useRoute();
const router = useRouter();

const agents = ref<LegalAgent[]>([]);
const messages = ref<AgentChatMessage[]>([]);
const draft = ref("");
const feedback = ref("");
const loadingMessages = ref(false);
const sending = ref(false);
const showChannels = ref(false);
const showChannelOptions = ref(false);
const showSecret = ref(false);
const configMode = ref<"quick" | "manual">("manual");
const activeSetupChannel = ref<SetupChannelName>("QQ");
const expandedConnectedChannel = ref<ConnectedChannelName | null>(null);
const channelApplyNotice = ref("");
const messageListRef = ref<HTMLElement | null>(null);
let channelSuccessTimer: number | null = null;

type SetupChannelName = "微信" | "QQ" | "企业微信" | "元宝" | "飞书" | "钉钉";
type ConnectedChannelName = "QQ" | "元宝" | "飞书" | "微信";
type ConfigField = "appId" | "appSecret";

const setupChannels: SetupChannelName[] = ["微信", "QQ", "企业微信", "元宝", "飞书", "钉钉"];

const configValues = ref<Record<SetupChannelName, Record<ConfigField, string>>>({
  微信: { appId: "", appSecret: "" },
  QQ: { appId: "", appSecret: "" },
  企业微信: { appId: "", appSecret: "" },
  元宝: { appId: "", appSecret: "" },
  飞书: { appId: "", appSecret: "" },
  钉钉: { appId: "", appSecret: "" },
});

const connectedChannels: Array<
  | {
      name: Exclude<ConnectedChannelName, "微信">;
      kind: "credentials";
      appId: string;
      secretLabel: string;
      secret: string;
    }
  | {
      name: "微信";
      kind: "text";
      detail: string;
    }
> = [
  {
    name: "QQ",
    kind: "credentials",
    appId: "1903828696",
    secretLabel: "clientSecret",
    secret: "2CN**************",
  },
  {
    name: "元宝",
    kind: "credentials",
    appId: "ez1**************",
    secretLabel: "appSecret",
    secret: "TpU**************",
  },
  {
    name: "飞书",
    kind: "credentials",
    appId: "cli_aaaa6b9710f85be9",
    secretLabel: "appSecret",
    secret: "DMQ**************",
  },
  {
    name: "微信",
    kind: "text",
    detail: "已连接微信 ClawBot",
  },
];

const selectedAgent = computed(() => {
  const id = String(route.params.id || "");
  return agents.value.find((agent) => agent.id === id || agent.role === id) ?? null;
});

const latestAgentMessage = computed(() =>
  [...messages.value].reverse().find((message) => message.sender === "agent") ?? null,
);

onMounted(async () => {
  agents.value = await api.agents();
  if (!selectedAgent.value && agents.value.length) {
    await router.replace(`/agents/${agents.value[0].id}`);
    return;
  }
  await loadMessages();
});

watch(
  () => route.params.id,
  async () => {
    if (agents.value.length) {
      await loadMessages();
    }
  },
);

async function loadMessages() {
  const agent = selectedAgent.value;
  if (!agent) return;
  loadingMessages.value = true;
  feedback.value = "";
  try {
    messages.value = await api.agentChatMessages(agent.id);
    await scrollToBottom();
  } catch (error) {
    feedback.value = error instanceof Error ? error.message : "读取会话失败。";
  } finally {
    loadingMessages.value = false;
  }
}

async function sendMessage() {
  const agent = selectedAgent.value;
  const content = draft.value.trim();
  if (!agent || !content || sending.value) return;
  sending.value = true;
  feedback.value = "";
  draft.value = "";
  try {
    const response = await api.sendAgentMessage(agent.id, content);
    messages.value.push(response.user_message, response.agent_message);
    await scrollToBottom();
  } catch (error) {
    draft.value = content;
    feedback.value = error instanceof Error ? error.message : "发送失败。";
  } finally {
    sending.value = false;
  }
}

async function scrollToBottom() {
  await nextTick();
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight;
  }
}

function agentDisplayTitle(title: string) {
  return title.replace(/\s*Agent/g, "智能体");
}

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

function groupTone(group: string): "blue" | "green" | "amber" | "red" | "slate" {
  if (group === "core_business" || group === "orchestration") return "blue";
  if (group === "client_service") return "green";
  if (group === "compliance_review") return "amber";
  if (group === "archive_management") return "slate";
  return "slate";
}

function sourceTone(source: AgentChatMessage["source"]): "blue" | "green" | "amber" | "red" | "slate" {
  if (source === "llm") return "green";
  if (source === "rule_fallback") return "amber";
  return "slate";
}

function sourceLabel(source: AgentChatMessage["source"]) {
  return {
    llm: "大模型",
    rule_fallback: "规则兜底",
    manual: "人工",
  }[source];
}

function sourceTypeLabel(sourceType: AgentRetrievedContext["source_type"]) {
  return {
    case: "案件",
    memory: "记忆",
    wechat: "聊天",
    document: "文件",
    research: "检索",
    task: "任务",
  }[sourceType];
}

function formatTime(value: string) {
  try {
    return new Date(value).toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return value;
  }
}

function selectSetupChannel(channel: SetupChannelName) {
  activeSetupChannel.value = channel;
  showChannelOptions.value = false;
}

function configValue(field: ConfigField) {
  const channel = activeSetupChannel.value;
  return configValues.value[channel][field];
}

function updateConfigValue(field: ConfigField, event: Event) {
  const channel = activeSetupChannel.value;
  const input = event.target as HTMLInputElement;
  configValues.value[channel][field] = input.value;
}

function qrCellClass(index: number) {
  const row = Math.floor((index - 1) / 7);
  const col = (index - 1) % 7;
  const isCorner =
    (row <= 1 && col <= 1) ||
    (row <= 1 && col >= 5) ||
    (row >= 5 && col <= 1);
  const channelOffset = activeSetupChannel.value.length;
  return isCorner || (row * 3 + col * 5 + channelOffset) % 4 !== 1 ? "dark" : "light";
}

function applyChannelConfig() {
  const channel = activeSetupChannel.value;
  if (connectedChannels.some((item) => item.name === channel)) {
    expandedConnectedChannel.value = channel as ConnectedChannelName;
  }
  channelApplyNotice.value = "添加成功";
  if (channelSuccessTimer !== null) {
    window.clearTimeout(channelSuccessTimer);
  }
  channelSuccessTimer = window.setTimeout(() => {
    channelApplyNotice.value = "";
    channelSuccessTimer = null;
  }, 1600);
}

function toggleConnectedChannel(channel: ConnectedChannelName) {
  expandedConnectedChannel.value = expandedConnectedChannel.value === channel ? null : channel;
}
</script>

<style scoped>
.button-icon {
  width: 15px;
  height: 15px;
}

.agent-chat-workbench {
  display: grid;
  grid-template-columns: 292px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}

.agent-list-panel {
  position: sticky;
  top: 86px;
  padding: 12px;
}

.agent-list {
  display: grid;
  gap: 6px;
}

.agent-list-link {
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  min-height: 48px;
  padding: 7px;
  border: 1px solid transparent;
  border-radius: 6px;
  color: inherit;
  text-decoration: none;
}

.agent-list-link:hover,
.agent-list-link.active {
  border-color: var(--border);
  background: #f8fafc;
}

.agent-list-icon {
  width: 30px;
  height: 30px;
  padding: 6px;
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--blue);
  background: #eff6ff;
}

.agent-list-link strong,
.agent-list-link small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-list-link small {
  color: var(--muted);
  font-size: 11px;
}

.agent-chat-panel {
  display: grid;
  grid-template-rows: auto minmax(380px, calc(100vh - 312px)) auto auto;
  gap: 10px;
  min-height: calc(100vh - 126px);
}

.agent-chat-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}

.agent-chat-head h2 {
  margin: 7px 0 3px;
  font-size: 16px;
  letter-spacing: 0;
}

.agent-chat-head p {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
}

.agent-message-list {
  display: flex;
  flex-direction: column;
  gap: 9px;
  min-height: 380px;
  overflow: auto;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #f8fafc;
}

.agent-message {
  max-width: 78%;
  padding: 9px 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: white;
}

.agent-message.outbound {
  align-self: flex-end;
  border-color: #bfdbfe;
  background: #eff6ff;
}

.agent-message.inbound {
  align-self: flex-start;
}

.agent-message-author,
.agent-message-meta {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 6px;
  color: var(--muted);
  font-size: 11px;
}

.agent-message-author span {
  color: var(--text);
  font-weight: 700;
}

.agent-message-meta {
  margin: 8px 0 0;
}

.agent-contexts {
  display: grid;
  gap: 7px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--border);
}

.agent-contexts-title {
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
}

.agent-context-item {
  padding: 7px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: #ffffff;
}

.agent-context-item div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.agent-context-item strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}

.agent-context-item p {
  margin: 5px 0 0;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.5;
}

.agent-composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 9px;
}

.agent-input {
  min-height: 64px;
  max-height: 160px;
}

.agent-send-button {
  align-self: end;
  min-width: 88px;
  min-height: 38px;
}

.agent-feedback {
  margin: 0;
  color: var(--amber);
  font-size: 12px;
}

.channel-backdrop {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(15, 23, 42, 0.22);
}

.channel-modal {
  position: relative;
  width: min(582px, calc(100vw - 32px));
  max-height: calc(100vh - 40px);
  overflow: auto;
  padding: 28px 28px 26px;
  border: 1px solid var(--border);
  border-radius: 2px;
  background: white;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.18);
}

.channel-close {
  position: absolute;
  top: 9px;
  right: 9px;
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--muted);
}

.channel-close:hover {
  background: #f8fafc;
}

.channel-success-pop {
  position: absolute;
  top: 18px;
  left: 50%;
  z-index: 3;
  min-width: 112px;
  min-height: 36px;
  display: grid;
  place-items: center;
  padding: 0 16px;
  border: 1px solid #bbf7d0;
  border-radius: 6px;
  background: #f0fdf4;
  color: #15803d;
  font-size: 14px;
  font-weight: 700;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.14);
  transform: translateX(-50%);
}

.channel-picker {
  position: relative;
}

.channel-select,
.channel-auth {
  width: 100%;
  min-height: 45px;
  border: 1px solid var(--border);
  border-radius: 0;
  background: white;
  color: #0f172a;
  font-size: 16px;
}

.channel-select {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  text-align: left;
}

.channel-options {
  position: absolute;
  inset: calc(100% + 4px) 0 auto 0;
  z-index: 2;
  display: grid;
  gap: 2px;
  padding: 6px;
  border: 1px solid var(--border);
  background: white;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
}

.channel-option {
  min-height: 34px;
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  padding: 0 10px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: #334155;
  font-size: 14px;
  text-align: left;
  cursor: pointer;
}

.channel-option:hover,
.channel-option.checked {
  background: #f1f5f9;
}

.channel-radio {
  width: 15px;
  height: 15px;
  display: grid;
  place-items: center;
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  background: white;
}

.channel-radio span {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: #2563eb;
}

.channel-option.checked .channel-radio {
  border-color: #2563eb;
}

.channel-config {
  display: grid;
  gap: 12px;
  margin-top: 12px;
}

.channel-config-tabs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.channel-config-tab {
  min-height: 45px;
  border: 1px solid var(--border);
  border-radius: 0;
  background: white;
  color: #0f172a;
  font-size: 16px;
}

.channel-config-tab.active {
  border-color: #2563eb;
  color: #2563eb;
}

.channel-config-input {
  width: 100%;
  min-height: 45px;
  border: 1px solid var(--border);
  border-radius: 0;
  background: white;
  color: #0f172a;
  padding: 0 16px;
  font-size: 16px;
}

.channel-config-input::placeholder {
  color: #64748b;
}

.channel-qr-panel {
  display: grid;
  justify-items: center;
  gap: 10px;
  min-height: 184px;
  padding: 18px;
  border: 1px solid var(--border);
  background: #ffffff;
}

.channel-qr-code {
  display: grid;
  grid-template-columns: repeat(7, 14px);
  grid-template-rows: repeat(7, 14px);
  gap: 4px;
  padding: 14px;
  border: 1px solid var(--border);
  background: #f8fafc;
}

.channel-qr-cell {
  width: 14px;
  height: 14px;
  border-radius: 2px;
}

.channel-qr-cell.dark {
  background: #0f172a;
}

.channel-qr-cell.light {
  background: #ffffff;
}

.channel-qr-panel p {
  margin: 0;
  color: #64748b;
  font-size: 14px;
}

.channel-secret-row {
  position: relative;
}

.channel-secret-toggle {
  position: absolute;
  top: 8px;
  right: 8px;
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #334155;
}

.channel-secret-toggle:hover {
  background: #f1f5f9;
}

.channel-auth {
  font-weight: 700;
}

.channel-copy {
  margin: 17px 0 0;
  color: #64748b;
  font-size: 16px;
}

.channel-divider {
  height: 1px;
  margin: 31px -28px 27px;
  background: var(--border);
}

.channel-title {
  margin: 0 0 20px;
  color: #475569;
  font-size: 16px;
  font-weight: 500;
}

.channel-list {
  display: grid;
  gap: 14px;
}

.channel-card {
  border: 1px solid var(--border);
  background: white;
}

.channel-row {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 61px;
  padding: 0 28px 0 23px;
  border: 0;
  border-radius: 0;
  background: #f1f5f9;
  color: #0f172a;
  text-align: left;
}

.channel-row:hover {
  background: #e8eef6;
}

.channel-name,
.channel-status {
  display: flex;
  align-items: center;
  gap: 10px;
}

.channel-name strong,
.channel-status span {
  font-size: 16px;
}

.channel-dot {
  width: 12px;
  height: 12px;
  border-radius: 999px;
  background: #12b76a;
}

.channel-separator {
  width: 1px;
  height: 20px;
  background: #cbd5e1;
}

.channel-delete {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #334155;
}

.channel-delete:hover {
  background: #e2e8f0;
}

.channel-detail {
  display: grid;
  gap: 12px;
  min-height: 104px;
  padding: 28px 24px;
  color: #64748b;
  font-size: 16px;
}

.channel-detail p {
  margin: 0;
}

.channel-icon {
  width: 18px;
  height: 18px;
}

@media (max-width: 980px) {
  .agent-chat-workbench,
  .agent-composer {
    grid-template-columns: 1fr;
  }

  .agent-list-panel {
    position: static;
  }

  .agent-message {
    max-width: 100%;
  }

  .channel-row {
    padding: 0 14px;
  }
}
</style>
