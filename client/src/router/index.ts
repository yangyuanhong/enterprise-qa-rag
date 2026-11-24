/**
 * 路由配置与权限守卫
 * - /login           登录页（无需登录）
 * - /chat            智能问答（所有登录用户）
 * - /admin/*         管理后台（仅管理员）
 */
import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'


const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/chat' },
    {
      path: '/login',
      component: () => import('@/views/Login.vue'),
      meta: { public: true, title: '登录' },
    },
    {
      path: '/chat',
      component: () => import('@/views/chat/Chat.vue'),
      meta: { title: '智能问答' },
    },
    {
      path: '/admin',
      component: () => import('@/layouts/AdminLayout.vue'),
      redirect: '/admin/home',
      meta: { admin: true },
      children: [
        { path: 'home', component: () => import('@/views/admin/Home.vue'), meta: { title: '数据概览' } },
        { path: 'users', component: () => import('@/views/admin/UserManage.vue'), meta: { title: '用户管理' } },
        {
          path: 'knowledge',
          component: () => import('@/views/admin/KnowledgeManage.vue'),
          meta: { title: '知识库管理' },
        },
        {
          path: 'documents',
          component: () => import('@/views/admin/DocumentManage.vue'),
          meta: { title: '文档管理' },
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ]
})


// 全局前置守卫：未登录跳登录页，普通用户禁止进入管理后台
router.beforeEach(async (to) => {
  const store = useUserStore()
  if (to.meta.public) {
    return true
  }
  if (!store.token) {
    return '/login'
  }
  // 刷新页面后 store 中没有用户信息，需要重新获取
  if (!store.user) {
    try {
      await store.fetchProfile()
    } catch {
      store.logout()
      return '/login'
    }
  }
  if (to.matched.some((r) => r.meta.admin) && !store.isAdmin) {
    return '/chat'
  }
  return true
})

// 设置浏览器标题
router.afterEach((to) => {
  document.title = `${(to.meta.title as string) ?? ''} - 企业知识库问答系统`
})
export default router