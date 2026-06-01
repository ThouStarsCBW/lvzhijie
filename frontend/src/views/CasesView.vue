<template>
  <PageHeader title="案件中心" description="案件是聊天、文件、推理和任务的业务容器。">
    <RouterLink class="button primary" to="/cases/new">新建案件</RouterLink>
  </PageHeader>
  <section class="page-content">
    <section class="panel">
      <table class="table">
        <thead>
          <tr>
            <th>案件</th>
            <th>类型</th>
            <th>状态</th>
            <th>摘要</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in cases" :key="item.id">
            <td><strong>{{ item.title }}</strong></td>
            <td><Badge tone="blue">{{ caseTypeLabel(item.case_type) }}</Badge></td>
            <td><Badge :tone="item.status === 'closed' ? 'slate' : 'green'">{{ caseStatusLabel(item.status) }}</Badge></td>
            <td class="muted">{{ item.summary }}</td>
            <td>
              <div class="row-actions">
                <RouterLink class="button" :to="`/cases/${item.id}`">打开</RouterLink>
                <button class="button danger" :disabled="deletingId === item.id" @click="deleteCase(item)">
                  {{ deletingId === item.id ? "删除中" : confirmingId === item.id ? "确认删除" : "删除" }}
                </button>
                <button v-if="confirmingId === item.id" class="button" @click="confirmingId = ''">取消</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="!cases.length" class="empty-state">暂无案件。</div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";

import Badge from "@/components/Badge.vue";
import PageHeader from "@/components/PageHeader.vue";
import { api } from "@/services/api";
import type { CaseItem } from "@/types";

const cases = ref<CaseItem[]>([]);
const deletingId = ref("");
const confirmingId = ref("");

async function load() {
  cases.value = await api.cases();
}

async function deleteCase(item: CaseItem) {
  if (confirmingId.value !== item.id) {
    confirmingId.value = item.id;
    return;
  }
  deletingId.value = item.id;
  try {
    await api.deleteCase(item.id);
    confirmingId.value = "";
    await load();
  } finally {
    deletingId.value = "";
  }
}

onMounted(load);

function caseTypeLabel(type: string) {
  return {
    contract: "合同纠纷",
    labor: "劳动争议",
    marriage: "婚姻家事",
    debt: "债权债务",
    traffic: "交通事故",
    company: "公司商事",
    real_estate: "房产纠纷",
    criminal: "刑事咨询",
    other: "其他",
  }[type] ?? type;
}

function caseStatusLabel(status: string) {
  return {
    open: "进行中",
    collecting_info: "信息收集中",
    closed: "已关闭",
  }[status] ?? status;
}
</script>
