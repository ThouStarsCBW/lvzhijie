<template>
  <div class="document-detail-view">
    <div class="detail-header">
      <div class="header-left">
        <button class="button" @click="goBack">
          <ArrowLeft class="icon" />
          返回文件库
        </button>
        <div class="document-title-section">
          <h1 class="document-title">{{ document?.title || "加载中..." }}</h1>
          <div class="document-meta" v-if="document">
            <span class="document-type">{{ documentTypeLabel(document.document_type) }}</span>
            <span class="document-date">{{ formatDate(document.updated_at) }}</span>
          </div>
        </div>
      </div>
      <div class="header-right">
        <button class="button" @click="refreshTree" :disabled="loadingTree">
          <RefreshCw class="icon" :class="{ 'animate-spin': loadingTree }" />
          刷新
        </button>
      </div>
    </div>

    <div v-if="loading && !document" class="loading-state">加载中...</div>
    <div v-else-if="error" class="error-state">{{ error }}</div>
    
    <div v-else-if="document" class="detail-content">
      <!-- 三列布局 -->
      <div class="columns-container">
        <!-- 左列：分支概览 -->
        <div class="column branch-column">
          <div class="panel">
            <div class="panel-header">
              <h2 class="panel-title">
                <GitBranch class="icon" />
                分支概览
              </h2>
              <button class="button small primary" @click="showNewBranchForm = true">
                <Plus class="icon" />
                新建分支
              </button>
            </div>
            
            <!-- 新建分支表单 -->
            <div v-if="showNewBranchForm" class="new-branch-form">
              <div class="form-group">
                <label class="form-label">分支名称</label>
                <input v-model="newBranchName" class="input" placeholder="例如: feature/payment-terms" />
              </div>
              <div class="form-group">
                <label class="form-label">基于版本</label>
                <select v-model="newBranchBaseRevisionId" class="select">
                  <option value="">选择基础版本</option>
                  <template v-for="branch in treeData?.branches || []" :key="branch.id">
                    <option v-for="rev in branch.revisions" :key="rev.id" :value="rev.id">
                      {{ branch.name }} / {{ rev.label }}
                    </option>
                  </template>
                </select>
              </div>
              <div class="form-actions">
                <button class="button small" @click="showNewBranchForm = false">取消</button>
                <button 
                  class="button small primary" 
                  @click="createBranch"
                  :disabled="!newBranchName || !newBranchBaseRevisionId || creatingBranch"
                >
                  {{ creatingBranch ? "创建中" : "创建分支" }}
                </button>
              </div>
            </div>

            <!-- 分支树 -->
            <div v-if="loadingTree" class="loading-state">加载分支树...</div>
            <div v-else-if="treeData?.branches.length === 0" class="empty-state">
              暂无分支，请创建分支开始版本控制。
            </div>
            <div v-else class="branch-tree">
              <div v-for="branch in treeData?.branches" :key="branch.id" class="branch-group">
                <div 
                  class="branch-header"
                  :class="{ 'is-default': branch.is_default, 'is-selected': selectedBranchId === branch.id }"
                  @click="selectBranch(branch.id)"
                >
                  <div class="branch-name">
                    <GitBranch class="icon" />
                    {{ branch.name }}
                    <span v-if="branch.is_default" class="default-badge">默认</span>
                  </div>
                  <div class="branch-meta">
                    {{ branch.revisions.length }} 个版本
                  </div>
                </div>
                
                <!-- 版本列表 -->
                <div class="revision-list">
                  <div 
                    v-for="(revision, index) in branch.revisions" 
                    :key="revision.id"
                    class="revision-item"
                    :class="{ 
                      'is-head': revision.id === branch.head_revision_id,
                      'is-selected': selectedRevisionId === revision.id 
                    }"
                    @click="selectRevision(revision.id)"
                  >
                    <div class="revision-dot" :class="{ 'is-first': index === 0 }"></div>
                    <div class="revision-info">
                      <div class="revision-hash">{{ revision.short_hash }}</div>
                      <div class="revision-label">{{ revision.label }}</div>
                      <div class="revision-meta">
                        <span class="revision-date">{{ formatDate(revision.created_at) }}</span>
                        <span v-if="revision.change_summary" class="revision-summary">
                          {{ revision.change_summary }}
                        </span>
                      </div>
                    </div>
                    <div v-if="revision.id === branch.head_revision_id" class="head-badge">HEAD</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 中列：提交新版本 -->
        <div class="column submit-column">
          <div class="panel">
            <div class="panel-header">
              <h2 class="panel-title">
                <Upload class="icon" />
                提交新版本
              </h2>
            </div>
            
            <div v-if="!selectedBranchId" class="empty-state">
              请先选择一个分支。
            </div>
            
            <div v-else class="submit-form">
              <div class="form-group">
                <label class="form-label">目标分支</label>
                <div class="selected-branch">
                  <GitBranch class="icon" />
                  {{ selectedBranchName }}
                </div>
              </div>
              
              <div class="form-group">
                <label class="form-label">变更说明</label>
                <input v-model="changeSummary" class="input" placeholder="描述本次修改内容" />
              </div>
              
              <div class="form-group">
                <label class="form-label">内容输入方式</label>
                <div class="input-mode-toggle">
                  <button 
                    class="toggle-btn" 
                    :class="{ active: inputMode === 'text' }"
                    @click="inputMode = 'text'"
                  >
                    <FileText class="icon" />
                    文本输入
                  </button>
                  <button 
                    class="toggle-btn" 
                    :class="{ active: inputMode === 'file' }"
                    @click="inputMode = 'file'"
                  >
                    <Upload class="icon" />
                    文件上传
                  </button>
                </div>
              </div>
              
              <!-- 文本输入模式 -->
              <div v-if="inputMode === 'text'" class="form-group">
                <label class="form-label">文件内容</label>
                <textarea 
                  v-model="contentText" 
                  class="textarea" 
                  rows="10"
                  placeholder="输入文件内容..."
                ></textarea>
              </div>
              
              <!-- 文件上传模式 -->
              <div v-if="inputMode === 'file'" class="form-group">
                <label class="form-label">上传文件</label>
                <input 
                  class="input file-input" 
                  type="file" 
                  accept=".txt,.md,.docx" 
                  @change="pickFile" 
                />
                <div v-if="uploadFile" class="file-info">
                  <FileText class="icon" />
                  {{ uploadFile.name }}
                </div>
              </div>
              
              <button 
                class="button primary full-width" 
                @click="submitRevision"
                :disabled="!canSubmit || submitting"
              >
                {{ submitting ? "提交中" : "提交新版本" }}
              </button>
            </div>
          </div>
        </div>

        <!-- 右列：Diff 与 AI 分析 -->
        <div class="column diff-column">
          <div class="panel">
            <div class="panel-header">
              <h2 class="panel-title">
                <FileDiff class="icon" />
                版本对比
              </h2>
            </div>
            
            <div class="diff-selectors">
              <div class="form-group">
                <label class="form-label">基准版本</label>
                <select v-model="diffBaseRevisionId" class="select">
                  <option value="">选择基准版本</option>
                  <template v-for="branch in treeData?.branches || []" :key="branch.id">
                    <option v-for="rev in branch.revisions" :key="rev.id" :value="rev.id">
                      {{ branch.name }} / {{ rev.label }}
                    </option>
                  </template>
                </select>
              </div>
              
              <div class="form-group">
                <label class="form-label">目标版本</label>
                <select v-model="diffTargetRevisionId" class="select">
                  <option value="">选择目标版本</option>
                  <template v-for="branch in treeData?.branches || []" :key="branch.id">
                    <option v-for="rev in branch.revisions" :key="rev.id" :value="rev.id">
                      {{ branch.name }} / {{ rev.label }}
                    </option>
                  </template>
                </select>
              </div>
              
              <div class="diff-actions">
                <button 
                  class="button" 
                  @click="loadDiff"
                  :disabled="!diffBaseRevisionId || !diffTargetRevisionId || loadingDiff"
                >
                  {{ loadingDiff ? "加载中" : "查看差异" }}
                </button>
                <a 
                  v-if="diffResult" 
                  :href="diffExportUrl" 
                  class="button"
                  target="_blank"
                >
                  <Download class="icon" />
                  导出 Word
                </a>
              </div>
            </div>
            
            <!-- Diff 结果 -->
            <div v-if="loadingDiff" class="loading-state">加载差异中...</div>
            <div v-else-if="diffResult" class="diff-result">
              <div class="diff-stats">
                <span class="stat">
                  <FileDiff class="icon" />
                  {{ diffResult.segments.length }} 个差异段落
                </span>
                <span class="stat">
                  <RefreshCw class="icon" />
                  {{ diffResult.paragraph_changes.length }} 处段落变更
                </span>
              </div>
              
              <!-- 段落变更 -->
              <div class="paragraph-changes">
                <div v-for="(change, index) in diffResult.paragraph_changes" :key="index" class="paragraph-change">
                  <div class="change-header">
                    <span class="change-op" :class="change.op">{{ changeOpLabel(change.op) }}</span>
                  </div>
                  <div v-if="change.base" class="change-base">
                    <span class="label">原文:</span> {{ formatChangeText(change.base) }}
                  </div>
                  <div v-if="change.target" class="change-target">
                    <span class="label">新文:</span> {{ formatChangeText(change.target) }}
                  </div>
                </div>
              </div>
              
              <!-- 风险提示 -->
              <div v-if="diffResult.risk_summary.length > 0" class="risk-summary">
                <h4 class="risk-title">
                  <AlertTriangle class="icon" />
                  风险提示
                </h4>
                <ul class="risk-list">
                  <li v-for="(risk, index) in diffResult.risk_summary" :key="index">
                    {{ risk }}
                  </li>
                </ul>
              </div>
            </div>
            
            <!-- AI 分析 -->
            <div v-if="diffResult" class="ai-analysis-section">
              <div class="panel-header">
                <h3 class="panel-title">
                  <Brain class="icon" />
                  AI 风险分析
                </h3>
                <button 
                  class="button small" 
                  @click="analyzeDiff"
                  :disabled="analyzing"
                >
                  {{ analyzing ? "分析中" : "开始分析" }}
                </button>
              </div>
              
              <div v-if="analyzing" class="loading-state">AI 分析中，请稍候...</div>
              <div v-else-if="analysisResult" class="analysis-result">
                <div class="analysis-header">
                  <div class="analysis-status" :class="analysisResult.risk_level">
                    {{ riskLevelLabel(analysisResult.risk_level) }}
                  </div>
                  <div class="analysis-source">
                    来源: {{ analysisResult.source === "llm" ? "AI 模型" : "规则引擎" }}
                  </div>
                </div>
                
                <!-- 风险点 -->
                <div v-if="analysisResult.risk_points.length > 0" class="analysis-section">
                  <h4 class="section-title">风险点</h4>
                  <ul class="analysis-list">
                    <li v-for="(point, index) in analysisResult.risk_points" :key="index">
                      {{ point }}
                    </li>
                  </ul>
                </div>
                
                <!-- 模糊条款 -->
                <div v-if="analysisResult.ambiguities.length > 0" class="analysis-section">
                  <h4 class="section-title">模糊条款</h4>
                  <ul class="analysis-list">
                    <li v-for="(ambiguity, index) in analysisResult.ambiguities" :key="index">
                      {{ ambiguity }}
                    </li>
                  </ul>
                </div>
                
                <!-- 隐形变更 -->
                <div v-if="analysisResult.stealth_changes.length > 0" class="analysis-section">
                  <h4 class="section-title">隐形变更</h4>
                  <ul class="analysis-list">
                    <li v-for="(change, index) in analysisResult.stealth_changes" :key="index">
                      {{ change }}
                    </li>
                  </ul>
                </div>
                
                <!-- 建议 -->
                <div v-if="analysisResult.suggestions.length > 0" class="analysis-section">
                  <h4 class="section-title">修改建议</h4>
                  <ul class="analysis-list">
                    <li v-for="(suggestion, index) in analysisResult.suggestions" :key="index">
                      {{ suggestion }}
                    </li>
                  </ul>
                </div>
                
                <!-- 人工审核清单 -->
                <div v-if="analysisResult.manual_review_checklist.length > 0" class="analysis-section">
                  <h4 class="section-title">人工审核清单</h4>
                  <ul class="analysis-list checklist">
                    <li v-for="(item, index) in analysisResult.manual_review_checklist" :key="index">
                      <input type="checkbox" :id="`check-${index}`" />
                      <label :for="`check-${index}`">{{ item }}</label>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { 
  ArrowLeft, 
  GitBranch, 
  Plus, 
  Upload, 
  FileText, 
  FileDiff, 
  Download, 
  Brain, 
  Minus, 
  RefreshCw,
  AlertTriangle
} from "lucide-vue-next";

