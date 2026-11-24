/**
 * 后端接口定义，按模块分组
 */
import { request, requestRaw, type PageData } from './request'
import type { ChatMessage, ChatSession, DocumentItem, KnowledgeBase, User } from './types'

/** 分页查询参数 */
export interface PageQuery {
  page: number
  size: number
  keyword?: string
  kb_id?: number
}

/** 认证接口 */
export const authApi = {
  /** 登录 */
  login: (data: { username: string; password: string }) =>
    request<{ token: string, user: User }>({ url: "/auth/login", method: 'post', data }),
  /** 获取当前登录用户信息 */
  profile: () => request<User>({ url: "/auth/profile" }),
  /** 修改密码 */
  changePassword: (data: { old_password: string; new_password: string }) =>
    requestRaw({ url: "/auth/change-password", method: 'put', data }),
}

/** 用户管理接口 */
export const userApi = {
  list: (params: PageQuery) => request<PageData<User>>({ url: '/users', params }),
  create: (data: Partial<User> & { password?: string }) =>
    requestRaw<User>({ url: '/users', method: 'post', data }),
  update: (id: number, data: Partial<User>) => requestRaw<User>({ url: `/users/${id}`, method: 'put', data }),
  resetPassword: (id: number) => requestRaw({ url: `/users/${id}/reset-password`, method: 'put' }),
  remove: (id: number) => requestRaw({ url: `/users/${id}`, method: 'delete' }),
}

/** 知识库接口 */
export const knowledgeApi = {
  list: () => request<KnowledgeBase[]>({ url: '/knowledge' }),
  create: (data: Partial<KnowledgeBase>) => requestRaw({ url: '/knowledge', method: 'post', data }),
  update: (id: number, data: Partial<KnowledgeBase>) =>
    requestRaw({ url: `/knowledge/${id}`, method: 'put', data }),
  remove: (id: number) => requestRaw({ url: `/knowledge/${id}`, method: 'delete' }),
}

/** 文档接口 */
export const documentApi = {
  list: (params: PageQuery) => request<PageData<DocumentItem>>({ url: '/documents', params }),
  /** 上传文档，form 中包含 file 和 kb_id。后端保存文件后立即返回，向量化在后台执行 */
  upload: (form: FormData) => requestRaw<DocumentItem>({ url: '/documents/upload', method: 'post', data: form }),
  /** 重建索引，加入后台队列后立即返回 */
  reindex: (id: number) => requestRaw({ url: `/documents/${id}/reindex`, method: 'post' }),
  remove: (id: number) => requestRaw({ url: `/documents/${id}`, method: 'delete' }),
}

/** 会话接口（流式提问见 utils/sse.ts） */
export const chatApi = {
  sessions: () => request<ChatSession[]>({ url: '/chat/sessions' }),
  createSession: () => request<ChatSession>({ url: '/chat/sessions', method: 'post' }),
  removeSession: (id: number) => requestRaw({ url: `/chat/sessions/${id}`, method: 'delete' }),
  messages: (id: number) => request<ChatMessage[]>({ url: `/chat/sessions/${id}/messages` }),
}

/** 统计接口 */
export const statsApi = {
  overview: () =>
    request<{
      user_count: number
      kb_count: number
      doc_count: number
      question_count: number
      today_question_count: number
    }>({ url: '/stats/overview' }),
  trend: () => request<{ dates: string[]; counts: number[] }>({ url: '/stats/trend' }),
  docDistribution: () => request<{ name: string; value: number }[]>({ url: '/stats/doc-distribution' }),
  activeUsers: () => request<{ names: string[]; counts: number[] }>({ url: '/stats/active-users' }),
}