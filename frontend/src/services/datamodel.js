import api from './api.js'

// 上传数模文件
export function uploadDataModel(file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/datamodel/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 获取数模列表
export function listDataModels(params = {}) {
  return api.get('/datamodel/list', { params })
}

// 搜索数模对象
export function searchDataModel(query) {
  return api.get('/datamodel/search', {
    params: { q: query }
  })
}

// 获取数模详情
export function getDataModelDetail(id) {
  return api.get(`/datamodel/${id}`)
}

// 获取对象列表
export function getObjects(datamodelId, params = {}) {
  return api.get(`/datamodel/${datamodelId}/objects`, { params })
}

// 获取对象详情
export function getObjectDetail(datamodelId, objectId) {
  return api.get(`/datamodel/${datamodelId}/objects/${objectId}`)
}

// 删除数模
export function deleteDataModel(id) {
  return api.delete(`/datamodel/${id}`)
}

// 加载当前活动数模
export function loadActiveDataModel() {
  return api.get('/datamodel/active')
}

// 设置活动数模
export function setActiveDataModel(id) {
  return api.post(`/datamodel/${id}/activate`)
}

export default {
  uploadDataModel,
  listDataModels,
  searchDataModel,
  getDataModelDetail,
  getObjects,
  getObjectDetail,
  deleteDataModel,
  loadActiveDataModel,
  setActiveDataModel
}
