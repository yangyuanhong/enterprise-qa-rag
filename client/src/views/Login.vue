<!-- 登录页：管理员登录后进入后台首页，普通用户进入问答页 -->
<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const store = useUserStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({
  username: '',
  password: ''
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

// 提交登录
async function handleLogin() {
  if (!(await formRef.value?.validate().catch(() => false))) return
  loading.value = true
  try {
    await store.login(form.username, form.password)
    router.push(store.isAdmin ? "/admin/home" : "/chat")
  } finally {
    loading.value = false
  }
}
</script>
<template>
  <div class="login-page">
    <div class="login-card">
      <div class="title">
        <el-icon :size="32" color="#409eff"><ChatDotRound /></el-icon>
        <h2>企业知识库问答系统</h2>
      </div>
      <p class="subtitle">基于 LangChain + Ollama 的 RAG 智能助手</p>

      <el-form ref="formRef" :model="form" :rules="rules" size="large" @keyup.enter="handleLogin">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="账号" prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" prefix-icon="Lock" show-password />
        </el-form-item>
        <el-button type="primary" class="login-btn" :loading="loading" @click="handleLogin">登 录</el-button>
      </el-form>

      <p class="tip">测试账号：admin（管理员）/ zhangsan（普通用户），密码 123456</p>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #e8f1ff 0%, #f5f7fa 100%);
}

.login-card {
  width: 400px;
  padding: 40px 36px 28px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(64, 158, 255, 0.12);
}

.title {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.title h2 {
  margin: 0;
  font-size: 22px;
}

.subtitle {
  margin: 8px 0 28px;
  text-align: center;
  color: #909399;
}

.login-btn {
  width: 100%;
}

.tip {
  margin: 20px 0 0;
  font-size: 12px;
  text-align: center;
  color: #a8abb2;
}
</style>