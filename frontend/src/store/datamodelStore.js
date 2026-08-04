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
  // 是否使用了降级接口（旧版后端兼容）
  usingFallbackApi: false,

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
        totalObjects: result.total_objects || 0,
        sourceFile: result.source_file,
        classes: result.classes || []
      })

      // 如果 loaded=true 但 total_objects=0，可能是数据有问题
      if (result.loaded && (result.total_objects === 0 || result.total_objects === undefined)) {
        set({ error: '数模已加载但对象数为0，数据可能为空或格式异常' })
      }

      return result
    } catch (err) {
      // 404 表示未加载，这是正常情况
      if (err.status !== 404) {
        set({ error: err.message || '检查数模状态失败' })
      }
      return null
    }
  },

  // ---- 上传数模 ----
  async uploadFile(file) {
    set({ uploading: true, uploadProgress: 0, error: null, usingFallbackApi: false })
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
        totalObjects: result.total_objects || 0,
        classes: result.classes || [],
        sourceFile: file.name
      })

      // 上传成功后加载对象列表
      await get().loadObjects()

      // 检查加载结果，如果对象数为0给出警告
      const state = get()
      if (state.objects.length === 0 && !state.error) {
        set({ error: '上传成功但未解析到任何对象，请检查数模文件格式' })
      }

      return result
    } catch (err) {
      set({ uploading: false, uploadProgress: 0, error: err.message || '上传失败' })
      throw err
    }
  },

  // ---- 加载对象列表（带降级逻辑）----
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

      let result
      let usedFallback = false

      // 先尝试新接口 /datamodel/objects
      try {
        result = await getObjectHeaders(queryParams)
      } catch (apiErr) {
        // 如果是 404，降级使用旧接口 /datamodel/list 并在前端过滤
        if (apiErr.status === 404) {
          console.warn('新接口 /datamodel/objects 不存在，降级使用旧接口 /datamodel/list')
          usedFallback = true

          // 使用旧接口获取全部数据，然后前端过滤出 attribute_id=0 的对象
          const listResult = await getDataModelList(queryParams)

          // 旧接口可能返回 { items: [...] } 或直接数组 或 { results: [...] }
          const allItems = listResult.objects || listResult.items || listResult.results || listResult || []

          // 过滤出对象标题行（attribute_id=0）
          const objectHeaders = allItems.filter((obj) => {
            const attrId = obj.attribute_id
            return attrId === 0 || attrId === '0' || attrId === null || attrId === undefined
          })

          result = {
            objects: objectHeaders,
            total: objectHeaders.length
          }
        } else {
          // 其他错误直接抛出
          throw apiErr
        }
      }

      // 后端返回格式: { objects: [...], total: N }
      const objectList = result.objects || []
      const total = result.total ?? objectList.length

      set({
        objects: objectList,
        totalObjectHeaders: total,
        loading: false,
        isSearching: false,
        usingFallbackApi: usedFallback
      })

      // 如果使用了降级接口且对象数为0，设置警告
      if (usedFallback && objectList.length === 0) {
        set({ error: '当前后端版本较旧，使用兼容模式加载，但未找到对象数据' })
      }

      return objectList
    } catch (err) {
      const errorMsg = err.message || '加载对象列表失败'

      // 区分不同类型的错误
      let displayMsg = errorMsg
      if (err.status === 404) {
        displayMsg = '接口不存在，请检查后端版本是否支持数据模型功能'
      } else if (err.status === 500) {
        displayMsg = `服务器错误：${errorMsg}`
      } else if (!err.status) {
        displayMsg = '无法连接到后端服务，请检查后端是否启动'
      }

      set({ loading: false, error: displayMsg, objects: [] })
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
      const objectHeaders = (result.results || []).filter((obj) => {
        const attrId = obj.attribute_id
        return attrId === 0 || attrId === '0' || attrId === null || attrId === undefined
      })

      set({
        objects: objectHeaders,
        loading: false
      })

      return objectHeaders
    } catch (err) {
      const errorMsg = err.message || '搜索失败'
      let displayMsg = errorMsg
      if (err.status === 404) {
        displayMsg = '搜索接口不存在，请检查后端版本'
      } else if (!err.status) {
        displayMsg = '无法连接到后端服务，请检查后端是否启动'
      }
      set({ loading: false, error: displayMsg })
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
        set({ error: err.message || '加载类列表失败' })
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
      const errorMsg = err.message || '加载对象详情失败'
      let displayMsg = errorMsg
      if (err.status === 404) {
        displayMsg = '对象详情接口不存在，请检查后端版本'
      } else if (!err.status) {
        displayMsg = '无法连接到后端服务，请检查后端是否启动'
      }
      set({ detailLoading: false, error: displayMsg })
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
      error: null,
      usingFallbackApi: false
    })
  }
}))

export default useDataModelStore
