<template>
  <PageHeader title="法律文件" description="法律文件类版本控制，支持上传、版本历史、逐字差异和风险摘要。">
    <button class="button primary" @click="createSample">新建双版本示例</button>
  </PageHeader>
  <section class="page-content">
    <div class="split">
      <section class="panel">
        <h2 class="panel-title">文件库</h2>
        <p class="panel-subtitle">第一阶段支持文本和文档转文本后的版本比较。</p>
        <input v-model="uploadTitle" class="input" placeholder="上传文件标题，可留空" />
        <select v-model="uploadType" class="select" style="margin-top: 10px">
          <option value="contract">合同</option>
          <option value="letter">函件</option>
          <option value="pleading">文书</option>
          <option value="evidence">证据</option>
          <option value="other">其他</option>
        </select>
        <input class="input file-input" type="file" accept=".txt,.md,.docx" @change="pickUpload" />
        <button class="button" style="margin: 10px 0 16px" :disabled="!uploadFile" @click="uploadDocument">
          上传为新文件
        </button>

        <div
          v-for="document in documents"
          :key="document.id"
          :class="['list-item', 'item-with-action', selectedId === document.id && 'active']"
        >
          <button class="list-item-main" @click="select(document.id)">
            <strong>{{ document.title }}</strong>
            <div class="muted small">{{ documentTypeLabel(document.document_type) }}</div>
          </button>
          <button class="button danger" :disabled="deletingId === document.id" @click="deleteDocument(document.id)">
            {{ deletingId === document.id ? "删除中" : confirmingId === document.id ? "确认删除" : "删除" }}
          </button>
          <button v-if="confirmingId === document.id" class="button" @click="confirmingId = ''">取消</button>
        </div>
      </section>

      <section class="panel">
        <div class="detail-header">
          <div>
            <h2 class="panel-title">版本差异</h2>
            <p class="panel-subtitle">红色为删除，绿色为新增。</p>
          </div>
          <div v-if="detail" class="row-actions">
            <Badge tone="blue">{{ detail.revisions.length }} 个版本</Badge>
            <a class="button" :href="api.documentExportUrl(detail.document.id)">导出 Word</a>
          </div>
        </div>

        <section v-if="detail" class="version-tools">
          <div class="item-grid">
            <article v-for="revision in detail.revisions" :key="revision.id" class="list-item item-with-action">
              <div>
                <strong>v{{ revision.version_number }}</strong>
                <div class="muted small">
                  {{ revision.source_filename || "手动录入" }} · {{ authorLabel(revision.author_type) }}
                </div>
                <div class="muted small">{{ revision.change_summary }}</div>
              </div>
              <button class="button danger" :disabled="deletingId === revision.id" @click="deleteRevision(revision.id)">
                {{ deletingId === revision.id ? "删除中" : confirmingId === revision.id ? "确认删除" : "删除" }}
              </button>
              <button v-if="confirmingId === revision.id" class="button" @click="confirmingId = ''">取消</button>
            </article>
          </div>
          <textarea v-model="revisionText" class="textarea" placeholder="粘贴新版本文本" />
          <input class="input file-input" type="file" accept=".txt,.md,.docx" @change="pickRevisionUpload" />
          <div class="form-actions">
            <button class="button" :disabled="!revisionText.trim()" @click="createTextRevision">新增文本版本</button>
            <button class="button" :disabled="!revisionFile" @click="uploadRevision">上传新版本</button>
          </div>
          <div v-if="detail.revisions.length > 1" class="compare-row">
            <label>
              <span class="small muted">基准版本</span>
              <select v-model="baseRevisionId" class="select" @change="reloadDiff">
                <option v-for="revision in detail.revisions" :key="revision.id" :value="revision.id">
                  v{{ revision.version_number }} {{ revision.change_summary }}
                </option>
              </select>
            </label>
            <label>
              <span class="small muted">目标版本</span>
              <select v-model="targetRevisionId" class="select" @change="reloadDiff">
                <option v-for="revision in detail.revisions" :key="revision.id" :value="revision.id">
                  v{{ revision.version_number }} {{ revision.change_summary }}
                </option>
              </select>
            </label>
          </div>
        </section>

        <div v-if="diff">
          <div class="diff">
            <span
              v-for="(segment, index) in diff.segments"
              :key="index"
              :class="segment.op === 'insert' ? 'diff-insert' : segment.op === 'delete' ? 'diff-delete' : ''"
            >{{ segment.text }}</span>
          </div>
          <section class="plain-section">
            <h3 class="panel-title">段落变化</h3>
            <div v-for="(change, index) in diff.paragraph_changes" :key="index" class="paragraph-change">
              <Badge :tone="change.op === 'insert' ? 'green' : change.op === 'delete' ? 'red' : change.op === 'replace' ? 'amber' : 'slate'">
                {{ changeOpLabel(change.op) }}
              </Badge>
              <div class="muted small">{{ change.base || change.target }}</div>
            </div>
          </section>
          <section class="plain-section">
            <h3 class="panel-title">风险提示</h3>
            <ul>
              <li v-for="risk in diff.risk_summary" :key="risk">{{ risk }}</li>
            </ul>
          </section>
        </div>
        <div v-else class="empty-state">请选择至少包含两个版本的文件。</div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";

