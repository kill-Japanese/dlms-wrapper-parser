import { create } from 'zustand'

const useParserStore = create((set, get) => ({
  // 原始Hex输入
  rawHex: '',

  // 解析结果
  parseResult: null,

  // 解析方向: 'unpack' | 'pack'
  direction: 'unpack',

  // 解析历史
  parseHistory: [],

  // 安全配置
  securityConfig: {
    blockCipherKey: '',
    systemTitle: '',
    invocationCounter: 0,
    useCiphering: true,
    useCompression: true,
    authenticationKey: ''
  },

  // 加载状态
  loading: false,
  error: null,

  // Actions
  setRawHex: (hex) => set({ rawHex: hex }),

  setParseResult: (result) => set({ parseResult: result }),

  setDirection: (direction) => set({ direction }),

  addToHistory: (item) => set((state) => ({
    parseHistory: [
      {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        ...item
      },
      ...state.parseHistory
    ].slice(0, 100) // 最多保留100条
  })),

  clearHistory: () => set({ parseHistory: [] }),

  updateSecurityConfig: (config) => set((state) => ({
    securityConfig: {
      ...state.securityConfig,
      ...config
    }
  })),

  setLoading: (loading) => set({ loading }),

  setError: (error) => set({ error }),

  reset: () => set({
    rawHex: '',
    parseResult: null,
    error: null
  })
}))

export default useParserStore
