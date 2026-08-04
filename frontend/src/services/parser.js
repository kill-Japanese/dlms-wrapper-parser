import api from './api.js'

// 解析 DLMS 十六进制帧数据
export function parseHex(hexData, securityConfig = {}) {
  const payload = {
    hex_data: hexData
  }

  // 添加安全配置参数（仅在有值时添加）
  if (securityConfig.guek) payload.guek = securityConfig.guek
  if (securityConfig.gubk) payload.gubk = securityConfig.gubk
  if (securityConfig.ak) payload.ak = securityConfig.ak
  if (securityConfig.kek) payload.kek = securityConfig.kek
  if (securityConfig.systemTitle) payload.system_title = securityConfig.systemTitle
  if (securityConfig.invocationCounter !== undefined && securityConfig.invocationCounter !== null) {
    payload.invocation_counter = securityConfig.invocationCounter
  }
  // 兼容旧字段
  if (securityConfig.blockCipherKey && !securityConfig.guek) {
    payload.encryption_key = securityConfig.blockCipherKey
  }

  return api.post('/parse/hex', payload)
}

// 构建 DLMS 帧
export function buildFrame(apduType, params, options = {}) {
  const payload = {
    apdu_type: apduType,
    params: params,
    src_wport: options.srcWPort || 1,
    dst_wport: options.dstWPort || 16,
    encrypt: options.encrypt || false,
    key_id: options.keyId || 0
  }

  // 添加安全配置参数
  if (options.guek) payload.guek = options.guek
  if (options.gubk) payload.gubk = options.gubk
  if (options.ak) payload.ak = options.ak
  if (options.kek) payload.kek = options.kek
  if (options.systemTitle) payload.system_title = options.systemTitle
  if (options.invocationCounter !== undefined) {
    payload.invocation_counter = options.invocationCounter
  }
  // 兼容旧字段
  if (options.blockCipherKey && !options.guek) {
    payload.encryption_key = options.blockCipherKey
  }

  return api.post('/parse/build', payload)
}

// 解析 DLMS Wrapper 数据（兼容旧接口）
export function parseWrapper(hexData, options = {}) {
  return parseHex(hexData, options)
}

// 打包 DLMS Wrapper 数据（兼容旧接口）
export function packWrapper(data, options = {}) {
  return buildFrame(data.apdu_type || 'GetRequest', data.params || {}, options)
}

// 获取解析历史
export function getParseHistory(params = {}) {
  return api.get('/parser/history', { params })
}

// 获取单条历史记录
export function getHistoryItem(id) {
  return api.get(`/parser/history/${id}`)
}

// 清空解析历史
export function clearParseHistory() {
  return api.delete('/parser/history')
}

// TCP 服务器控制
export function startTcpServer(port = 4059) {
  return api.post('/tcp/start', { port })
}

export function stopTcpServer() {
  return api.post('/tcp/stop')
}

export function getTcpStatus() {
  return api.get('/tcp/status')
}

// 获取已连接设备
export function getConnectedDevices() {
  return api.get('/tcp/devices')
}

// 发送数据到设备
export function sendToDevice(deviceId, hexData) {
  return api.post(`/tcp/devices/${deviceId}/send`, {
    hex: hexData
  })
}

// 日志相关
export function getParseLogs(params = {}) {
  return api.get('/logs/parse', { params })
}

export function getDataLogs(params = {}) {
  return api.get('/logs/data', { params })
}

export function clearLogs(type = 'all') {
  return api.delete('/logs', { params: { type } })
}

export default {
  parseHex,
  buildFrame,
  parseWrapper,
  packWrapper,
  getParseHistory,
  getHistoryItem,
  clearParseHistory,
  startTcpServer,
  stopTcpServer,
  getTcpStatus,
  getConnectedDevices,
  sendToDevice,
  getParseLogs,
  getDataLogs,
  clearLogs
}
