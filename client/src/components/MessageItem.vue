<!-- 单条聊天消息：用户消息靠右显示纯文本，助手消息靠左渲染 Markdown 并可展开引用来源 -->
<script setup lang="ts">
import { computed } from 'vue'
import { Marked } from 'marked'
import type { ChatMessage } from '@/api/types'

const props = defineProps<{ message: ChatMessage }>()

/**
 * 转义 HTML 特殊字符
 * @param text 原始文本
 */
function escapeHtml(text: string) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

// Markdown 解析器：把内容中的原始 HTML 当普通文本显示，防止 XSS
const marked = new Marked({
  breaks: true,
  renderer: {
    html: ({ text }) => escapeHtml(text),
  },
})

/** 助手回答渲染后的 HTML */
const html = computed(() => marked.parse(props.message.content || '', { async: false }) as string)
</script>

<template>
  <div class="message" :class="message.role">
    <el-avatar
      :size="36"
      :icon="message.role === 'user' ? 'UserFilled' : 'Service'"
      :class="message.role === 'user' ? 'avatar-user' : 'avatar-bot'"
    />
    <div class="bubble-wrap">
      <div class="bubble">
        <template v-if="message.role === 'user'">{{ message.content }}</template>
        <template v-else>
          <div v-if="message.loading && !message.content" class="thinking">
            <el-icon class="is-loading"><Loading /></el-icon> 正在检索知识库并思考…
          </div>
          <div v-else class="markdown" v-html="html" />
        </template>
      </div>

      <el-collapse v-if="message.sources?.length" class="sources">
        <el-collapse-item :title="`参考来源（${message.sources.length}）`">
          <div v-for="(s, i) in message.sources" :key="i" class="source-item">
            <div class="source-head">
              <el-icon><Document /></el-icon>
              <span>{{ s.file_name }}</span>
              <el-tag v-if="s.score !== undefined" size="small" type="info">相似度 {{ s.score }}</el-tag>
            </div>
            <div class="source-content">{{ s.content }}</div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>
  </div>
</template>

<style scoped>
.message {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.message.user {
  flex-direction: row-reverse;
}

.avatar-user {
  background: #409eff;
  flex-shrink: 0;
}

.avatar-bot {
  background: #67c23a;
  flex-shrink: 0;
}

.bubble-wrap {
  max-width: 75%;
  min-width: 0;
}

.bubble {
  padding: 10px 14px;
  border-radius: 8px;
  line-height: 1.7;
  word-break: break-word;
  background: #fff;
  border: 1px solid #ebeef5;
}

.message.user .bubble {
  background: #409eff;
  border-color: #409eff;
  color: #fff;
  white-space: pre-wrap;
}

.thinking {
  color: #909399;
  display: flex;
  align-items: center;
  gap: 6px;
}

.markdown :deep(p) {
  margin: 0 0 8px;
}

.markdown :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown :deep(ul),
.markdown :deep(ol) {
  margin: 4px 0;
  padding-left: 20px;
}

.markdown :deep(code) {
  background: #f4f4f5;
  padding: 1px 4px;
  border-radius: 3px;
  font-family: Consolas, monospace;
}

.sources {
  margin-top: 8px;
  border: none;
  --el-collapse-header-height: 32px;
  --el-collapse-header-bg-color: transparent;
  --el-collapse-content-bg-color: transparent;
  --el-collapse-header-text-color: #909399;
}

.source-item {
  padding: 8px 10px;
  margin-bottom: 8px;
  background: #fafafa;
  border-radius: 6px;
}

.source-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  margin-bottom: 4px;
}

.source-content {
  font-size: 13px;
  color: #606266;
  white-space: pre-wrap;
  max-height: 160px;
  overflow-y: auto;
}
</style>
