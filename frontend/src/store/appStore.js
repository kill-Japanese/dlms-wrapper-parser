import { create } from 'zustand'

/**
 * 应用全局状态管理
 */
const useAppStore = create((set) => ({
  // 主题模式: 'light' | 'dark'
  theme: 'light',

  // 侧边栏折叠状态
  sidebarCollapsed: false,

  // 当前页面标题
  pageTitle: 'DLMS Wrapper 解析器',

  // 全局加载状态
  globalLoading: false,

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

  setGlobalLoading: (loading) => set({ globalLoading: loading })
}))

export default useAppStore
