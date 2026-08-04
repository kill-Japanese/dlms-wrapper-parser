import { create } from 'zustand'
import {
  uploadDataModel,
  getDataModelList,
  getObjectHeaders,
  searchDataModel,
  getDataModelClasses,
  getDataModelStatus,
  getObjectDetail
} from '../services/datamodel.js'

const useDataModelStore = create((set, get) => ({
  // 数据模型是否已加载
  isLoaded: false,
  // 源文件名
  sourceFile: null,
  // 总对象数（所有条目数，包括属性和方法）
  totalObjects: 0,
  // 对象标题行总数（attribute_id=0的对象数）
  totalObjectHeaders: 0,

  // 对象列表（对象标题行，attribute_id=0）
  objects: [],
  // 类ID列表
  classes: [],
  // 当前选中的类过滤
  selectedClassId: null,

  // 选中的对象基本信息
  selectedObject: null,
  // 选中对象的完整详情（含属性和方法）
  selectedObjectDetail: null,

  // 搜索关键词
  searchQuery: '',
  // 是否处于搜索模式
  isSearching: false,

  // 加载状态
  loading: false,
  uploading: false,
  uploadProgress: 0,
  detailLoading: false,
  error: null,

  // ---- 基础 setters ----
  setSearchQuery: (query) => set({ searchQuery: query }),
  setSelectedClassId: (classId) => set({ selectedClassId: classId }),
  setError: (error) => set({ error }),

  // ---- 加载状态检查 ----
  async checkStatus() {
    try {
      const result = await getDataModelStatus()
      set({
        isLoaded: result.loaded,
        totalObjects: result.total_objects,
        sourceFile: result.source_file,
        classes: result.classes || []
      })
      return result
    } catch (err) {
      // 404 表示未加载，这是正常情况
      if (err.status !== 404) {
        set({ error: err.message })
      }
      return null
    }
  },

  // ---- 上传数模 ----
  async uploadFile(file) {
    set({ uploading: true, uploadProgress: 0, error: null })
    try {
      const result = await uploadDataModel(file, (progressEvent) => {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        )
        set({ uploadProgress: percentCompleted })
      })

      set({
        uploading: false,
        uploadProgress: 100,
        isLoaded: true,
        totalObjects: result.total_objects,
        classes: result.classes || [],
        sourceFile: file.name
      })

      // 上传成功后加载对象列表
      await get().loadObjects()

      return result
    } catch (err) {
      set({ uploading: false, uploadProgress: 0, error: err.message })
      throw err
    }
  },

  // ---- 加载对象列表 ----
  async loadObjects(params = {}) {
    set({ loading: true, error: null })
    try {
      const state = get()
      const queryParams = {
        limit: params.limit || 500,
        offset: params.offset || 0
      }
      if (state.selectedClassId) {
        queryParams.class_id = state.selectedClassId
      }

      // 使用专用的对象标题行接口，后端已过滤attribute_id=0
      const result = await getObjectHeaders(queryParams)

      // 后端返回格式: { objects: [...], total: N }
      const objectList = result.objects || []
      const total = result.total ?? objectList.length

      set({
        objects: objectList,
        totalObjectHeaders: total,
        loading: false,
        isSearching: false
      })

      return objectList
    } catch (err) {
      set({ loading: false, error: err.message, objects: [] })
      throw err
    }
  },

  // ---- 搜索对象 ----
  async search(keyword) {
    if (!keyword || !keyword.trim()) {
      // 清空搜索，重新加载列表
      await get().loadObjects()
      return
    }

    set({ loading: true, error: null, isSearching: true })
    try {
      const state = get()
      const result = await searchDataModel(keyword, state.selectedClassId)

      // 过滤出对象本身（attribute_id=0 或 attribute_id=null/undefined）
      // 兼容 attribute_id 为数字0或字符串"0"的情况
      const objectHeaders = result.results.filter((obj) => {
        const attrId = obj.attribute_id
        return attrId === 0 || attrId === '0' || attrId === null || attrId === undefined
      })

      set({
        objects: objectHeaders,
        loading: false
      })

      return objectHeaders
    } catch (err) {
      set({ loading: false, error: err.message })
      throw err
    }
  },

  // ---- 加载类ID列表 ----
  async loadClasses() {
    try {
      const result = await getDataModelClasses()
      set({ classes: result.classes || [] })
      return result.classes
    } catch (err) {
      if (err.status !== 404) {
        set({ error: err.message })
      }
      return []
    }
  },

  // ---- 选择对象并加载详情 ----
  async selectObject(obj) {
    set({ selectedObject: obj, selectedObjectDetail: null, detailLoading: true, error: null })
    try {
      const detail = await getObjectDetail(obj.class_id, obj.obis)
      set({ selectedObjectDetail: detail, detailLoading: false })
      return detail
    } catch (err) {
      set({ detailLoading: false, error: err.message })
      // 即使详情加载失败，也保留基本选中状态
      return null
    }
  },

  // ---- 重置 ----
  reset() {
    set({
      isLoaded: false,
      sourceFile: null,
      totalObjects: 0,
      totalObjectHeaders: 0,
      objects: [],
      classes: [],
      selectedClassId: null,
      selectedObject: null,
      selectedObjectDetail: null,
      searchQuery: '',
      isSearching: false,
      loading: false,
      uploading: false,
      uploadProgress: 0,
      detailLoading: false,
      error: null
    })
  }
}))

export default useDataModelStore