import { api } from "@/services/api";
import type { 
  LegalDocument, 
  LegalDocumentBranch, 
  LegalDocumentRevision, 
  LegalDocumentTree, 
  LegalDocumentDiff, 
  LegalDocumentAnalysis 
} from "@/types";

const route = useRoute();
const router = useRouter();
const documentId = computed(() => route.params.id as string);

// 文档数据
const document = ref<LegalDocument | null>(null);
const branches = ref<LegalDocumentBranch[]>([]);
const revisions = ref<LegalDocumentRevision[]>([]);
const treeData = ref<LegalDocumentTree | null>(null);
const loading = ref(true);
const loadingTree = ref(false);
const error = ref<string | null>(null);

// 分支选择
const selectedBranchId = ref<string | null>(null);
const selectedRevisionId = ref<string | null>(null);

// 新建分支
const showNewBranchForm = ref(false);
const newBranchName = ref("");
const newBranchBaseRevisionId = ref("");
const creatingBranch = ref(false);

// 提交新版本
const inputMode = ref<"text" | "file">("text");
const contentText = ref("");
const changeSummary = ref("");
const uploadFile = ref<File | null>(null);
const submitting = ref(false);

// Diff 比较
const diffBaseRevisionId = ref("");
const diffTargetRevisionId = ref("");
const diffResult = ref<LegalDocumentDiff | null>(null);
const loadingDiff = ref(false);

