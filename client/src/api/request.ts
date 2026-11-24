/**
 * Axios 封装：统一 baseURL、自动携带 token、统一处理后端返回的 {code, msg, data}
 */
import axios, { type AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'

/** 后端统一响应结构 */
export interface ApiResult<T = unknown> {
  code: number
  msg: string
  data: T
}

/** 分页数据结构 */
export interface PageData<T> {
  list: T[]
  total: number
  page: number
  size: number
}

export const TOKEN_KEY = 'eqa_token'

const instance = axios.create({
  baseURL: '/api',
  timeout: 120000, // 上传 20MB 文件在网速慢时也需要一段时间，超时设长一点（向量化已改为后台执行）
})

// 请求拦截：在请求头中加入 token
instance.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) { 
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})

/** 登录失效：清除 token 并跳转登录页 */
export function handleUnauthorized() {
  localStorage.removeItem(TOKEN_KEY)
  if (location.pathname !== '/login') {
    location.href = '/login'
  }
}

// 响应拦截：code 非 0 时弹出错误提示并 reject
instance.interceptors.response.use(
  (response) => {
    const res = response.data as ApiResult
    if (res.code !== 0) {
      ElMessage.error(res.msg || '请求失败')
      return Promise.reject(new Error(res.msg))
    }
    return response
  },
  (err) => {
    const status = err.response?.status
    const msg = err.response?.data?.msg || err.message || '网络错误'
    if (status === 401) {
      handleUnauthorized()
    }
    ElMessage.error(msg)
    return Promise.reject(err)
  }
)

/**
 * 通用请求方法，直接返回 data 部分
 * @param config axios 请求配置
 */
export async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const response = await instance.request<ApiResult<T>>(config)
  return response.data.data
}

/**
 * 请求并返回完整结果（需要用到后端 msg 提示时使用）
 * @param config axios 请求配置
 */
export async function requestRaw<T>(config: AxiosRequestConfig): Promise<ApiResult<T>> {
  const response = await instance.request<ApiResult<T>>(config)
  return response.data
}