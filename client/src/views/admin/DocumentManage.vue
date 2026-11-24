<!-- 文档管理：按知识库筛选、上传（后台自动向量化，列表显示进度）、重建索引、删除 -->
<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox, type UploadRawFile } from 'element-plus'
import { documentApi, knowledgeApi } from '@/api'
import type { DocumentItem, KnowledgeBase } from '@/api/types'

const route = useRoute()
const UPDATE_TYPE = ['txt', 'md', 'pdf', 'docx', "csv"]
const ACCEPT = UPDATE_TYPE.map(item=>("."+item)).join(",")


/** 状态展示配置 */
const STATUS_MAP: Record<number, { text: string; type: 'info' | 'success' | 'danger' | 'warning' }> = {
  0: { text: '排队中', type: 'info' },
  1: { text: '已向量化', type: 'success' },
  2: { text: '失败', type: 'danger' },
  3: { text: '处理中', type: 'warning' },
}
/** 排队中、处理中的文档还在后台处理，列表需要轮询刷新 */
const UNFINISHED = [0, 3]
const POLL_INTERVAL = 3000

const kbList = ref<KnowledgeBase[]>([])
const loading = ref(false)
const list = ref<DocumentItem[]>([])
const total = ref(0)
const query = reactive({
  page: 1,
  size: 10,
  keyword: '',
  // 从知识库管理页跳转过来时带有 kb_id
  kb_id: route.query.kb_id ? Number(route.query.kb_id) : undefined,
})

let pollTimer: ReturnType<typeof setTimeout> | undefined

/**
 * 加载文档列表。当前页有未处理完的文档时，3 秒后自动再刷新一次，全部完成后停止
 * @param silent 为 true 时不显示表格 loading，轮询刷新时使用，避免表格每 3 秒闪一次
 */
async function loadList(silent = false) {
  clearTimeout(pollTimer)
  if (!silent) loading.value = true
  try {
    const data = await documentApi.list(query)
    list.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
    // 请求失败时也继续轮询，网络恢复后进度能自动更新
    if (list.value.some((d) => UNFINISHED.includes(d.status))) {
      pollTimer = setTimeout(() => loadList(true), POLL_INTERVAL)
    }
  }
}

onBeforeUnmount(() => clearTimeout(pollTimer))

/** 搜索时回到第一页 */
function handleSearch() {
  query.page = 1
  loadList()
}

/**
 * 字节数转为易读格式
 * @param size 字节数
 */