// AI 分析
const analysisResult = ref<LegalDocumentAnalysis | null>(null);
const analyzing = ref(false);

// 计算属性
const selectedBranchName = computed(() => {
  if (!selectedBranchId.value || !treeData.value) return "";
  const branch = treeData.value.branches.find(b => b.id === selectedBranchId.value);
  return branch?.name || "";
});

const canSubmit = computed(() => {
  if (!selectedBranchId.value) return false;
  if (inputMode.value === "text") return contentText.value.trim().length > 0;
  return uploadFile.value !== null;
});

const diffExportUrl = computed(() => {
  if (!diffBaseRevisionId.value || !diffTargetRevisionId.value) return "#";
  return api.documentDiffExportUrl(documentId.value, diffBaseRevisionId.value, diffTargetRevisionId.value);
});

// 方法
async function loadDocument() {
  loading.value = true;
  error.value = null;
  try {
    const data = await api.documentDetail(documentId.value);
    document.value = data.document;
    branches.value = data.branches;
    revisions.value = data.revisions;
    await loadTree();
  } catch (e: any) {
    error.value = e.message || "加载失败";
  } finally {
    loading.value = false;
  }
}

async function loadTree() {
  loadingTree.value = true;
  try {
    treeData.value = await api.documentTree(documentId.value);
    // 自动选择默认分支
    if (treeData.value.branches.length > 0 && !selectedBranchId.value) {
      const defaultBranch = treeData.value.branches.find(b => b.is_default) || treeData.value.branches[0];
      selectBranch(defaultBranch.id);
    }
  } catch (e: any) {
    console.error("加载分支树失败:", e);
  } finally {
    loadingTree.value = false;
  }
}

