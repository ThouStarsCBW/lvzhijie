<template>
  <PageHeader title="演示聊天记录" description="通过本地 JSON 和上传文件模拟微信会话，用于演示与测试。">
    <button class="button" @click="syncToStore">同步到微信接入</button>
    <RouterLink class="button primary" to="/wechat">打开微信接入</RouterLink>
  </PageHeader>
  <section class="page-content">
    <div class="split">
      <section class="panel">
        <h2 class="panel-title">会话列表</h2>
        <p class="panel-subtitle">点击选择会话。</p>
        <div v-if="selectedId" style="margin-bottom: 10px">
          <button class="button danger" style="width: 100%" @click="deleteSelectedConversation">
            删除当前会话
          </button>
        </div>
        <button
          v-for="conv in conversations"
          :key="conv.id"
          :class="['list-item', selectedId === conv.id && 'active']"
          @click="select(conv.id)"
        >
          <strong>{{ conv.contact?.display_name ?? "未知" }}</strong>
          <div class="muted small">{{ conv.contact?.remark ?? "" }}</div>
        </button>

        <div style="margin-top: 16px; border-top: 1px solid var(--border); padding-top: 12px">
          <h3 class="panel-title">新建对话</h3>
          <input v-model="newName" class="input" placeholder="客户名称" style="margin-top: 6px" />
          <input v-model="newRemark" class="input" placeholder="备注" style="margin-top: 6px" />
          <button
            class="button primary"
            style="width: 100%; margin-top: 8px"
            :disabled="!newName.trim()"
            @click="createConversation"
          >
            新建
          </button>
        </div>
      </section>

      <section class="panel">
        <h2 class="panel-title">聊天预览</h2>
        <p class="panel-subtitle">{{ selectedId ? "当前会话消息" : "请先选择会话" }}</p>
        <div style="min-height: 300px; max-height: 500px; overflow-y: auto">
          <div
            v-for="msg in messages"
            :key="msg.id"
            :class="['message', msg.direction === 'outbound' && 'outbound']"
            style="position: relative"
          >
            <button
              class="message-delete"
              title="删除消息"
              @click="deleteMessage(msg.id)"
            >
              ×
            </button>
            <div v-if="msg.content" class="message-text">{{ msg.content }}</div>
            <div v-if="msg.attachments?.length" class="message-attachments">
              <template v-for="att in msg.attachments" :key="att.url">
                <a
                  v-if="isImage(att)"
                  :href="apiAssetUrl(att.url)"
                  target="_blank"
                  rel="noreferrer"
                  class="message-image-link"
                >
                  <img :src="apiAssetUrl(att.url)" :alt="att.name" class="message-image" />
                </a>
                <a
                  v-else
                  :href="apiAssetUrl(att.url)"
                  target="_blank"
                  rel="noreferrer"
                  class="message-file"
                >
                  <span class="message-file-name">{{ att.name }}</span>
                  <span class="message-file-meta">{{ fmtSize(att.size) }}</span>
                </a>
              </template>
            </div>
            <div class="message-meta">
              {{ msg.sender === "wechat_user" ? "客户" : "我" }} · {{ msg.created_at }}
            </div>
          </div>
          <div v-if="!messages.length && selectedId" class="empty-state">暂无消息</div>
        </div>

        <div v-if="selectedId" style="margin-top: 16px; border-top: 1px solid var(--border); padding-top: 12px">
          <div class="send-section">
            <h3 class="panel-title">客户发送</h3>
            <textarea
              v-model="customerContent"
              class="textarea"
              placeholder="输入客户消息内容"
              rows="2"
            ></textarea>
            <input
              ref="customerFilesRef"
              type="file"
              multiple
              class="file-input"
              @change="onCustomerFiles"
            />
            <button
              class="button primary"
              style="width: 100%; margin-top: 6px"
              :disabled="!canSendCustomer"
              @click="sendCustomer"
            >
              发送（客户）
            </button>
          </div>

          <div class="send-section" style="margin-top: 14px">
            <h3 class="panel-title">我的发送</h3>
            <textarea
              v-model="ownerContent"
              class="textarea"
              placeholder="输入我的消息内容"
              rows="2"
            ></textarea>
            <input
              ref="ownerFilesRef"
              type="file"
              multiple
              class="file-input"
              @change="onOwnerFiles"
            />
            <button
              class="button primary"
              style="width: 100%; margin-top: 6px"
              :disabled="!canSendOwner"
              @click="sendOwner"
            >
              发送（我）
            </button>
          </div>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import PageHeader from "@/components/PageHeader.vue";
