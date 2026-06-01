<template>
  <PageHeader title="微信桥配置" description="微信插件在本系统中只作为运行环境和消息跳板。">
    <button class="button" :disabled="checking || saving" @click="check">
      {{ checking ? "检查中..." : "检查连接" }}
    </button>
    <button class="button primary" :disabled="saving || checking" @click="save">
      {{ saving ? "保存中..." : "保存" }}
    </button>
  </PageHeader>
  <section class="page-content">
    <section v-if="feedback" class="panel feedback-panel">
      <Badge :tone="feedbackTone">{{ feedbackTitle }}</Badge>
      <span class="muted" style="margin-left: 10px">{{ feedback }}</span>
    </section>
    <div class="grid cols-2">
      <section class="panel">
        <h2 class="panel-title">本地微信桥配置</h2>
        <p class="panel-subtitle">不会占用法律推理、文档比对或智能体协同边界。</p>
        <label class="small muted">传输模式</label>
        <select v-model="form.transport_mode" class="select" style="margin: 6px 0 14px">
          <option value="gateway_rpc">网关调用</option>
          <option value="mock">演示模式</option>
        </select>
        <label class="small muted">网关地址</label>
        <input v-model="form.gateway_url" class="input" style="margin: 6px 0 14px" />
        <label class="small muted">协议版本</label>
        <select v-model.number="form.gateway_protocol_version" class="select" style="margin: 6px 0 14px">
          <option :value="0">自动尝试 4、3、2、1</option>
          <option :value="4">4</option>
          <option :value="3">3</option>
          <option :value="2">2</option>
          <option :value="1">1</option>
        </select>
        <label class="small muted">网关令牌</label>
        <input v-model="form.gateway_token" class="input" style="margin: 6px 0 14px" />
        <label class="small muted">工作目录</label>
        <input v-model="form.workspace_root" class="input" style="margin: 6px 0 14px" />
        <div class="grid cols-2">
          <label class="check-row">
            <input v-model="form.allow_insecure_tls" type="checkbox" />
            允许不安全加密连接
          </label>
          <label class="check-row">
            <input v-model="form.disable_device_pairing" type="checkbox" />
            跳过控制台配对（仅旧版网关需要）
          </label>
        </div>
      </section>
      <section class="panel">
        <h2 class="panel-title">网关调用方法</h2>
        <p class="panel-subtitle">默认复用任务控制台的微信桥网关协议。</p>
        <label class="small muted">会话筛选</label>
        <input v-model="form.wechat_session_filter" class="input" style="margin: 6px 0 14px" />
        <label class="small muted">会话列表方法</label>
        <input v-model="form.list_method" class="input" style="margin: 6px 0 14px" />
        <label class="small muted">历史消息方法</label>
        <input v-model="form.history_method" class="input" style="margin: 6px 0 14px" />
        <label class="small muted">发送消息方法</label>
        <input v-model="form.send_method" class="input" style="margin: 6px 0 14px" />
        <label class="small muted">历史消息数量</label>
        <input v-model.number="form.history_limit" type="number" min="1" class="input" style="margin: 6px 0 0" />
      </section>
      <section class="panel">
        <h2 class="panel-title">状态</h2>
        <p class="panel-subtitle">这里读取微信插件状态；如果未启动，会显示连接失败原因。</p>
        <Badge :tone="status?.online ? 'green' : 'amber'">
          {{ checking ? "检查中" : status?.online ? "在线" : "未知" }}
        </Badge>
        <p style="margin-top: 14px">{{ localizeStatusMessage(status?.message) }}</p>
        <p v-if="status?.error" class="muted small">{{ status.error }}</p>
        <div class="muted small">
          运行模式：{{ displayMode(status?.mode) }}<br />
          传输模式：{{ displayTransport(status?.transport_mode ?? form.transport_mode) }}<br />
          协议版本：{{ form.gateway_protocol_version || "自动" }}<br />
          会话数量：{{ status?.sessions_count ?? "-" }}<br />
          检查时间：{{ status?.checked_at ?? form.last_checked_at ?? "-" }}<br />
          上次同步：{{ form.last_sync_at ?? "-" }}
        </div>
      </section>
    </div>
    <section class="panel" style="margin-top: 16px">
      <h2 class="panel-title">演示聊天记录</h2>
      <p class="panel-subtitle">管理本地 Mock 微信聊天记录，用于演示和测试。</p>
      <RouterLink class="button primary" to="/settings/mock-wechat">
        打开演示聊天编辑器
      </RouterLink>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";

import Badge from "@/components/Badge.vue";
import PageHeader from "@/components/PageHeader.vue";
import { api } from "@/services/api";
import type { OpenClawConnection, OpenClawStatus } from "@/types";

const form = reactive<OpenClawConnection>({
  id: "local_openclaw",
  name: "本机 OpenClaw",
  gateway_url: "ws://localhost:18789",
  gateway_token: "",
  workspace_root: "~/.openclaw",
  transport_mode: "gateway_rpc",
  gateway_protocol_version: 0,
  allow_insecure_tls: false,
  disable_device_pairing: false,
  wechat_session_filter: "",
  list_method: "sessions.list",
  history_method: "chat.history",
  send_method: "chat.send",
  history_limit: 80,
  enabled: true,
});
const status = ref<OpenClawStatus | null>(null);
const saving = ref(false);
const checking = ref(false);
const feedback = ref("");
const feedbackKind = ref<"success" | "warning" | "error">("success");

const feedbackTone = computed(() => {
  if (feedbackKind.value === "success") return "green";
  if (feedbackKind.value === "error") return "red";
  return "amber";
});
const feedbackTitle = computed(() => {
  if (feedbackKind.value === "success") return "完成";
  if (feedbackKind.value === "error") return "失败";
  return "提示";
});

async function load() {
  try {
    Object.assign(form, await api.openclawConnection());
  } catch (error) {
    feedbackKind.value = "error";
    feedback.value = error instanceof Error ? error.message : "读取微信桥配置失败。";
  }
}

async function save() {
  saving.value = true;
  feedbackKind.value = "warning";
  feedback.value = "正在保存微信桥配置...";
  try {
    Object.assign(form, await api.updateOpenclawConnection(form));
    feedbackKind.value = "success";
    feedback.value = "微信桥配置已保存。";
  } catch (error) {
    feedbackKind.value = "error";
    feedback.value = error instanceof Error ? error.message : "保存失败。";
  } finally {
    saving.value = false;
  }
}

async function check() {
  checking.value = true;
  feedbackKind.value = "warning";
  feedback.value = "正在检查微信桥连接...";
  try {
    status.value = await api.openclawStatus();
    feedbackKind.value = status.value.online ? "success" : "error";
    feedback.value = status.value.online
      ? "微信桥已连接，可以同步微信会话。"
      : status.value.error || localizeStatusMessage(status.value.message) || "微信桥暂不可用。";
    await load();
  } catch (error) {
    feedbackKind.value = "error";
    feedback.value = error instanceof Error ? error.message : "检查连接失败。";
  } finally {
    checking.value = false;
  }
}

onMounted(load);

function displayTransport(value?: string | null) {
  if (value === "gateway_rpc") return "网关调用";
  if (value === "mock") return "演示模式";
  return value || "-";
}

function displayMode(value?: string | null) {
  if (!value || value === "wechat_transport_only") return "仅微信通道";
  return value;
}

function localizeStatusMessage(value?: string | null) {
  if (!value) return "尚未检查";
  return value
    .replaceAll("OpenClaw", "微信桥")
    .replaceAll("Gateway", "网关")
    .replaceAll("wechat_transport_only", "仅微信通道");
}
</script>
