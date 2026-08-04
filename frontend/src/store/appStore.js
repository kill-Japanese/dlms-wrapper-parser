import { create } from 'zustand'
import { checkHealth } from '../services/api.js'

/**
 * 应用全局状态管理
 */
const useAppStore = create((set, get) => ({
  // 主题模式: 'light' | 'dark'
  theme: 'light',

  // 侧边栏折叠状态
  sidebarCollapsed: false,

  // 当前页面标题
  pageTitle: 'DLMS Wrapper 解析器',

  // 全局加载状态
  globalLoading: false,

  // 后端健康状态
  backendHealth: {
    status: 'unknown', // 'unknown' | 'healthy' | 'unhealthy' | 'checking'
    version: null,
    appName: null,
    lastCheck: null,
    error: null
  },

  // Actions
  setTheme: (theme) => set({ theme }),

  toggleTheme: () => set((state) => ({
    theme: state.theme === 'light' ? 'dark' : 'light'
  })),

  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

  toggleSidebar: () => set((state) => ({
    sidebarCollapsed: !state.sidebarCollapsed
  })),

  setPageTitle: (title) => set({ pageTitle: title }),

  setGlobalLoading: (loading) => set({ globalLoading: loading }),

  // 检查后端健康状态
  async checkBackendHealth() {
    set({ backendHealth: { ...get().backendHealth, status: 'checking' } })
    try {
      const result = await checkHealth()
      set({
        backendHealth: {
          status: result.status === 'healthy' ? 'healthy' : 'unhealthy',
          version: result.version || null,
          appName: result.app_name || null,
          lastCheck: new Date().toISOString(),
          error: null
        }
      })
      return result
    } catch (err) {
      set({
        backendHealth: {
          status: 'unhealthy',
          version: null,
          appName: null,
          lastCheck: new Date().toISOString(),
          error: err.message || '无法连接到后端服务'
        }
      })
      return null
    }
  },

  // 重置健康状态
  resetBackendHealth() {
    set({
      backendHealth: {
        status: 'unknown',
        version: null,
        appName: null,
        lastCheck: null,
        error: null
      }
    })
  }
}))

export default useAppStore
