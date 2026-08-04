import { create } from 'zustand'

const STORAGE_KEY = 'dlms_pull_presets'

// 从 localStorage 加载预设
const loadPresetsFromStorage = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      return JSON.parse(saved)
    }
  } catch (e) {
    console.error('加载预设失败:', e)
  }
  // 默认预设
  return [
    {
      id: 'default-electricity',
      name: '电表基础数据',
      description: '读取电表的基础电能数据',
      system_title: null,
      device_name: null,
      key_type: 'GUEK',
      operations: [
        { class_id: 3, obis: '1.0.1.8.0.255', attribute_id: 2, name: '有功总电能（正向）' },
        { class_id: 3, obis: '1.0.2.8.0.255', attribute_id: 2, name: '有功总电能（反向）' },
        { class_id: 1, obis: '1.0.32.7.0.255', attribute_id: 2, name: '电压' },
        { class_id: 1, obis: '1.0.31.7.0.255', attribute_id: 2, name: '电流' },
      ]
    }
  ]
}

// 保存到 localStorage
const savePresetsToStorage = (presets) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(presets))
  } catch (e) {
    console.error('保存预设失败:', e)
  }
}

const usePullStore = create((set, get) => ({
  // 预设列表
  presets: loadPresetsFromStorage(),

  // 当前编辑的预设
  activePreset: null,

  // 执行结果
  executionResult: null,

  // 加载状态
  loading: false,

  // 错误信息
  error: null,

  // 对象选择器可见性
  objectSelectorVisible: false,

  // 当前要添加操作的预设ID（用于对象选择器回调）
  selectorTargetPresetId: null,

  // ---------- Actions ----------

  setLoading: (loading) => set({ loading }),

  setError: (error) => set({ error }),

  setActivePreset: (preset) => set({ activePreset: preset }),

  setExecutionResult: (result) => set({ executionResult: result }),

  clearExecutionResult: () => set({ executionResult: null }),

  setObjectSelectorVisible: (visible) => set({ objectSelectorVisible: visible }),

  setSelectorTargetPresetId: (id) => set({ selectorTargetPresetId: id }),

  // 加载预设列表
  loadPresets: async (apiFn) => {
    set({ loading: true, error: null })
    try {
      const result = await apiFn()
      if (result?.presets) {
        set({ presets: result.presets, loading: false })
        savePresetsToStorage(result.presets)
      }
      return result
    } catch (error) {
      set({ loading: false, error: error.message })
      // 后端失败时使用本地存储的数据
      return { presets: get().presets }
    }
  },

  // 保存预设列表到后端
  savePresets: async (apiFn) => {
    const { presets } = get()
    set({ loading: true, error: null })
    try {
      const result = await apiFn(presets)
      set({ loading: false })
      savePresetsToStorage(presets)
      return result
    } catch (error) {
      set({ loading: false, error: error.message })
      // 后端失败时仍保存到本地
      savePresetsToStorage(presets)
      throw error
    }
  },

  // 添加预设
  addPreset: (preset) => {
    set((state) => {
      const newPreset = {
        system_title: null,
        device_name: null,
        key_type: 'GUEK',
        ...preset
      }
      const newPresets = [...state.presets, newPreset]
      savePresetsToStorage(newPresets)
      return { presets: newPresets }
    })
  },

  // 更新预设
  updatePreset: (id, updates) => {
    set((state) => {
      const newPresets = state.presets.map((p) =>
        p.id === id ? { ...p, ...updates } : p
      )
      savePresetsToStorage(newPresets)
      // 如果当前编辑的是这个预设，也更新
      const newActive = state.activePreset?.id === id
        ? { ...state.activePreset, ...updates }
        : state.activePreset
      return { presets: newPresets, activePreset: newActive }
    })
  },

  // 删除预设
  deletePreset: (id) => {
    set((state) => {
      const newPresets = state.presets.filter((p) => p.id !== id)
      savePresetsToStorage(newPresets)
      const newActive = state.activePreset?.id === id ? null : state.activePreset
      return { presets: newPresets, activePreset: newActive }
    })
  },

  // 向预设添加操作
  addOperation: (presetId, operation) => {
    set((state) => {
      const newPresets = state.presets.map((p) => {
        if (p.id === presetId) {
          return {
            ...p,
            operations: [...p.operations, operation]
          }
        }
        return p
      })
      savePresetsToStorage(newPresets)
      const newActive = state.activePreset?.id === presetId
        ? { ...state.activePreset, operations: [...state.activePreset.operations, operation] }
        : state.activePreset
      return { presets: newPresets, activePreset: newActive }
    })
  },

  // 更新预设中的操作
  updateOperation: (presetId, operationIndex, updates) => {
    set((state) => {
      const newPresets = state.presets.map((p) => {
        if (p.id === presetId) {
          const newOps = [...p.operations]
          newOps[operationIndex] = { ...newOps[operationIndex], ...updates }
          return { ...p, operations: newOps }
        }
        return p
      })
      savePresetsToStorage(newPresets)
      const newActive = state.activePreset?.id === presetId
        ? {
            ...state.activePreset,
            operations: state.activePreset.operations.map((op, idx) =>
              idx === operationIndex ? { ...op, ...updates } : op
            )
          }
        : state.activePreset
      return { presets: newPresets, activePreset: newActive }
    })
  },

  // 删除预设中的操作
  deleteOperation: (presetId, operationIndex) => {
    set((state) => {
      const newPresets = state.presets.map((p) => {
        if (p.id === presetId) {
          return {
            ...p,
            operations: p.operations.filter((_, idx) => idx !== operationIndex)
          }
        }
        return p
      })
      savePresetsToStorage(newPresets)
      const newActive = state.activePreset?.id === presetId
        ? {
            ...state.activePreset,
            operations: state.activePreset.operations.filter((_, idx) => idx !== operationIndex)
          }
        : state.activePreset
      return { presets: newPresets, activePreset: newActive }
    })
  },

  // 执行预设
  executePreset: async (apiFn, presetId, options = {}) => {
    set({ loading: true, error: null, executionResult: null })
    try {
      const result = await apiFn(presetId, options)
      set({ loading: false, executionResult: result })
      return result
    } catch (error) {
      set({ loading: false, error: error.message })
      throw error
    }
  },

  // 从数模页面快速添加对象到预设
  addObjectToPreset: (presetId, objectInfo) => {
    const operation = {
      class_id: objectInfo.class_id || objectInfo.class || 0,
      obis: objectInfo.obis,
      attribute_id: objectInfo.attribute_id || 2,
      name: objectInfo.name || objectInfo.obis
    }
    get().addOperation(presetId, operation)
  },

  // 重置
  reset: () => {
    set({
      presets: loadPresetsFromStorage(),
      activePreset: null,
      executionResult: null,
      loading: false,
      error: null,
      objectSelectorVisible: false,
      selectorTargetPresetId: null
    })
  }
}))

export default usePullStore
