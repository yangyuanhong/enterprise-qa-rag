<!-- 管理后台布局：左侧菜单 + 顶栏 + 内容区 -->
<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import UserMenu from "@/components/UserMenu.vue";

const route = useRoute();

/** 左侧菜单配置 */
const menus = [
  { path: "/admin/home", title: "数据概览", icon: "DataAnalysis" },
  { path: "/admin/users", title: "用户管理", icon: "User" },
  { path: "/admin/knowledge", title: "知识库管理", icon: "Collection" },
  { path: "/admin/documents", title: "文档管理", icon: "Document" },
];

/** 当前页面标题，显示在顶栏 */
const pageTitle = computed(() => (route.meta.title as string) ?? "");
</script>
<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">
        <el-icon :size="22"><ChatDotRound /></el-icon>
        <span>知识库管理后台</span>
      </div>
      <el-menu :default-active="route.path" router class="menu">
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path">
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span class="page-title">{{ pageTitle }}</span>
        <div class="header-right">
          <router-link to="/chat">
            <el-button type="primary" plain icon="ChatLineRound"
              >进入问答</el-button
            >
          </router-link>
          <UserMenu />
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>
<style scoped>
.layout {
  height: 100%;
}

.aside {
  background: #fff;
  border-right: 1px solid #ebeef5;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #409eff;
  border-bottom: 1px solid #ebeef5;
}

.menu {
  border-right: none;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.main {
  padding: 20px;
}
</style>
