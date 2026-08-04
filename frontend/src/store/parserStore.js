import { create } from 'zustand'

// localStorage 键名
const STORAGE_KEY = 'dlms-parser-security-config'

// 从 localStorage 加载安全配置
const loadSecurityConfig = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      return {
        guek: parsed.guek || '',
        gubk: parsed.gubk || '',
        ak: parsed.ak || '',
        kek: parsed.kek || '',
        systemTitle: parsed.systemTitle || '',
        invocationCounter: parsed.invocationCounter ?? 0,
        useCiphering: parsed.useCiphering ?? true,
        useCompression: parsed.useCompression ?? true,
        selectedKeyType: parsed.selectedKeyType || 'guek',
        // 兼容旧字段
        blockCipherKey: parsed.blockCipherKey || parsed.guek || '',
        authenticationKey: parsed.authenticationKey || parsed.ak || ''
      }
    }
  } catch (e) {
    console.warn('Failed to load security config from localStorage:', e)
  }
  return null
}

// 默认安全配置
const defaultSecurityConfig = {
  guek: '',                    // Global Unicast Encryption Key
  gubk: '',                    // Global Unicast Broadcast Key
  ak: '',                      // Authentication Key
  kek: '',                     // Key Encryption Key
  systemTitle: '',             // System Title
  invocationCounter: 0,        // Invocation Counter
  useCiphering: true,          // 启用加密
  useCompression: true,        // 启用压缩
  selectedKeyType: 'guek',     // 当前选中的密钥类型: 'guek' | 'gubk' | 'custom'
  // 兼容旧字段
  blockCipherKey: '',
  authenticationKey: ''
}

const initialSecurityConfig = loadSecurityConfig() || defaultSecurityConfig

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
  securityConfig: initialSecurityConfig,

  // 安全配置面板展开状态
  securityPanelExpanded: true,

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

  updateSecurityConfig: (config) => set((state) => {
    const newConfig = {
      ...state.securityConfig,
      ...config
    }
    // 同步兼容字段
    if (config.guek !== undefined) {
      newConfig.blockCipherKey = config.guek
    }
    if (config.ak !== undefined) {
      newConfig.authenticationKey = config.ak
    }
    // 保存到 localStorage
    try {
      const toSave = {
        guek: newConfig.guek,
        gubk: newConfig.gubk,
        ak: newConfig.ak,
        kek: newConfig.kek,
        systemTitle: newConfig.systemTitle,
        invocationCounter: newConfig.invocationCounter,
        useCiphering: newConfig.useCiphering,
        useCompression: newConfig.useCompression,
        selectedKeyType: newConfig.selectedKeyType
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave))
    } catch (e) {
      console.warn('Failed to save security config to localStorage:', e)
    }
    return { securityConfig: newConfig }
  }),

  setSecurityPanelExpanded: (expanded) => set({ securityPanelExpanded: expanded }),

  toggleSecurityPanel: () => set((state) => ({
    securityPanelExpanded: !state.securityPanelExpanded
  })),

  setLoading: (loading) => set({ loading }),

  setError: (error) => set({ error }),

  reset: () => set({
    rawHex: '',
    parseResult: null,
    error: null
  }),

  // 重置安全配置为默认值
  resetSecurityConfig: () => set({ securityConfig: defaultSecurityConfig })
}))

export default useParserStore
