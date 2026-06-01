<template>
  <span :class="['badge', tone]"><slot /></span>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ tone?: "blue" | "green" | "amber" | "red" | "slate" }>(), {
  tone: "slate",
});
</script>

