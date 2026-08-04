import { create } from 'zustand'

const useDataModelStore = create((set, get) => ({
  // 是否加载
  loaded: false,

  // 数模列表
  dataModels: [],

  // 当前活动数模
  activeDataModel: null,

  // 对象列表
  objects: [],

  // 选中的对象
  selectedObject: null,

  // 搜索关键词
  searchQuery: '',

  // 加载状态
  loading: false,
  error: null,

  // Actions
  setLoaded: (loaded) => set({ loaded }),

  setDataModels: (models) => set({ dataModels: models }),

  setActiveDataModel: (model) => set({ activeDataModel: model }),

  setObjects: (objects) => set({ objects }),

  setSelectedObject: (obj) => set({ selectedObject: obj }),

  setSearchQuery: (query) => set({ searchQuery: query }),

  setLoading: (loading) => set({ loading }),

  setError: (error) => set({ error }),

  addDataModel: (model) => set((state) => ({
    dataModels: [...state.dataModels, model]
  })),

  removeDataModel: (id) => set((state) => ({
    dataModels: state.dataModels.filter((m) => m.id !== id)
  })),

  loadDataModel: async (loadFn, id = null) => {
    set({ loading: true, error: null })
    try {
      const result = id ? await loadFn(id) : await loadFn()
      set({
        loaded: true,
        loading: false
      })
      return result
    } catch (error) {
      set({ loading: false, error: error.message })
      throw error
    }
  },

  reset: () => set({
    loaded: false,
    objects: [],
    selectedObject: null,
    searchQuery: '',
    error: null
  })
}))

export default useDataModelStore
