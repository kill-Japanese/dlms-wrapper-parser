import api from './api.js'

// TCP/UDP 服务器相关 API

// 获取服务器状态
export function getTcpStatus() {
  return api.get('/tcp/status')
}

// 获取服务器配置
export function getTcpConfig() {
  return api.get('/tcp/config')
}

// 更新服务器配置
export function updateTcpConfig(config) {
  return api.put('/tcp/config', config)
}

// 启动服务器
export function startTcpServer() {
  return api.post('/tcp/start')
}

// 停止服务器
export function stopTcpServer() {
  return api.post('/tcp/stop')
}

// 重启服务器
export function restartTcpServer() {
  return api.post('/tcp/restart')
}

// 获取设备列表
export function getTcpClients() {
  return api.get('/tcp/clients')
}

// 获取指定连接信息
export function getTcpClient(connectionId) {
  return api.get(`/tcp/clients/${connectionId}`)
}

// 根据 System Title 获取设备信息
export function getDeviceBySystemTitle(systemTitle) {
  return api.get(`/tcp/device/${systemTitle}`)
}

// 重命名设备
export function renameDevice(systemTitle, deviceName) {
  return api.put(`/tcp/device/${systemTitle}/name`, { device_name: deviceName })
}

// 发送数据
export function sendTcpData(params) {
  return api.post('/tcp/send', params)
}

// 按 System Title 发送数据
export function sendToDevice(systemTitle, hexData) {
  return api.post('/tcp/send-to-device', {
    system_title: systemTitle,
    hex_data: hexData
  })
}

export default {
  getTcpStatus,
  getTcpConfig,
  updateTcpConfig,
  startTcpServer,
  stopTcpServer,
  restartTcpServer,
  getTcpClients,
  getTcpClient,
  getDeviceBySystemTitle,
  renameDevice,
  sendTcpData,
  sendToDevice
}
