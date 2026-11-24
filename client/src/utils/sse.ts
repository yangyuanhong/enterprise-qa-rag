/**
 * 流式问答：用 fetch 读取后端 text/event-stream 响应。
 * 原生 EventSource 只支持 GET 且不能自定义请求头，所以这里手动解析 SSE。
 */
import { handleUnauthorized, TOKEN_KEY } from '@/api/request'
import type { Source } from '@/api/types'

/** 后端推送的事件类型 */
export type AskEvent =
  | { type: 'token'; content: string }
  | { type: 'sources'; sources: Source[] }
  | { type: 'done'; message_id: number }
  | { type: 'error'; msg: string }

/** 提问参数 */
export interface AskParams {
  session_id: number
  question: string
  kb_id?: number | null
}

/**
 * 发起流式提问
 * @param params 提问参数
 * @param onEvent 每收到一个事件就回调一次
 * @param signal 用于中途停止生成
 */
export async function askStream(
  params: AskParams,
  onEvent: (event: AskEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch('/api/chat/ask', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY) ?? ''}`,
    },
    body: JSON.stringify(params),
    signal,
  })

  if (response.status === 401) {
    handleUnauthorized()
    throw new Error('登录已过期')
  }
  // 参数错误时后端返回普通 JSON 而不是事件流
  const contentType = response.headers.get('Content-Type') ?? ''
  if (!contentType.includes('text/event-stream')) {
    const res = await response.json()
    throw new Error(res.msg || '请求失败')
  }

  const reader = response.body!.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // SSE 消息之间用空行分隔，最后一段可能不完整，留到下次拼接
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''
    for (const part of parts) {
      const line = part.trim()
      if (line.startsWith('data:')) {
        onEvent(JSON.parse(line.slice(5).trim()) as AskEvent)
      }
    }
  }
}
