/**
 * 模拟 WebSocket 消息
 *
 * 模拟WebSocket连接和消息推送，用于前端开发测试。
 * 无需真实后端即可测试实时数据流功能。
 */

import { mockFrames, mockParseResult, mockEncryptedParseResult, mockSecurityConfig } from './mockFrames.js'

// 模拟连接状态
let mockConnected = false
let mockMessageHandlers = []
let mockErrorHandlers = []
let mockCloseHandlers = []
let mockIntervalId = null
let mockFrameIndex = 0

// 模拟设备列表
export const mockDevices = [
  {
    id: 'dev-001',
    address: '192.168.1.100',
    port: 4059,
    connectedAt: new Date(Date.now() - 3600000).toISOString(),
    framesReceived: 156,
    status: 'connected',
    name: '电表A-1001',
    serial: '1234567890',
  },
  {
    id: 'dev-002',
    address: '192.168.1.101',
    port: 4059,
    connectedAt: new Date(Date.now() - 7200000).toISOString(),
    framesReceived: 89,
    status: 'connected',
    name: '电表B-1002',
    serial: '0987654321',
  },
  {
    id: 'dev-003',
    address: '192.168.1.102',
    port: 4059,
    connectedAt: null,
    framesReceived: 0,
    status: 'disconnected',
    name: '电表C-1003',
    serial: '1122334455',
  },
]

// 模拟WebSocket消息类型
export const MOCK_MESSAGE_TYPES = {
  FRAME_RECEIVED: 'frame_received',
  DEVICE_CONNECTED: 'device_connected',
  DEVICE_DISCONNECTED: 'device_disconnected',
  PARSE_RESULT: 'parse_result',
  ERROR: 'error',
  PONG: 'pong',
}

// 生成模拟帧消息
function generateMockFrameMessage() {
  const frames = [
    { ...mockFrames[0], deviceId: 'dev-001' },
    { ...mockFrames[1], deviceId: 'dev-001' },
    { ...mockFrames[2], deviceId: 'dev-002' },
    { ...mockFrames[3], deviceId: 'dev-002' },
    { ...mockFrames[4], deviceId: 'dev-001' },
  ]

  const frame = frames[mockFrameIndex % frames.length]
  mockFrameIndex++

  return {
    type: MOCK_MESSAGE_TYPES.FRAME_RECEIVED,
    timestamp: new Date().toISOString(),
    deviceId: frame.deviceId,
    frame: {
      hex: frame.hex,
      length: frame.length,
    },
    parseResult: frame.security === 'plain'
      ? { ...mockParseResult, frameId: `mock-${Date.now()}`, rawHex: frame.hex }
      : frame.security === 'encrypted'
        ? { ...mockEncryptedParseResult, frameId: `mock-${Date.now()}`, rawHex: frame.hex }
        : null,
  }
}

// 生成模拟设备连接消息
function generateDeviceConnectedMessage() {
  return {
    type: MOCK_MESSAGE_TYPES.DEVICE_CONNECTED,
    timestamp: new Date().toISOString(),
    device: {
      id: `dev-${Math.random().toString(36).substr(2, 6)}`,
      address: `192.168.1.${100 + Math.floor(Math.random() * 50)}`,
      port: 4059,
      connectedAt: new Date().toISOString(),
      status: 'connected',
    },
  }
}

// 生成模拟设备断开消息
function generateDeviceDisconnectedMessage() {
  return {
    type: MOCK_MESSAGE_TYPES.DEVICE_DISCONNECTED,
    timestamp: new Date().toISOString(),
    deviceId: 'dev-003',
    reason: 'connection_closed',
  }
}

/**
 * Mock WebSocket 类
 *
 * 模拟WebSocket API，用于前端开发测试。
 * 用法与原生WebSocket类似：
 * const ws = new MockWebSocket('ws://localhost:8000/ws/stream')
 * ws.onmessage = (event) => { ... }
 */