function refreshTree() {
  loadTree();
}

function selectBranch(branchId: string) {
  selectedBranchId.value = branchId;
  // 自动选择分支的 HEAD 版本
  if (treeData.value) {
    const branch = treeData.value.branches.find(b => b.id === branchId);
    if (branch && branch.revisions.length > 0) {
      selectedRevisionId.value = branch.head_revision_id || branch.revisions[branch.revisions.length - 1].id;
    }
  }
}

function selectRevision(revisionId: string) {
  selectedRevisionId.value = revisionId;
}

async function createBranch() {
  if (!newBranchName.value || !newBranchBaseRevisionId.value) return;
  
  creatingBranch.value = true;
  try {
    await api.createDocumentBranch(documentId.value, {
      name: newBranchName.value,
      base_revision_id: newBranchBaseRevisionId.value,
    });
    newBranchName.value = "";
    newBranchBaseRevisionId.value = "";
    showNewBranchForm.value = false;
    await loadTree();
  } catch (e: any) {
    alert("创建分支失败: " + e.message);
  } finally {
    creatingBranch.value = false;
  }
}

function pickFile(event: Event) {
  const input = event.target as HTMLInputElement;
  uploadFile.value = input.files?.[0] ?? null;
}

async function submitRevision() {
  if (!selectedBranchId.value || !canSubmit.value) return;
  
  submitting.value = true;
  try {
    if (inputMode.value === "text") {
      await api.createBranchRevision(documentId.value, selectedBranchId.value, {
        content_text: contentText.value,
        change_summary: changeSummary.value || undefined,
      });
      contentText.value = "";
    } else if (uploadFile.value) {
      const form = new FormData();
      form.append("file", uploadFile.value);
      if (changeSummary.value) form.append("change_summary", changeSummary.value);
      await api.uploadBranchRevision(documentId.value, selectedBranchId.value, form);
      uploadFile.value = null;
    }
    changeSummary.value = "";
    await loadTree();
  } catch (e: any) {
    alert("提交失败: " + e.message);
  } finally {
    submitting.value = false;
  }
}

