import api from './api.js'

// 上传数模Excel文件
export function uploadDataModel(file, onUploadProgress) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/datamodel/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    onUploadProgress
  })
}

// 获取对象列表（支持class_id过滤、分页）
export function getDataModelList(params = {}) {
  return api.get('/datamodel/list', { params })
}

// 获取对象标题行列表（仅attribute_id=0的对象，用于列表展示）
export function getObjectHeaders(params = {}) {
  return api.get('/datamodel/objects', { params })
}

// 搜索对象
export function searchDataModel(keyword, class_id) {
  const params = { keyword }
  if (class_id) {
    params.class_id = class_id
  }
  return api.get('/datamodel/search', { params })
}

// 获取所有类ID
export function getDataModelClasses() {
  return api.get('/datamodel/classes')
}

// 获取数据模型加载状态
export function getDataModelStatus() {
  return api.get('/datamodel/status')
}

// 获取单个对象的完整信息（含所有属性和方法）
export function getObjectDetail(class_id, obis) {
  return api.get(`/datamodel/object/${class_id}/${encodeURIComponent(obis)}`)
}

// 从 GitHub 导入数据模型
export function importFromGithub(url) {
  return api.post('/datamodel/import-github', { url })
}

export default {
  uploadDataModel,
  importFromGithub,
  getDataModelList,
  getObjectHeaders,
  searchDataModel,
  getDataModelClasses,
  getDataModelStatus,
  getObjectDetail
}