import Badge from "@/components/Badge.vue";
import PageHeader from "@/components/PageHeader.vue";
import { api } from "@/services/api";
import type { LegalDocument, LegalDocumentDiff, LegalDocumentRevision } from "@/types";

const documents = ref<LegalDocument[]>([]);
const selectedId = ref("");
const detail = ref<{ document: LegalDocument; revisions: LegalDocumentRevision[] } | null>(null);
const diff = ref<LegalDocumentDiff | null>(null);
const uploadTitle = ref("");
const uploadType = ref("contract");
const uploadFile = ref<File | null>(null);
const revisionText = ref("");
const revisionFile = ref<File | null>(null);
const deletingId = ref("");
const confirmingId = ref("");
const baseRevisionId = ref("");
const targetRevisionId = ref("");

async function load() {
  documents.value = await api.documents();
  if (!selectedId.value && documents.value[0]) {
    await select(documents.value[0].id);
  } else if (selectedId.value && !documents.value.some((item) => item.id === selectedId.value)) {
    selectedId.value = "";
    detail.value = null;
    diff.value = null;
    if (documents.value[0]) await select(documents.value[0].id);
  }
}

async function select(id: string) {
  selectedId.value = id;
  detail.value = await api.documentDetail(id);
  const revisions = detail.value.revisions;
  baseRevisionId.value = revisions.length > 1 ? revisions[revisions.length - 2].id : "";
  targetRevisionId.value = revisions.length ? revisions[revisions.length - 1].id : "";
  await reloadDiff();
}

async function reloadDiff() {
  if (!selectedId.value || !detail.value || detail.value.revisions.length < 2) {
    diff.value = null;
    return;
  }
  if (baseRevisionId.value === targetRevisionId.value) {
    diff.value = null;
    return;
  }
  diff.value = await api.documentDiff(selectedId.value, baseRevisionId.value, targetRevisionId.value);
}

function pickUpload(event: Event) {
  const input = event.target as HTMLInputElement;
  uploadFile.value = input.files?.[0] ?? null;
}

function pickRevisionUpload(event: Event) {
  const input = event.target as HTMLInputElement;
  revisionFile.value = input.files?.[0] ?? null;
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
  await select(document.id);
}

async function createTextRevision() {
  if (!selectedId.value || !revisionText.value.trim()) return;
  await api.createRevision(selectedId.value, {
    content_text: revisionText.value.trim(),
    change_summary: "手动粘贴新版本",
  });
  revisionText.value = "";
  await select(selectedId.value);
}

async function uploadRevision() {
  if (!selectedId.value || !revisionFile.value) return;
  const form = new FormData();
  form.append("file", revisionFile.value);
  form.append("change_summary", "上传新版本");
  await api.uploadRevision(selectedId.value, form);
  revisionFile.value = null;
  await select(selectedId.value);
}

async function withDelete(id: string, action: () => Promise<void>) {
  deletingId.value = id;
  try {
    await action();
    confirmingId.value = "";
  } finally {
    deletingId.value = "";
  }
}

function armDelete(id: string) {
  if (confirmingId.value !== id) {
    confirmingId.value = id;
    return false;
  }
  return true;
}

async function deleteDocument(documentId: string) {
  if (!armDelete(documentId)) return;
  await withDelete(documentId, async () => {
    await api.deleteDocument(documentId);
    if (selectedId.value === documentId) {
      selectedId.value = "";
      detail.value = null;
      diff.value = null;
    }
    await load();
  });
}

async function deleteRevision(revisionId: string) {
  if (!selectedId.value || !armDelete(revisionId)) return;
  await withDelete(revisionId, async () => {
    const documentId = selectedId.value;
    const result = await api.deleteRevision(documentId, revisionId);
    await load();
    if (Boolean(result.deleted_document)) {
      selectedId.value = "";
      detail.value = null;
      diff.value = null;
      await load();
    } else if (selectedId.value) {
      await select(selectedId.value);
    }
  });
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
  await select(document.id);
}

function documentTypeLabel(type: string) {
  return {
    contract: "合同",
    letter: "函件",
    pleading: "文书",
    evidence: "证据",
    other: "其他",
  }[type] ?? type;
}

function authorLabel(type: string) {
  return {
    owner: "人工录入",
    agent: "智能体生成",
    import: "文件导入",
  }[type] ?? type;
}

function changeOpLabel(op: string) {
  return {
    insert: "新增",
    delete: "删除",
    replace: "替换",
    equal: "未变更",
  }[op] ?? op;
}

onMounted(load);
</script>
