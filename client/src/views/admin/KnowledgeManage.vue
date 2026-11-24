<!-- 知识库管理：列表、新增、编辑、删除 -->
<script lang="ts" setup name="KnowledgeManage">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { knowledgeApi } from '@/api'
import type { KnowledgeBase } from '@/api/types'

const router = useRouter()

const loading = ref(false)
const list = ref<KnowledgeBase[]>([])

/** 加载知识库列表 */
async function loadList() {
  loading.value = true
  try {
    list.value = await knowledgeApi.list()
  } finally {
    loading.value = false
  }
}

// ---------- 新增 / 编辑弹窗 ----------
const dialogVisible = ref(false)
const formRef = ref<FormInstance>()
const editingId = ref<number | null>(null)
const form = reactive({ name: '', description: '' })
const rules: FormRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
}

/**
 * 打开弹窗
 * @param row 传入则为编辑，否则为新增
 */
function openDialog(row?: KnowledgeBase) {
  editingId.value = row?.id ?? null
  Object.assign(form, { name: row?.name ?? '', description: row?.description ?? '' })
  dialogVisible.value = true
  formRef.value?.clearValidate()
}

/** 提交新增或编辑 */
async function submitForm() {
  if (!(await formRef.value?.validate().catch(() => false))) return
  const res = editingId.value ? await knowledgeApi.update(editingId.value, form) : await knowledgeApi.create(form)
  ElMessage.success(res.msg)
  dialogVisible.value = false
  loadList()
}

/**
 * 删除知识库（需先删除其下文档）
 * @param row 知识库
 */
async function removeKb(row: KnowledgeBase) {
  await ElMessageBox.confirm(`确定删除知识库「${row.name}」吗？`, '提示', { type: 'warning' })
  await knowledgeApi.remove(row.id)
  ElMessage.success('删除成功')
  loadList()
}

/**
 * 跳转到文档管理并按该知识库筛选
 * @param row 知识库
 */
function viewDocs(row: KnowledgeBase) {
  router.push({ path: '/admin/documents', query: { kb_id: row.id } })
}

onMounted(loadList)
</script>
<template>
  <div class="page-card">
    <div class="toolbar">
      <span class="tip">知识库用于对文档分类，问答时可以选择只在某个知识库中检索</span>
      <el-button type="primary" icon="Plus" @click="openDialog()">新增知识库</el-button>
    </div>

    <el-table v-loading="loading" :data="list" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="名称" width="180" />
      <el-table-column prop="description" label="描述" show-overflow-tooltip />
      <el-table-column label="文档数" width="100">
        <template #default="{ row }">
          <el-button link type="primary" @click="viewDocs(row)">{{ row.doc_count }}</el-button>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button link type="danger" @click="removeKb(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑知识库' : '新增知识库'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="60px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" maxlength="100" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" maxlength="500" show-word-limit />
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
.tip {
  color: #909399;
}
</style>