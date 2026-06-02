<template>
  <PageHeader title="微信工作台" description="读取微信聊天记录，并以微信桥作为手机发送跳板。">
    <button class="button" @click="sync">同步微信桥</button>
  </PageHeader>
  <section class="page-content">
    <section v-if="syncMessage" class="panel" style="margin-bottom: 16px">
      <Badge :tone="syncOk ? 'green' : 'amber'">{{ syncOk ? "同步完成" : "同步提醒" }}</Badge>
      <span class="muted" style="margin-left: 10px">{{ syncMessage }}</span>
    </section>
    <div class="split">
      <section class="panel">
        <h2 class="panel-title">会话</h2>
        <p class="panel-subtitle">微信插件同步过来的聊天。</p>
        <input v-model="query" class="input" placeholder="搜索联系人或消息内容" style="margin-bottom: 10px" />
        <div
          v-for="conversation in filteredConversations"
          :key="conversation.id"
          :class="['list-item', 'item-with-action', selectedId === conversation.id && 'active']"
        >
          <button class="list-item-main" type="button" @click="select(conversation.id)">
            <strong>{{ conversation.contact?.display_name ?? "微信用户" }}</strong>
            <div class="muted small">
              {{ conversation.contact?.remark ?? conversation.openclaw_conversation_id }}
            </div>
            <div style="margin-top: 8px">
              <Badge tone="blue">{{ autoReplyLabel(conversation.auto_reply_source) }}</Badge>
              <Badge v-if="conversation.case_id" tone="green" style="margin-left: 6px">已建案</Badge>
            </div>
          </button>
          <button class="button danger conversation-delete-button" type="button" @click="deleteConversation(conversation)">
            删除
          </button>
        </div>
      </section>

      <section class="panel">
        <div style="display: flex; justify-content: space-between; gap: 12px">
          <div>
            <h2 class="panel-title">聊天记录</h2>
            <p class="panel-subtitle">电脑端发送会经由微信桥转发到微信。</p>
          </div>
          <div v-if="selected" class="page-actions">
            <select v-if="!selected.case_id" v-model="bindCaseId" class="select" style="width: 180px">
              <option value="">绑定已有案件</option>
              <option v-for="item in cases" :key="item.id" :value="item.id">{{ item.title }}</option>
            </select>
            <button v-if="!selected.case_id" class="button" :disabled="!bindCaseId" @click="bindCase">绑定</button>
            <button
              class="button primary"
              :disabled="Boolean(selected.case_id) || creatingCase"
              @click="createCase"
            >
              {{ selected.case_id ? "已建立案件" : creatingCase ? "建案中..." : "一键建立案件" }}
            </button>
          </div>
        </div>
        <div style="min-height: 360px">
          <div
            v-for="message in filteredMessages"
            :key="message.id"
            :class="['message', message.direction === 'outbound' && 'outbound']"
          >
            <div v-if="message.content" class="message-text">{{ message.content }}</div>
            <div v-if="message.attachments?.length" class="message-attachments">
              <template v-for="attachment in message.attachments" :key="attachment.url">
                <a
                  v-if="isImageAttachment(attachment)"
                  :href="apiAssetUrl(attachment.url)"
                  target="_blank"
                  rel="noreferrer"
                  class="message-image-link"
                >
                  <img :src="apiAssetUrl(attachment.url)" :alt="attachment.name" class="message-image" />
                </a>
                <a
                  v-else
                  :href="apiAssetUrl(attachment.url)"
                  target="_blank"
                  rel="noreferrer"
                  class="message-file"
                >
                  <span class="message-file-name">{{ attachment.name }}</span>
                  <span class="message-file-meta">{{ formatFileSize(attachment.size) }}</span>
                </a>
              </template>
            </div>
            <div class="message-meta">
              {{ senderLabel(message.sender) }} · {{ statusLabel(message.status) }}
            </div>
          </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr auto; gap: 10px">
          <input v-model="draft" class="input" placeholder="输入要发给微信用户的消息" />
          <button class="button primary" :disabled="!selectedId || !draft.trim()" @click="send">
            发送
          </button>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import Badge from "@/components/Badge.vue";
import PageHeader from "@/components/PageHeader.vue";
import { api, apiAssetUrl } from "@/services/api";
import type { CaseItem, WechatAttachment, WechatConversation, WechatMessage } from "@/types";