async function loadDiff() {
  if (!diffBaseRevisionId.value || !diffTargetRevisionId.value) return;
  
  loadingDiff.value = true;
  diffResult.value = null;
  analysisResult.value = null;
  try {
    diffResult.value = await api.documentDiff(
      documentId.value,
      diffBaseRevisionId.value,
      diffTargetRevisionId.value,
    );
  } catch (e: any) {
    alert("加载差异失败: " + e.message);
  } finally {
    loadingDiff.value = false;
  }
}

async function analyzeDiff() {
  if (!diffBaseRevisionId.value || !diffTargetRevisionId.value) return;
  
  analyzing.value = true;
  analysisResult.value = null;
  try {
    analysisResult.value = await api.analyzeDocumentDiff(documentId.value, {
      base_revision_id: diffBaseRevisionId.value,
      target_revision_id: diffTargetRevisionId.value,
    });
  } catch (e: any) {
    alert("AI 分析失败: " + e.message);
  } finally {
    analyzing.value = false;
  }
}

function goBack() {
  router.push("/documents");
}

function documentTypeLabel(type: string) {
  return { contract: "合同", letter: "函件", pleading: "文书", evidence: "证据", other: "其他" }[type] ?? type;
}

function formatDate(dateStr: string) {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString("zh-CN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

function riskLevelLabel(level: string) {
  return { low: "低风险", medium: "中风险", high: "高风险" }[level] ?? level;
}

function changeOpLabel(op: string) {
  return { equal: "无变化", insert: "新增", delete: "删除", replace: "修改" }[op] ?? op;
}

function formatChangeText(text: string) {
  if (!text) return "";
  // 将换行符替换为分号和空格，使文本在一行内显示
  return text.replace(/\n/g, "；").replace(/；；/g, "；");
}

// 初始化
onMounted(loadDocument);

// 监听路由参数变化
watch(documentId, (newId) => {
  if (newId) {
    document.value = null;
    treeData.value = null;
    selectedBranchId.value = null;
    selectedRevisionId.value = null;
    diffResult.value = null;
    analysisResult.value = null;
    loadDocument();
  }
});
</script>

<style scoped>
.document-detail-view {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.document-title-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.document-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
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

.detail-content {
  flex: 1;
  overflow: hidden;
}

.columns-container {
  display: grid;
  grid-template-columns: 300px 1fr 1fr;
  gap: 16px;
  height: 100%;
}

.column {
  overflow-y: auto;
}

.panel {
  background: white;
  border: 1px solid var(--border);
  border-radius: 8px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid var(--border);
}

.panel-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-title .icon {
  width: 16px;
  height: 16px;
}

/* 分支树样式 */
.branch-tree {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.branch-group {
  margin-bottom: 12px;
}

.branch-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--surface-muted);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.branch-header:hover {
  background: var(--blue-soft);
}

.branch-header.is-selected {
  background: var(--blue-soft);
  border: 1px solid var(--blue);
}

.branch-header.is-default {
  border-left: 3px solid var(--blue);
}

.branch-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 500;
}

.branch-name .icon {
  width: 14px;
  height: 14px;
  color: var(--blue);
}

.default-badge {
  background: var(--blue);
  color: white;
  padding: 1px 6px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 600;
}

.branch-meta {
  font-size: 11px;
  color: var(--muted);
}

.revision-list {
  padding-left: 20px;
  border-left: 2px solid var(--border);
  margin-left: 16px;
  margin-top: 8px;
}

.revision-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 8px;
  position: relative;
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 4px;
}

.revision-item:hover {
  background: var(--surface-muted);
}

.revision-item.is-selected {
  background: var(--blue-soft);
}

.revision-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--border);
  margin-top: 4px;
  flex-shrink: 0;
}