function formatSize(size: number) {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

// ---------- 上传弹窗 ----------
const uploadVisible = ref(false)
const uploading = ref(false)
const uploadKbId = ref<number>()
const uploadFile = ref<UploadRawFile>()

/** 打开上传弹窗，默认选中当前筛选的知识库 */
function openUpload() {
  uploadKbId.value = query.kb_id ?? kbList.value[0]?.id
  uploadFile.value = undefined
  uploadVisible.value = true
}

/**
 * 选择文件时校验类型和大小，返回 false 阻止 el-upload 自动上传
 * @param file 选中的文件
 */
function beforeUpload(file: UploadRawFile) {
  const ext = file.name.split('.').pop()?.toLowerCase() ?? ''
  if (!UPDATE_TYPE.includes(ext)) {
    ElMessage.warning(`仅支持 ${UPDATE_TYPE.join('、')} 格式`)
    return false
  }
  if (file.size > 20 * 1024 * 1024) {
    ElMessage.warning('文件不能超过 20MB')
    return false
  }
  uploadFile.value = file
  return false
}

/** 提交上传：后端保存文件后立即返回，解析和向量化在后台执行，进度在列表中查看 */
async function submitUpload() {
  if (!uploadKbId.value) return ElMessage.warning('请选择知识库')
  if (!uploadFile.value) return ElMessage.warning('请选择文件')

  const form = new FormData()
  form.append('file', uploadFile.value)
  form.append('kb_id', String(uploadKbId.value))
  uploading.value = true
  try {
    const res = await documentApi.upload(form)
    ElMessage.success(res.msg)
    uploadVisible.value = false
    loadList()
  } finally {
    uploading.value = false
  }
}

/**
 * 重建索引：加入后台队列后立即返回，列表会自动轮询显示进度
 * @param row 文档
 */
async function reindex(row: DocumentItem) {
  const res = await documentApi.reindex(row.id)
  ElMessage.success(res.msg)
  loadList()
}

/**
 * 删除文档
 * @param row 文档
 */
async function removeDoc(row: DocumentItem) {
  await ElMessageBox.confirm(`确定删除文档「${row.file_name}」吗？对应的向量数据也会删除。`, '提示', {
    type: 'warning',
  })
  await documentApi.remove(row.id)
  ElMessage.success('删除成功')
  loadList()
}

onMounted(async () => {
  kbList.value = await knowledgeApi.list()
  loadList()
})
</script>

<template>
  <div class="page-card">
    <div class="toolbar">
      <div class="toolbar-left">
        <el-select v-model="query.kb_id" placeholder="全部知识库" clearable style="width: 180px" @change="handleSearch">
          <el-option v-for="kb in kbList" :key="kb.id" :label="kb.name" :value="kb.id" />
        </el-select>
        <el-input
          v-model="query.keyword"
          placeholder="搜索文件名"
          prefix-icon="Search"
          clearable
          style="width: 220px"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-button icon="Search" @click="handleSearch">搜索</el-button>
      </div>
      <el-button type="primary" icon="Upload" @click="openUpload">上传文档</el-button>
    </div>

    <el-table v-loading="loading" :data="list" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="file_name" label="文件名" min-width="180" show-overflow-tooltip />
      <el-table-column prop="kb_name" label="知识库" width="120" />
      <el-table-column label="类型" width="80">
        <template #default="{ row }">{{ row.file_type.toUpperCase() }}</template>
      </el-table-column>
      <el-table-column label="大小" width="100">
        <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
      </el-table-column>
      <el-table-column prop="chunk_count" label="片段数" width="80" />
      <el-table-column label="状态" width="260">
        <template #default="{ row }">
          <!-- 标签和进度放在同一行，进度过长时省略显示，鼠标悬停看全文 -->
          <div class="status-cell">
            <el-tooltip :disabled="!row.error_msg" :content="row.error_msg">
              <el-tag :type="STATUS_MAP[row.status]?.type" class="status-tag">
                <el-icon v-if="UNFINISHED.includes(row.status)" class="is-loading"><Loading /></el-icon>
                {{ STATUS_MAP[row.status]?.text }}
              </el-tag>
            </el-tooltip>
            <span v-if="row.status === 3 && row.progress" class="progress-text" :title="row.progress">
              {{ row.progress }}
            </span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="上传时间" width="170" />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <!-- 处理中不能重建或删除：后台任务会和这些操作冲突 -->
          <el-button link type="primary" :disabled="UNFINISHED.includes(row.status)" @click="reindex(row)">
            重建索引
          </el-button>
          <el-button link type="danger" :disabled="UNFINISHED.includes(row.status)" @click="removeDoc(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.size"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadList()"
      />
    </div>

    <el-dialog v-model="uploadVisible" title="上传文档" width="500px" :close-on-click-modal="!uploading">
      <el-form label-width="70px">
        <el-form-item label="知识库">
          <el-select v-model="uploadKbId" placeholder="请选择" style="width: 100%">
            <el-option v-for="kb in kbList" :key="kb.id" :label="kb.name" :value="kb.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="文件">
          <el-upload drag :show-file-list="false" :before-upload="beforeUpload" :accept="ACCEPT" style="width: 100%">
            <el-icon :size="40" color="#c0c4cc"><UploadFilled /></el-icon>
            <div v-if="uploadFile" class="upload-name">{{ uploadFile.name }}</div>
            <div v-else>将文件拖到此处，或 <em>点击选择</em></div>
            <template #tip>
              <div class="upload-tip">
                支持 {{ UPDATE_TYPE.join(' / ') }}，单个文件不超过 20MB。上传后在后台解析和向量化，可在列表中查看进度
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :disabled="uploading" @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="submitUpload">
          {{ uploading ? '正在上传…' : '上传' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.upload-name {
  color: #409eff;
  word-break: break-all;
}

.upload-tip {
  font-size: 12px;
  color: #909399;
}

.status-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.status-tag {
  flex-shrink: 0;
}

/* 标签内的转圈图标和文字之间留点间距 */
.status-tag :deep(.el-icon) {
  margin-right: 4px;
}

.progress-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-size: 12px;
  color: #909399;
}
</style>
