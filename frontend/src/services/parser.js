import api from './api.js'

// 解析 DLMS Wrapper 数据
export function parseWrapper(hexData, options = {}) {
  return api.post('/parser/parse', {
    hex: hexData,
    ...options
  })
}

// 打包 DLMS Wrapper 数据
export function packWrapper(data, options = {}) {
  return api.post('/parser/pack', {
    data,
    ...options
  })
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