.revision-dot.is-first {
  background: var(--blue);
}

.revision-item.is-head .revision-dot {
  background: var(--green);
  box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.2);
}

.revision-info {
  flex: 1;
  min-width: 0;
}

.revision-hash {
  font-family: monospace;
  font-size: 11px;
  color: var(--muted);
  background: var(--surface-muted);
  padding: 1px 4px;
  border-radius: 3px;
  display: inline-block;
  margin-bottom: 2px;
}

.revision-label {
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 2px;
}

.revision-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--muted);
}

.revision-summary {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.head-badge {
  background: var(--green);
  color: white;
  padding: 1px 6px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 600;
  flex-shrink: 0;
}

/* 提交表单样式 */
.submit-form {
  padding: 16px;
  flex: 1;
  overflow-y: auto;
}

.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 6px;
  color: var(--muted);
}

.selected-branch {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--blue-soft);
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
}

.selected-branch .icon {
  width: 14px;
  height: 14px;
  color: var(--blue);
}

.input-mode-toggle {
  display: flex;
  gap: 8px;
}

.toggle-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--surface-muted);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.toggle-btn:hover {
  background: var(--blue-soft);
}

.toggle-btn.active {
  background: var(--blue-soft);
  border-color: var(--blue);
  color: var(--blue);
}

.toggle-btn .icon {
  width: 14px;
  height: 14px;
}

.textarea {
  width: 100%;
  min-height: 200px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-family: monospace;
  font-size: 13px;
  resize: vertical;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding: 8px 12px;
  background: var(--surface-muted);
  border-radius: 6px;
  font-size: 13px;
}

.file-info .icon {
  width: 16px;
  height: 16px;
  color: var(--blue);
}

.full-width {
  width: 100%;
}

/* Diff 样式 */
.diff-selectors {
  padding: 16px;
  border-bottom: 1px solid var(--border);
}

