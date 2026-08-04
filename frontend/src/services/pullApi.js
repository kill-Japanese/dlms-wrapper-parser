import api from './api.js'

// Pull 预设相关 API

// 获取预设列表
export function getPullPresets() {
  return api.get('/pull/presets')
}

// 获取单个预设详情
export function getPullPreset(presetId) {
  return api.get(`/pull/presets/${presetId}`)
}

// 保存预设列表（全量替换）
export function savePullPresets(presets) {
  return api.put('/pull/presets', presets)
}

// 创建新预设
export function createPullPreset(preset) {
  return api.post('/pull/presets', preset)
}

// 更新预设
export function updatePullPreset(presetId, updates) {
  return api.put(`/pull/presets/${presetId}`, updates)
}

// 删除预设
export function deletePullPreset(presetId) {
  return api.delete(`/pull/presets/${presetId}`)
}

// 构建单个 GetRequest 帧
export function buildGetRequest(params) {
  return api.post('/pull/build-request', params)
}

// 执行预设 Pull 操作
export function executePullPreset(presetId, options = {}) {
  return api.post('/pull/execute', {
    preset_id: presetId,
    use_with_list: options.useWithList ?? true,
    with_wrapper: options.withWrapper ?? true,
    src_wport: options.srcWport ?? 1,
    dst_wport: options.dstWport ?? 16
  })
}

// 直接执行操作列表（不通过预设）
export function executePullOperations(operations, options = {}) {
  return api.post('/pull/execute-operations', {
    operations,
    use_with_list: options.useWithList ?? true,
    with_wrapper: options.withWrapper ?? true,
    src_wport: options.srcWport ?? 1,
    dst_wport: options.dstWport ?? 16
  })
}

// 自动处理配置相关 API

// 获取自动处理配置
export function getAutoConfig(deviceId = null) {
  const params = deviceId ? { device_id: deviceId } : {}
  return api.get('/auto/config', { params })
}

// 更新自动处理配置
export function updateAutoConfig(config, deviceId = null) {
  const params = deviceId ? { device_id: deviceId } : {}
  return api.put('/auto/config', config, { params })
}

// 获取自动处理状态
export function getAutoStatus() {
  return api.get('/auto/status')
}

// 获取设备配置列表
export function listDeviceConfigs() {
  return api.get('/auto/devices')
}

// 删除设备配置
export function deleteDeviceConfig(deviceId) {
  return api.delete(`/auto/config/${deviceId}`)
}

// 手动触发自动处理
export function triggerAutoFlow(connectionId, deviceId = null) {
  return api.post('/auto/trigger', {
    connection_id: connectionId,
    device_id: deviceId
  })
}

export default {
  // Pull 预设
  getPullPresets,
  getPullPreset,
  savePullPresets,
  createPullPreset,
  updatePullPreset,
  deletePullPreset,
  buildGetRequest,
  executePullPreset,
  executePullOperations,
  // 自动处理
  getAutoConfig,
  updateAutoConfig,
  getAutoStatus,
  listDeviceConfigs,
  deleteDeviceConfig,
  triggerAutoFlow
}
