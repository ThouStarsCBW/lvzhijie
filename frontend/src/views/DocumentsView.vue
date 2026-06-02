<template>
  <PageHeader title="法律文件" description="文件库管理，支持上传、版本控制和法律风险分析。">
    <button class="button primary" @click="createSample">新建双版本示例</button>
  </PageHeader>

  <section class="page-content">
    <div class="documents-list-container">
      <!-- 上传新文件库 -->
      <section class="panel upload-panel">
        <h2 class="panel-title">上传新文件库</h2>
        <p class="panel-subtitle">支持 .txt、.md、.docx 文件。</p>
        <div class="upload-form">
          <input v-model="uploadTitle" class="input" placeholder="文件标题，可留空" />
          <select v-model="uploadType" class="select" style="margin-top: 10px">
            <option value="contract">合同</option>
            <option value="letter">函件</option>
            <option value="pleading">文书</option>
            <option value="evidence">证据</option>
            <option value="other">其他</option>
          </select>
          <input class="input file-input" type="file" accept=".txt,.md,.docx" @change="pickUpload" />
          <button class="button" style="margin: 10px 0 16px" :disabled="!uploadFile" @click="uploadDocument">
            上传为新文件库
          </button>
        </div>
      </section>

      <!-- 文件库列表 -->
      <section class="panel">
        <h2 class="panel-title">文件库列表</h2>
        <p class="panel-subtitle">点击文件库进入详情页面。</p>
        
        <div v-if="loading" class="empty-state">加载中...</div>
        <div v-else-if="documents.length === 0" class="empty-state">暂无文件库，请上传文件创建。</div>
        
        <div v-else class="documents-grid">
          <div
            v-for="document in documents"
            :key="document.id"
            class="document-card"
            @click="goToDetail(document.id)"
          >
            <div class="document-card-header">
              <div class="document-icon">
                <FileText class="icon" />
              </div>
              <div class="document-info">
                <h3 class="document-title">{{ document.title }}</h3>
                <div class="document-meta">
                  <span class="document-type">{{ documentTypeLabel(document.document_type) }}</span>
                  <span class="document-date">{{ formatDate(document.updated_at) }}</span>
                </div>
              </div>
              <button 
                class="button danger small" 
                @click.stop="deleteDocument(document.id)"
                :disabled="deletingId === document.id"
              >
                {{ deletingId === document.id ? "删除中" : confirmingId === document.id ? "确认删除" : "删除" }}
              </button>
              <button 
                v-if="confirmingId === document.id" 
                class="button small" 
                @click.stop="confirmingId = ''"
              >
                取消
              </button>
            </div>
            <div class="document-card-footer">
              <div class="document-stats">
                <span class="stat">
                  <GitBranch class="icon" />
                  {{ documentStats[document.id]?.branches || 0 }} 分支
                </span>
                <span class="stat">
                  <Clock class="icon" />
                  {{ documentStats[document.id]?.revisions || 0 }} 版本
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useRouter } from "vue-router";
import { FileText, GitBranch, Clock } from "lucide-vue-next";

import PageHeader from "@/components/PageHeader.vue";
import { api } from "@/services/api";
import type { LegalDocument } from "@/types";

const router = useRouter();
const documents = ref<LegalDocument[]>([]);
const loading = ref(true);
const uploadTitle = ref("");
const uploadType = ref("contract");
const uploadFile = ref<File | null>(null);
const deletingId = ref("");
const confirmingId = ref("");

// 存储每个文档的统计信息
const documentStats = ref<Record<string, { branches: number; revisions: number }>>({});

async function load() {
  loading.value = true;
  try {
    documents.value = await api.documents();
    // 并行加载每个文档的统计信息
    await Promise.all(documents.value.map(async (doc) => {
      try {
        const tree = await api.documentTree(doc.id);
        const totalRevisions = tree.branches.reduce((sum, branch) => sum + branch.revisions.length, 0);
        documentStats.value[doc.id] = {
          branches: tree.branches.length,
          revisions: totalRevisions,
        };
      } catch {
        documentStats.value[doc.id] = { branches: 0, revisions: 0 };
      }
    }));
  } finally {
    loading.value = false;
  }
}

function pickUpload(event: Event) {
  const input = event.target as HTMLInputElement;
  uploadFile.value = input.files?.[0] ?? null;
}

async function uploadDocument() {
  if (!uploadFile.value) return;
  const form = new FormData();
  form.append("file", uploadFile.value);
  form.append("document_type", uploadType.value);
  if (uploadTitle.value.trim()) form.append("title", uploadTitle.value.trim());
  form.append("change_summary", "上传初始版本");
  const document = await api.uploadDocument(form);
  uploadFile.value = null;
  uploadTitle.value = "";
  await load();
  // 跳转到新创建的文件库详情
  goToDetail(document.id);
}

function goToDetail(documentId: string) {
  router.push(`/documents/${documentId}`);
}

async function deleteDocument(documentId: string) {
  if (confirmingId.value !== documentId) {
    confirmingId.value = documentId;
    return;
  }
  
  deletingId.value = documentId;
  try {
    await api.deleteDocument(documentId);
    confirmingId.value = "";
    await load();
  } finally {
    deletingId.value = "";
  }
}

async function createSample() {
  const document = await api.createDocument({
    title: `合同审查 ${new Date().toLocaleTimeString()}`,
    document_type: "contract",
    content_text: "甲方应在验收后7日内支付服务费。违约金按每日万分之三计算。",
    change_summary: "初始版本",
  });
  await api.createRevision(document.id, {
    content_text: "甲方应在验收后30日内支付服务费。违约金按每日万分之一计算，累计不超过合同金额10%。",
    change_summary: "付款期限和违约责任调整",
  });
  await load();
  goToDetail(document.id);
}

function documentTypeLabel(type: string) {
  return { contract: "合同", letter: "函件", pleading: "文书", evidence: "证据", other: "其他" }[type] ?? type;
}

function formatDate(dateStr: string) {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
  } catch {
    return "";
  }
}

onMounted(load);
</script>

<style scoped>
.documents-list-container {
  max-width: 1200px;
  margin: 0 auto;
}

.upload-panel {
  margin-bottom: 20px;
}

.upload-form {
  display: grid;
  gap: 10px;
  max-width: 400px;
}

.documents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.document-card {
  background: white;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.document-card:hover {
  border-color: var(--blue);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.1);
  transform: translateY(-2px);
}

.document-card-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.document-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--blue-soft);
  border-radius: 8px;
  flex-shrink: 0;
}

.document-icon .icon {
  width: 20px;
  height: 20px;
  color: var(--blue);
}

.document-info {
  flex: 1;
  min-width: 0;
}

.document-title {
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.document-meta {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: var(--muted);
}

.document-type {
  background: var(--surface-muted);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}

.document-date {
  font-size: 11px;
}

.document-card-footer {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.document-stats {
  display: flex;
  gap: 16px;
}

.stat {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--muted);
}

.stat .icon {
  width: 14px;
  height: 14px;
}

.button.small {
  min-height: 28px;
  padding: 0 8px;
  font-size: 12px;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--muted);
  font-size: 14px;
}
</style>
