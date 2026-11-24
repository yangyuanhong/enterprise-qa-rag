<!-- 用户管理：分页列表、搜索、新增、编辑、启用/禁用、重置密码、删除 -->
<script lang="ts" setup name="UserManage">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { userApi } from '@/api'
import type { Role, User } from '@/api/types'
import { useUserStore } from '@/stores/user'

const store = useUserStore()

const loading = ref(false)
const list = ref<User[]>([])

const total = ref(0)
const query = reactive({ page: 1, size: 10, keyword: '' })


/** 加载用户列表 */
async function loadList() {
  loading.value = true
  try {
    const data = await userApi.list(query)
    list.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

/** 搜索时回到第一页 */
function handleSearch() {
  query.page = 1
  loadList()
}

// ---------- 新增 / 编辑弹窗 ----------
const dialogVisible = ref(false)
const formRef = ref<FormInstance>()
const editingId = ref<number | null>(null)
const form = reactive({ username: '', nickname: '', role: 'user' as Role })
const rules: FormRules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  nickname: [{ required: true, message: '请输入昵称', trigger: 'blur' }],
}

/**
 * 打开弹窗
 * @param row 传入则为编辑，否则为新增
 */
function openDialog(row?: User) {
  editingId.value = row?.id ?? null
  Object.assign(form, { username: row?.username ?? '', nickname: row?.nickname ?? '', role: row?.role ?? 'user' })
  dialogVisible.value = true
  formRef.value?.clearValidate()
}

/** 提交新增或编辑 */
async function submitForm() {
  if (!(await formRef.value?.validate().catch(() => false))) return
  const res = editingId.value
    ? await userApi.update(editingId.value, { nickname: form.nickname, role: form.role })
    : await userApi.create(form)
  ElMessage.success(editingId.value ? res.msg : `${res.msg}，默认密码 123456`)
  dialogVisible.value = false
  loadList()
}

/**
 * 切换启用/禁用状态
 * @param row 用户
 */
async function toggleStatus(row: User) {
  const status = row.status === 1 ? 0 : 1
  await userApi.update(row.id, { status })
  ElMessage.success(status === 1 ? '已启用' : '已禁用')
  loadList()
}

/**
 * 重置密码为 123456
 * @param row 用户
 */
async function resetPassword(row: User) {
  await ElMessageBox.confirm(`确定将「${row.nickname}」的密码重置为 123456 吗？`, '提示', { type: 'warning' })
  const res = await userApi.resetPassword(row.id)
  ElMessage.success(res.msg)
}

/**
 * 删除用户
 * @param row 用户
 */
async function removeUser(row: User) {
  await ElMessageBox.confirm(`确定删除用户「${row.nickname}」吗？其会话记录也会一并删除。`, '提示', {
    type: 'warning',
  })
  await userApi.remove(row.id)
  ElMessage.success('删除成功')
  loadList()
}

onMounted(loadList)
</script>
<template>
  <div class="page-card">
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="query.keyword"
          placeholder="搜索账号或昵称"
          prefix-icon="Search"
          clearable
          style="width: 240px"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-button icon="Search" @click="handleSearch">搜索</el-button>
      </div>
      <el-button type="primary" icon="Plus" @click="openDialog()">新增用户</el-button>
    </div>
     <el-table v-loading="loading" :data="list" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="账号" />
      <el-table-column prop="nickname" label="昵称" />
      <el-table-column label="角色" width="110">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : 'info'">{{ row.role === 'admin' ? '管理员' : '普通用户' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'warning'">{{ row.status === 1 ? '启用' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button link type="warning" :disabled="row.id === store.user?.id" @click="toggleStatus(row)">
            {{ row.status === 1 ? '禁用' : '启用' }}
          </el-button>
          <el-button link type="primary" @click="resetPassword(row)">重置密码</el-button>
          <el-button link type="danger" :disabled="row.id === store.user?.id" @click="removeUser(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.size"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadList"
      />
    </div>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑用户' : '新增用户'" width="460px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="70px">
        <el-form-item label="账号" prop="username">
          <el-input v-model="form.username" :disabled="!!editingId" />
        </el-form-item>
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="form.nickname" />
        </el-form-item>
        <el-form-item label="角色">
          <el-radio-group v-model="form.role" :disabled="editingId === store.user?.id">
            <el-radio value="user">普通用户</el-radio>
            <el-radio value="admin">管理员</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="!editingId" label="密码">
          <span class="form-tip">默认密码 123456，用户登录后可自行修改</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.form-tip {
  color: #909399;
  font-size: 13px;
}
</style>