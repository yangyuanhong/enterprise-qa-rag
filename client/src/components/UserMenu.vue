<!-- 顶栏右侧的用户菜单：显示昵称，提供修改密码、退出登录 -->
<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { authApi } from '@/api'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const store = useUserStore()

const dialogVisible = ref(false)
const formRef = ref<FormInstance>()
const form = reactive({ old_password: '', new_password: '', confirm: '' })
const rules: FormRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [{ required: true, min: 6, message: '新密码至少 6 位', trigger: 'blur' }],
  confirm: [
    {
      validator: (_rule, value, callback) =>
        value === form.new_password ? callback() : callback(new Error('两次输入的密码不一致')),
      trigger: 'blur',
    },
  ],
}

/**
 * 处理下拉菜单命令
 * @param command 菜单项标识
 */
async function handleCommand(command: string) {
  if (command === 'password') {
    Object.assign(form, { old_password: '', new_password: '', confirm: '' })
    dialogVisible.value = true
  } else if (command === 'logout') {
    await ElMessageBox.confirm('确定退出登录吗？', '提示', { type: 'warning' })
    store.logout()
    router.push('/login')
  }
}

/** 提交修改密码，成功后要求重新登录 */
async function submitPassword() {
  if (!(await formRef.value?.validate().catch(() => false))) return
  const res = await authApi.changePassword({ old_password: form.old_password, new_password: form.new_password })
  ElMessage.success(res.msg)
  dialogVisible.value = false
  store.logout()
  router.push('/login')
}
</script>

<template>
  <el-dropdown @command="handleCommand">
    <span class="user-name">
      <el-avatar :size="28" icon="UserFilled" />
      {{ store.user?.nickname }}
      <el-tag v-if="store.isAdmin" size="small" effect="plain">管理员</el-tag>
      <el-icon><ArrowDown /></el-icon>
    </span>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item command="password" icon="Key">修改密码</el-dropdown-item>
        <el-dropdown-item command="logout" icon="SwitchButton" divided>退出登录</el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>

  <el-dialog v-model="dialogVisible" title="修改密码" width="420px">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="原密码" prop="old_password">
        <el-input v-model="form.old_password" type="password" show-password />
      </el-form-item>
      <el-form-item label="新密码" prop="new_password">
        <el-input v-model="form.new_password" type="password" show-password />
      </el-form-item>
      <el-form-item label="确认密码" prop="confirm">
        <el-input v-model="form.confirm" type="password" show-password />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="submitPassword">确定</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.user-name {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  outline: none;
}
</style>
