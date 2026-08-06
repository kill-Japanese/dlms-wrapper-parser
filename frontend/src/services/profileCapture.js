import api from './api.js'

/**
 * Profile Capture Objects 管理 API
 * 注意：后端路由前缀是 /api/profile-capture
 * 前端 baseURL 是 /api，所以这里用 /profile-capture/xxx
 */

// 获取所有已配置的 Profile 列表
export async function getProfileCaptureList() {
  return api.get('/profile-capture/list')
}

// 获取指定 Profile 的配置详情
// 后端路由: GET /api/profile-capture/{profile_obis}
export async function getProfileCaptureDetail(profileObis) {
  return api.get(`/profile-capture/${encodeURIComponent(profileObis)}`)
}

// 保存（创建/更新）Profile capture_objects 配置
// 后端路由: POST /api/profile-capture/
export async function saveProfileCapture(profileObis, captureObjects, profileName = '', source = 'manual') {
  return api.post('/profile-capture/', {
    profile_obis: profileObis,
    capture_objects: captureObjects,
    profile_name: profileName,
    source
  })
}

// 删除指定 Profile 的配置
// 后端路由: DELETE /api/profile-capture/{profile_obis}
export async function deleteProfileCapture(profileObis) {
  return api.delete(`/profile-capture/${encodeURIComponent(profileObis)}`)
}

// 检查指定 Profile 是否已有配置
// 后端路由: GET /api/profile-capture/has/{profile_obis}
export async function hasProfileCapture(profileObis) {
  return api.get(`/profile-capture/has/${encodeURIComponent(profileObis)}`)
}

// 导出所有配置
// 后端路由: GET /api/profile-capture/export/all
export async function exportProfileCaptures() {
  return api.get('/profile-capture/export/all')
}

// 导入配置
// 后端路由: POST /api/profile-capture/import
export async function importProfileCaptures(configsData, overwrite = true) {
  return api.post('/profile-capture/import', {
    configs: configsData,
    overwrite
  })
}
