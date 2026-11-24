<!-- 智能问答页：左侧会话列表，右侧消息区和输入框，回答逐字流式显示 -->
<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { chatApi, knowledgeApi } from '@/api'
import type { ChatMessage, ChatSession, KnowledgeBase } from '@/api/types'
import { useUserStore } from '@/stores/user'
import { askStream } from '@/utils/sse'
import MessageItem from '@/components/MessageItem.vue'
import UserMenu from '@/components/UserMenu.vue'

const store = useUserStore()

/** 输入框为空时展示的示例问题 */
const EXAMPLES = ['试用期一般多久？', '年假有几天？', 'VPN 服务器地址是多少？', '出差住宿标准是多少？']

const sessions = ref<ChatSession[]>([])
const currentId = ref<number | null>(null)
const messages = ref<ChatMessage[]>([])
const kbList = ref<KnowledgeBase[]>([])
/** 检索范围，空表示全部知识库 */
const kbId = ref<number | null>(null)
const question = ref('')
const generating = ref(false)
const messageBox = ref<HTMLDivElement>()
let abortController: AbortController | null = null

/** 滚动到消息底部 */
async function scrollToBottom() {
  await nextTick()
  messageBox.value?.scrollTo({ top: messageBox.value.scrollHeight })
}

/** 加载会话列表 */
async function loadSessions() {
  sessions.value = await chatApi.sessions()
}

/**
 * 切换会话并加载消息
 * @param id 会话ID
 */
async function selectSession(id: number) {
  if (generating.value) return ElMessage.warning('请等待当前回答完成')
  currentId.value = id
  messages.value = await chatApi.messages(id)
  scrollToBottom()
}

/** 新建会话 */
async function newSession() {
  if (generating.value) return
  const session = await chatApi.createSession()
  sessions.value.unshift(session)
  currentId.value = session.id
  messages.value = []
}

/**
 * 删除会话
 * @param s 会话
 */
async function removeSession(s: ChatSession) {
  await ElMessageBox.confirm(`确定删除会话「${s.title}」吗？`, '提示', { type: 'warning' })
  await chatApi.removeSession(s.id)
  sessions.value = sessions.value.filter((x) => x.id !== s.id)
  if (currentId.value === s.id) {
    currentId.value = null
    messages.value = []
  }
}

/**
 * 发送问题，流式接收回答
 * @param text 问题文本，不传则取输入框内容
 */
async function send(text?: string) {
  const q = (text ?? question.value).trim()
  if (!q || generating.value) return

  // 没有选中会话时自动新建
  if (!currentId.value) {
    await newSession()
  }
  question.value = ''
  messages.value.push({ role: 'user', content: q, sources: [] })
  messages.value.push({ role: 'assistant', content: '', sources: [], loading: true })
  // 必须通过数组取出响应式代理对象，直接修改原始对象不会触发视图更新
  const answer = messages.value[messages.value.length - 1]!
  scrollToBottom()

  generating.value = true
  abortController = new AbortController()
  try {
    await askStream(
      { session_id: currentId.value!, question: q, kb_id: kbId.value },
      (event) => {
        if (event.type === 'token') {
          answer.content += event.content
          scrollToBottom()
        } else if (event.type === 'sources') {
          answer.sources = event.sources
        } else if (event.type === 'error') {
          ElMessage.error(`回答出错：${event.msg}`)
        }
      },
      abortController.signal,
    )
  } catch (e) {
    if ((e as Error).name !== 'AbortError') {
      answer.content ||= `请求失败：${(e as Error).message}`
    }
  } finally {
    answer.loading = false
    generating.value = false
    abortController = null
    // 刷新会话列表（首次提问后标题会更新）
    loadSessions()
  }
}

/** 停止生成 */
function stop() {
  abortController?.abort()
}

/**
 * 输入框按键：Enter 发送，Shift+Enter 换行
 * @param e 键盘事件
 */
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    send()
  }
}

onMounted(async () => {
  kbList.value = await knowledgeApi.list()
  await loadSessions()
  if (sessions.value.length) {
    selectSession(sessions.value[0]!.id)
  }
})
</script>

<template>
  <div class="chat-page">
    <!-- 左侧会话列表 -->
    <aside class="sidebar">
      <div class="brand">
        <el-icon :size="22"><ChatDotRound /></el-icon>
        <span>知识库问答</span>
      </div>
      <el-button type="primary" icon="Plus" class="new-btn" @click="newSession">新建对话</el-button>
      <div class="session-list">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="session-item"
          :class="{ active: s.id === currentId }"
          @click="selectSession(s.id)"
        >
          <el-icon><ChatLineSquare /></el-icon>
          <span class="session-title" :title="s.title">{{ s.title }}</span>
          <el-icon class="session-del" title="删除会话" @click.stop="removeSession(s)"><Delete /></el-icon>
        </div>
        <el-empty v-if="!sessions.length" description="暂无会话" :image-size="60" />
      </div>
    </aside>

    <!-- 右侧对话区 -->
    <main class="main">
      <header class="header">
        <div class="scope">
          <span>检索范围：</span>
          <el-select v-model="kbId" placeholder="全部知识库" clearable style="width: 180px">
            <el-option v-for="kb in kbList" :key="kb.id" :label="kb.name" :value="kb.id" />
          </el-select>
        </div>
        <div class="header-right">
          <router-link v-if="store.isAdmin" to="/admin/home">
            <el-button plain icon="Setting">管理后台</el-button>
          </router-link>
          <UserMenu />
        </div>
      </header>

      <div ref="messageBox" class="messages">
        <div v-if="!messages.length" class="welcome">
          <h2>您好，{{ store.user?.nickname }}</h2>
          <p>我是企业知识库助手，可以回答公司制度、IT 支持、财务报销等问题。试试这些：</p>
          <div class="examples">
            <el-button v-for="q in EXAMPLES" :key="q" round @click="send(q)">{{ q }}</el-button>
          </div>
        </div>
        <MessageItem v-for="(m, i) in messages" :key="m.id ?? `tmp-${i}`" :message="m" />
      </div>

      <div class="input-area">
        <el-input
          v-model="question"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 6 }"
          resize="none"
          maxlength="1000"
          placeholder="请输入问题，Enter 发送，Shift + Enter 换行"
          aria-label="输入问题"
          @keydown="onKeydown"
        />
        <el-button v-if="generating" type="danger" plain icon="VideoPause" @click="stop">停止</el-button>
        <el-button v-else type="primary" icon="Promotion" :disabled="!question.trim()" @click="send()">发送</el-button>
      </div>
    </main>
  </div>
</template>

<style scoped>
.chat-page {
  display: flex;
  height: 100%;
}

.sidebar {
  width: 260px;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-right: 1px solid #ebeef5;
}

.brand {
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

.new-btn {
  margin: 16px;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px 16px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: 6px;
  cursor: pointer;
  color: #606266;
}

.session-item:hover {
  background: #f5f7fa;
}

.session-item.active {
  background: #ecf5ff;
  color: #409eff;
}

.session-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-del {
  visibility: hidden;
  color: #909399;
}

.session-item:hover .session-del {
  visibility: visible;
}

.session-del:hover {
  color: #f56c6c;
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}

.scope {
  display: flex;
  align-items: center;
  color: #606266;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px 10%;
}

.welcome {
  text-align: center;
  margin-top: 12vh;
  color: #606266;
}

.welcome h2 {
  color: #303133;
}

.examples {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
  margin-top: 24px;
}

.examples .el-button + .el-button {
  margin-left: 0;
}

.input-area {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding: 16px 10% 24px;
}
</style>
