<template>
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark">律</div>
      <div>
        <div class="brand-name">律智界</div>
        <div class="brand-subtitle">个人法律工作台</div>
      </div>
    </div>

    <nav class="nav">
      <div class="nav-section">
        <p>导航</p>
        <RouterLink v-for="item in overview" :key="item.to" :to="item.to" class="nav-link">
          <component :is="item.icon" class="nav-icon" />
          {{ item.label }}
        </RouterLink>
      </div>
      <div class="nav-section">
        <p>核心能力</p>
        <RouterLink
          v-for="item in core"
          :key="item.to"
          :to="item.to"
          :class="['nav-link', isActive(item) && 'router-link-active']"
        >
          <component :is="item.icon" class="nav-icon" />
          {{ item.label }}
        </RouterLink>
      </div>
      <div class="nav-section">
        <p>系统</p>
        <RouterLink v-for="item in system" :key="item.to" :to="item.to" class="nav-link">
          <component :is="item.icon" class="nav-icon" />
          {{ item.label }}
        </RouterLink>
      </div>
    </nav>

    <div class="sidebar-status">
      <span class="status-dot"></span>
      微信桥仅负责消息通道
    </div>
  </aside>
</template>

<script setup lang="ts">
import {
  Bot,
  FileDiff,
  LayoutDashboard,
  MessageCircle,
  Network,
  Scale,
  Settings,
} from "lucide-vue-next";
import { useRoute } from "vue-router";

const route = useRoute();

const overview = [
  { to: "/dashboard", label: "总览", icon: LayoutDashboard, match: ["/dashboard"] },
];

const core = [
  { to: "/wechat", label: "微信接入", icon: MessageCircle, match: ["/wechat"] },
  { to: "/documents", label: "文件版本控制", icon: FileDiff, match: ["/documents"] },
  { to: "/cases", label: "案件与推理", icon: Scale, match: ["/cases", "/reasoning"] },
  { to: "/agents", label: "律所智能体", icon: Bot, match: ["/agents"] },
];

const system = [
  { to: "/openclaw", label: "微信桥配置", icon: Network, match: ["/openclaw"] },
  { to: "/settings", label: "系统设置", icon: Settings, match: ["/settings"] },
];

function isActive(item: { match: string[] }) {
  return item.match.some((path) => route.path === path || route.path.startsWith(`${path}/`));
}
</script>
