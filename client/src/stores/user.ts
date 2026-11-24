/**
 * 用户状态：保存 token 和当前登录用户信息
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { authApi } from '@/api'
import { TOKEN_KEY } from '@/api/request'
import type { User } from '@/api/types'

export const useUserStore = defineStore('user', () => {
  /** 登录凭证，持久化到 localStorage，刷新页面不丢失 */
  const token = ref<string>(localStorage.getItem(TOKEN_KEY) ?? '')
  /** 当前用户信息，刷新页面后通过 fetchProfile 重新获取 */
  const user = ref<User | null>(null)

  /** 是否为管理员 */
  const isAdmin = computed(() => user.value?.role === 'admin')

  /**
   * 登录
   * @param username 账号
   * @param password 密码
   */
  async function login(username: string, password: string) {
    const data = await authApi.login({ username, password })
    token.value = data.token
    user.value = data.user
    localStorage.setItem(TOKEN_KEY, data.token)
  }

  /** 获取当前用户信息 */
  async function fetchProfile() {
    user.value = await authApi.profile()
  }

  /** 退出登录 */
  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
  }

  return { token, user, isAdmin, login, fetchProfile, logout }
})