export class MockWebSocket {
  constructor(url) {
    this.url = url
    this.readyState = 0 // CONNECTING
    this.onopen = null
    this.onmessage = null
    this.onclose = null
    this.onerror = null

    // 模拟连接延迟
    setTimeout(() => {
      this.readyState = 1 // OPEN
      mockConnected = true
      if (this.onopen) {
        this.onopen({ type: 'open', target: this })
      }
    }, 300)
  }

  send(data) {
    if (this.readyState !== 1) {
      throw new Error('WebSocket is not open')
    }

    // 处理ping
    if (data === 'ping') {
      setTimeout(() => {
        if (this.onmessage) {
          this.onmessage({
            type: 'message',
            data: JSON.stringify({ type: MOCK_MESSAGE_TYPES.PONG }),
            target: this,
          })
        }
      }, 100)
    }
  }

  close() {
    this.readyState = 3 // CLOSED
    mockConnected = false
    if (this.onclose) {
      this.onclose({ type: 'close', code: 1000, reason: 'Normal closure', target: this })
    }
  }
}

/**
 * 启动模拟数据流
 *
 * @param {Object} options - 配置选项
 * @param {number} options.interval - 消息间隔（毫秒），默认3000
 * @param {Function} options.onMessage - 消息回调
 * @param {boolean} options.autoParse - 是否自动包含解析结果
 * @returns {Function} 停止函数
 */
export function startMockStream(options = {}) {
  const {
    interval = 3000,
    onMessage = null,
    autoParse = true,
  } = options

  if (mockIntervalId) {
    stopMockStream()
  }

  mockConnected = true

  // 立即发送一条消息
  if (onMessage) {
    onMessage(generateMockFrameMessage())
  }

  // 定时发送消息
  mockIntervalId = setInterval(() => {
    const message = generateMockFrameMessage()
    if (onMessage) {
      onMessage(message)
    }
    // 通知所有handler
    mockMessageHandlers.forEach(handler => {
      try { handler(message) } catch (e) { /* ignore */ }
    })
  }, interval)

  return stopMockStream
}

/**
 * 停止模拟数据流
 */
export function stopMockStream() {
  if (mockIntervalId) {
    clearInterval(mockIntervalId)
    mockIntervalId = null
  }
  mockConnected = false
}

/**
 * 获取模拟TCP服务器状态
 */
export function getMockTcpStatus() {
  return {
    running: true,
    host: '0.0.0.0',
    port: 4059,
    connectedClients: 2,
    totalFramesReceived: 245,
    startTime: new Date(Date.now() - 86400000).toISOString(),
  }
}

/**
 * 获取模拟日志
 */
export function getMockLogs(count = 20) {
  const levels = ['info', 'warn', 'error', 'debug']
  const steps = ['wrapper', 'ciphering', 'compression', 'apdu', 'input', 'tcp']
  const messages = [
    '帧解析成功',
    'Wrapper层解析完成',
    'AES-GCM解密成功',
    'V.44解压完成',
    'APDU类型: DataNotification',
    '新设备连接',
    '设备断开连接',
    '收到数据帧',
  ]

  const logs = []
  for (let i = 0; i < count; i++) {
    logs.push({
      id: `log-${i}`,
      timestamp: new Date(Date.now() - i * 5000).toISOString(),
      level: levels[Math.floor(Math.random() * levels.length)],
      step: steps[Math.floor(Math.random() * steps.length)],
      message: messages[Math.floor(Math.random() * messages.length)],
    })
  }
  return logs
}

/**
 * 添加消息处理器
 */
export function addMessageHandler(handler) {
  mockMessageHandlers.push(handler)
}

/**
 * 移除消息处理器
 */
export function removeMessageHandler(handler) {
  const index = mockMessageHandlers.indexOf(handler)
  if (index > -1) {
    mockMessageHandlers.splice(index, 1)
  }
}

/**
 * 获取当前连接状态
 */
export function isMockConnected() {
  return mockConnected
}

export default {
  MockWebSocket,
  startMockStream,
  stopMockStream,
  getMockTcpStatus,
  getMockLogs,
  mockDevices,
  MOCK_MESSAGE_TYPES,
  isMockConnected,
  addMessageHandler,
  removeMessageHandler,
  mockSecurityConfig,
}