import { api, apiAssetUrl, type MockConversation } from "@/services/api";
import type { WechatAttachment, WechatMessage } from "@/types";

const conversations = ref<MockConversation[]>([]);
const selectedId = ref("");
const messages = ref<WechatMessage[]>([]);
const newName = ref("");
const newRemark = ref("");
const customerContent = ref("");
const ownerContent = ref("");
const customerFiles = ref<File[]>([]);
const ownerFiles = ref<File[]>([]);
const customerFilesRef = ref<HTMLInputElement | null>(null);
const ownerFilesRef = ref<HTMLInputElement | null>(null);

const canSendCustomer = computed(
  () => selectedId.value && (customerContent.value.trim() || customerFiles.value.length > 0),
);
const canSendOwner = computed(
  () => selectedId.value && (ownerContent.value.trim() || ownerFiles.value.length > 0),
);

async function loadConversations() {
  conversations.value = await api.mockWechatConversations();
}

async function loadMessages() {
  if (!selectedId.value) {
    messages.value = [];
    return;
  }
  messages.value = await api.mockWechatMessages(selectedId.value);
}

async function select(id: string) {
  selectedId.value = id;
  await loadMessages();
}

async function createConversation() {
  if (!newName.value.trim()) return;
  await api.createMockWechatConversation({
    display_name: newName.value.trim(),
    remark: newRemark.value.trim(),
  });
  newName.value = "";
  newRemark.value = "";
  await loadConversations();
}

async function deleteSelectedConversation() {
  if (!selectedId.value) return;
  if (!confirm("确定删除此会话及其所有消息？")) return;
  await api.deleteMockWechatConversation(selectedId.value);
  selectedId.value = "";
  messages.value = [];
  await loadConversations();
}

async function deleteMessage(messageId: string) {
  if (!selectedId.value) return;
  await api.deleteMockWechatMessage(selectedId.value, messageId);
  await loadMessages();
}

function onCustomerFiles(e: Event) {
  const input = e.target as HTMLInputElement;
  customerFiles.value = input.files ? Array.from(input.files) : [];
}

function onOwnerFiles(e: Event) {
  const input = e.target as HTMLInputElement;
  ownerFiles.value = input.files ? Array.from(input.files) : [];
}

async function sendCustomer() {
  if (!canSendCustomer.value) return;
  const form = new FormData();
  form.append("sender", "wechat_user");
  form.append("content", customerContent.value);
  for (const file of customerFiles.value) {
    form.append("files", file);
  }
  await api.createMockWechatMessage(selectedId.value, form);
  customerContent.value = "";
  customerFiles.value = [];
  if (customerFilesRef.value) customerFilesRef.value.value = "";
  await loadMessages();
  await loadConversations();
}

async function sendOwner() {
  if (!canSendOwner.value) return;
  const form = new FormData();
  form.append("sender", "owner");
  form.append("content", ownerContent.value);
  for (const file of ownerFiles.value) {
    form.append("files", file);
  }
  await api.createMockWechatMessage(selectedId.value, form);
  ownerContent.value = "";
  ownerFiles.value = [];
  if (ownerFilesRef.value) ownerFilesRef.value.value = "";
  await loadMessages();
  await loadConversations();
}

async function syncToStore() {
  await api.syncOpenclaw();
}

function isImage(att: WechatAttachment) {
  return (
    att.mime_type?.startsWith("image/") ||
    /\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(att.name)
  );
}

function fmtSize(size?: number | null) {
  if (!size || size <= 0) return "文件";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

onMounted(loadConversations);
</script>

<style scoped>
.send-section {
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: #f8fafc;
}

.message-delete {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 18px;
  height: 18px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: var(--quiet);
  font-size: 14px;
  line-height: 1;
  padding: 0;
  opacity: 0;
  transition: opacity 0.15s;
}

.message:hover .message-delete {
  opacity: 1;
}

.message-delete:hover {
  background: #fee2e2;
  color: #dc2626;
}
</style>
