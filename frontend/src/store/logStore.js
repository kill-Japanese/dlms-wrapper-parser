import { create } from 'zustand'

const useLogStore = create((set, get) => ({
  // 解析日志
  parseLogs: [],

  // 数据交互日志
  dataLogs: [],

  // 过滤器
  filter: {
    level: 'all',
    type: 'all',
    keyword: ''
  },

  // 当前查看的标签页
  activeTab: 'parse',

  // 加载状态
  loading: false,
  error: null,

  // Actions
  addParseLog: (log) => set((state) => ({
    parseLogs: [
      {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        level: 'info',
        ...log
      },
      ...state.parseLogs
    ].slice(0, 500) // 最多保留500条
  })),

  addDataLog: (log) => set((state) => ({
    dataLogs: [
      {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        direction: 'in',
        ...log
      },
      ...state.dataLogs
    ].slice(0, 500)
  })),

  setParseLogs: (logs) => set({ parseLogs: logs }),

  setDataLogs: (logs) => set({ dataLogs: logs }),

  setFilter: (filter) => set((state) => ({
    filter: { ...state.filter, ...filter }
  })),

  setActiveTab: (tab) => set({ activeTab: tab }),

  setLoading: (loading) => set({ loading }),

  setError: (error) => set({ error }),

  clearParseLogs: () => set({ parseLogs: [] }),

  clearDataLogs: () => set({ dataLogs: [] }),

  clearAll: () => set({
    parseLogs: [],
    dataLogs: []
  }),

  // 获取过滤后的日志
  getFilteredParseLogs: () => {
    const { parseLogs, filter } = get()
    return parseLogs.filter((log) => {
      if (filter.level !== 'all' && log.level !== filter.level) return false
      if (filter.keyword && !JSON.stringify(log).toLowerCase().includes(filter.keyword.toLowerCase())) return false
      return true
    })
  },

  getFilteredDataLogs: () => {
    const { dataLogs, filter } = get()
    return dataLogs.filter((log) => {
      if (filter.type !== 'all' && log.direction !== filter.type) return false
      if (filter.keyword && !JSON.stringify(log).toLowerCase().includes(filter.keyword.toLowerCase())) return false
      return true
    })
  }
}))

export default useLogStore