.diff-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.diff-result {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.diff-stats {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}

.stat {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;
}

.stat .icon {
  width: 14px;
  height: 14px;
}

.stat.additions {
  color: var(--green);
}

.stat.deletions {
  color: var(--red);
}

.stat.changes {
  color: var(--blue);
}

.diff-content {
  font-family: monospace;
  font-size: 12px;
  line-height: 1.5;
  background: var(--surface-muted);
  border-radius: 6px;
  overflow: hidden;
}

.diff-line {
  padding: 2px 12px;
  white-space: pre-wrap;
  word-break: break-all;
}

.diff-line.addition {
  background: rgba(34, 197, 94, 0.1);
  color: var(--green);
}

.diff-line.deletion {
  background: rgba(239, 68, 68, 0.1);
  color: var(--red);
}

.diff-line.range {
  background: rgba(37, 99, 235, 0.1);
  color: var(--blue);
  font-weight: 500;
}

/* AI 分析样式 */
.ai-analysis-section {
  border-top: 1px solid var(--border);
  margin-top: 16px;
  padding-top: 16px;
}

.analysis-result {
  padding: 16px;
}

.analysis-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.analysis-status {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

.analysis-status.low {
  background: rgba(34, 197, 94, 0.1);
  color: var(--green);
}

.analysis-status.medium {
  background: rgba(234, 179, 8, 0.1);
  color: var(--yellow);
}

.analysis-status.high {
  background: rgba(239, 68, 68, 0.1);
  color: var(--red);
}

.analysis-source {
  font-size: 11px;
  color: var(--muted);
}

.analysis-content {
  background: var(--surface-muted);
  border-radius: 6px;
  padding: 16px;
}

.analysis-content pre {
  margin: 0;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

/* 新建分支表单 */
.new-branch-form {
  padding: 16px;
  background: var(--surface-muted);
  border-bottom: 1px solid var(--border);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}

/* 状态样式 */
.loading-state,
.empty-state,
.error-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: var(--muted);
  font-size: 14px;
}

.error-state {
  color: var(--red);
}

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 按钮样式 */
.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  text-decoration: none;
  color: inherit;
}

.button:hover {
  background: var(--surface-muted);
}

.button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.button.primary {
  background: var(--blue);
  border-color: var(--blue);
  color: white;
}

.button.primary:hover {
  background: var(--blue-dark);
}

.button.small {
  padding: 4px 8px;
  font-size: 12px;
}

.button .icon {
  width: 14px;
  height: 14px;
}

.input,
.select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 13px;
  background: var(--surface);
  transition: border-color 0.2s ease;
}

.input:focus,
.select:focus,
.textarea:focus {
  outline: none;
  border-color: var(--blue);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.1);
}

.input::placeholder,
.textarea::placeholder {
  color: var(--muted);
}

.file-input {
  padding: 8px;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .columns-container {
    grid-template-columns: 250px 1fr 1fr;
  }
}

@media (max-width: 992px) {
  .columns-container {
    grid-template-columns: 1fr;
    height: auto;
  }
  
  .column {
    max-height: 500px;
  }
}

@media (max-width: 768px) {
  .detail-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .header-left {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}

/* 段落变更样式 */
.paragraph-changes {
  margin-top: 16px;
}

.paragraph-change {
  padding: 12px;
  margin-bottom: 12px;
  background: var(--surface-muted);
  border-radius: 6px;
  border-left: 3px solid var(--border);
}

.paragraph-change:has(.change-op.replace) {
  border-left-color: var(--blue);
}

.paragraph-change:has(.change-op.insert) {
  border-left-color: var(--green);
}

.paragraph-change:has(.change-op.delete) {
  border-left-color: var(--red);
}

.change-header {
  margin-bottom: 8px;
}

.change-op {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.change-op.equal {
  background: var(--surface-muted);
  color: var(--muted);
}

.change-op.insert {
  background: rgba(34, 197, 94, 0.1);
  color: var(--green);
}

.change-op.delete {
  background: rgba(239, 68, 68, 0.1);
  color: var(--red);
}

.change-op.replace {
  background: rgba(37, 99, 235, 0.1);
  color: var(--blue);
}

.change-base,
.change-target {
  font-size: 13px;
  line-height: 1.5;
  margin-top: 4px;
}

.change-base .label,
.change-target .label {
  font-weight: 500;
  color: var(--muted);
  margin-right: 8px;
}

/* 风险提示样式 */
.risk-summary {
  margin-top: 16px;
  padding: 12px;
  background: rgba(234, 179, 8, 0.05);
  border: 1px solid rgba(234, 179, 8, 0.2);
  border-radius: 6px;
}

.risk-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--yellow);
}

.risk-title .icon {
  width: 16px;
  height: 16px;
}

.risk-list {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  line-height: 1.6;
}

.risk-list li {
  margin-bottom: 4px;
}

/* AI 分析部分样式 */
.analysis-section {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.section-title {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
}

.analysis-list {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  line-height: 1.6;
}

.analysis-list li {
  margin-bottom: 6px;
}

.analysis-list.checklist {
  list-style: none;
  padding-left: 0;
}

.analysis-list.checklist li {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.analysis-list.checklist input[type="checkbox"] {
  margin-top: 4px;
  flex-shrink: 0;
}

.analysis-list.checklist label {
  cursor: pointer;
}
</style>