const conversations = ref<WechatConversation[]>([]);
const cases = ref<CaseItem[]>([]);
const selectedId = ref("");
const messages = ref<WechatMessage[]>([]);
const draft = ref("");
const syncMessage = ref("");
const syncOk = ref(true);
const query = ref("");
const bindCaseId = ref("");
const creatingCase = ref(false);

const selected = computed(() => conversations.value.find((item) => item.id === selectedId.value));
const filteredMessages = computed(() => {
  const text = query.value.trim().toLowerCase();
  if (!text) return messages.value;
  return messages.value.filter((message) => {
    const attachmentText = (message.attachments ?? []).map((item) => item.name).join(" ");
    return `${message.content} ${attachmentText}`.toLowerCase().includes(text);
  });
});
const filteredConversations = computed(() => {
  const text = query.value.trim().toLowerCase();
  if (!text) return conversations.value;
  return conversations.value.filter((conversation) => {
    const label = `${conversation.contact?.display_name ?? ""} ${conversation.contact?.remark ?? ""} ${conversation.openclaw_conversation_id}`.toLowerCase();
    const inMessages = selectedId.value === conversation.id && filteredMessages.value.length > 0;
    return label.includes(text) || inMessages;
  });
});

async function load() {
  [conversations.value, cases.value] = await Promise.all([api.conversations(), api.cases()]);
  const selectedExists = conversations.value.some((item) => item.id === selectedId.value);
  if (!selectedExists) {
    selectedId.value = "";
    messages.value = [];
  }
  if (!selectedId.value && conversations.value[0]) {
    await select(conversations.value[0].id);
  } else if (selectedId.value) {
    await select(selectedId.value);
  }
}

async function select(id: string) {
  selectedId.value = id;
  messages.value = await api.conversationMessages(id);
}

async function send() {
  if (!selectedId.value || !draft.value.trim()) return;
  await api.sendWechatMessage(selectedId.value, draft.value.trim());
  draft.value = "";
  await select(selectedId.value);
  conversations.value = await api.conversations();
}

async function createCase() {
  if (!selectedId.value) return;
  creatingCase.value = true;
  try {
    const created = await api.createCaseFromConversation(selectedId.value);
    bindCaseId.value = "";
    syncOk.value = true;
    syncMessage.value = `已根据聊天记录建立案件：${created.title}`;
    await load();
  } finally {
    creatingCase.value = false;
  }
}

async function bindCase() {
  if (!selectedId.value || !bindCaseId.value) return;
  await api.bindConversationToCase(selectedId.value, bindCaseId.value);
  bindCaseId.value = "";
  await load();
}

async function deleteConversation(conversation: WechatConversation) {
  const label = conversation.contact?.display_name ?? conversation.openclaw_conversation_id;
  if (!confirm(`确定删除“${label}”这个会话及其聊天记录吗？`)) return;
  await api.deleteWechatConversation(conversation.id);
  if (selectedId.value === conversation.id) {
    selectedId.value = "";
    messages.value = [];
    bindCaseId.value = "";
  }
  syncOk.value = true;
  syncMessage.value = `已删除会话：${label}`;
  await load();
}

async function sync() {
  const result = await api.syncOpenclaw();
  syncOk.value = Boolean(result.ok);
  const errors = Array.isArray(result.errors) ? result.errors : [];
  syncMessage.value = syncOk.value
    ? `已同步 ${result.sessions ?? 0} 个会话、${result.messages ?? 0} 条消息。`
    : `微信桥同步未完成：${errors.join("; ") || "请检查网关配置"}`;
  await load();
}

function senderLabel(sender: string) {
  return {
    wechat_user: "微信用户",
    openclaw_auto: "微信桥自动回复",
    owner: "电脑端",
    system: "系统",
  }[sender] ?? sender;
}

function statusLabel(status: string) {
  return {
    synced: "已同步",
    sent: "已发送",
    pending: "待发送",
    failed: "发送失败",
  }[status] ?? status;
}

function autoReplyLabel(source: string) {
  return {
    openclaw: "微信桥",
    owner: "电脑端",
    system: "系统",
    manual: "人工",
  }[source] ?? source;
}

function isImageAttachment(attachment: WechatAttachment) {
  return (
    attachment.mime_type?.startsWith("image/") ||
    /\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(attachment.name)
  );
}

function formatFileSize(size?: number | null) {
  if (!size || size <= 0) return "文件";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

onMounted(load);
</script>
