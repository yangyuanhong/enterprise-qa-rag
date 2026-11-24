/**
 * 前后端共用的数据类型定义
 */

/** 用户角色 */
export type Role = 'admin' | 'user'

/** 用户信息 */
export interface User {
  id: number
  username: string
  nickname: string
  role: Role
  status: number
  created_at: string
}

/** 知识库 */
export interface KnowledgeBase {
  id: number
  name: string
  description: string
  doc_count: number
  created_at: string
}

/** 文档，status：0 排队中，1 已向量化，2 失败，3 处理中 */
export interface DocumentItem {
  id: number
  kb_id: number
  kb_name: string
  file_name: string
  file_type: string
  file_size: number
  chunk_count: number
  status: number
  /** 处理阶段，如“识别图片 3/5”，处理完成后为空 */
  progress: string
  error_msg: string
  created_at: string
}

/** 会话 */
export interface ChatSession {
  id: number
  title: string
  created_at: string
  updated_at: string
}

/** 回答引用的知识片段 */
export interface Source {
  file_name: string
  content: string
  score?: number
}

/** 聊天消息 */
export interface ChatMessage {
  id?: number
  role: 'user' | 'assistant'
  content: string
  sources: Source[]
  created_at?: string
  /** 前端状态：是否正在生成中 */
  loading?: boolean
}