import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";

import App from "./App.vue";
import AgentChatView from "./views/AgentChatView.vue";
import AgentsView from "./views/AgentsView.vue";
import CaseDetailView from "./views/CaseDetailView.vue";
import CaseNewView from "./views/CaseNewView.vue";
import CasesView from "./views/CasesView.vue";
import DashboardView from "./views/DashboardView.vue";
import DocumentDetailView from "./views/DocumentDetailView.vue";
import DocumentsView from "./views/DocumentsView.vue";
import LegalResearchView from "./views/LegalResearchView.vue";
import MockWechatView from "./views/MockWechatView.vue";
import OpenClawView from "./views/OpenClawView.vue";
import ReasoningView from "./views/ReasoningView.vue";
import WechatView from "./views/WechatView.vue";
import "./styles/app.css";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/dashboard" },
    { path: "/dashboard", component: DashboardView },
    { path: "/wechat", component: WechatView },
    { path: "/cases", component: CasesView },
    { path: "/cases/new", component: CaseNewView },
    { path: "/cases/:id", component: CaseDetailView, props: true },
    { path: "/cases/:id/chat", component: CaseDetailView, props: true },
    { path: "/cases/:id/tasks", component: CaseDetailView, props: true },
    { path: "/cases/:id/memory", component: CaseDetailView, props: true },
    { path: "/cases/:id/documents", component: CaseDetailView, props: true },
    { path: "/cases/:id/workflow", component: CaseDetailView, props: true },
    { path: "/cases/:id/reasoning", component: CaseDetailView, props: true },
    { path: "/documents", component: DocumentsView },
    { path: "/documents/:id", component: DocumentDetailView, props: true },
    { path: "/research", component: LegalResearchView },
    { path: "/reasoning", component: ReasoningView },
    { path: "/agents", component: AgentsView },
    { path: "/agents/:id", component: AgentChatView },
    { path: "/openclaw", component: OpenClawView },
    { path: "/settings", component: OpenClawView },
    { path: "/settings/mock-wechat", component: MockWechatView },
  ],
});

createApp(App).use(router).mount("#app");
