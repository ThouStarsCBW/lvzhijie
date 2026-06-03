<template>
  <PageHeader title="新建案件" description="手动创建独立案件，也可以稍后绑定客户会话和文件。">
    <RouterLink class="button" to="/cases">返回案件</RouterLink>
  </PageHeader>
  <section class="page-content">
    <section class="panel narrow-panel">
      <h2 class="panel-title">案件信息</h2>
      <p class="panel-subtitle">先建立业务容器，再补事实、证据、任务和推理。</p>
      <label class="small muted">案件标题</label>
      <input v-model="form.title" class="input" style="margin: 6px 0 14px" />
      <label class="small muted">案件类型</label>
      <select v-model="form.case_type" class="select" style="margin: 6px 0 14px">
        <option value="contract">合同纠纷</option>
        <option value="labor">劳动争议</option>
        <option value="marriage">婚姻家事</option>
        <option value="debt">债权债务</option>
        <option value="traffic">交通事故</option>
        <option value="company">公司商事</option>
        <option value="real_estate">房产纠纷</option>
        <option value="criminal">刑事咨询</option>
        <option value="other">其他</option>
      </select>
      <label class="small muted">摘要</label>
      <textarea v-model="form.summary" class="textarea" style="margin-top: 6px" />
      <div class="form-actions">
        <button class="button primary" :disabled="!form.title.trim()" @click="create">创建案件</button>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { reactive } from "vue";
import { useRouter } from "vue-router";

import PageHeader from "@/components/PageHeader.vue";
import { api } from "@/services/api";

const router = useRouter();
const form = reactive({
  title: "",
  case_type: "other",
  summary: "",
});

async function create() {
  if (!form.title.trim()) return;
  const created = await api.createCase({
    title: form.title.trim(),
    case_type: form.case_type,
    summary: form.summary.trim(),
  });
  await router.push(`/cases/${created.id}`);
}
</script>
