class WebSocketService {
  constructor() {
    this.ws = null
    this.url = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 3000
    this.shouldReconnect = false
    this.onMessageCallback = null
    this.onOpenCallback = null
    this.onCloseCallback = null
    this.onErrorCallback = null
  }

  connect(url) {
    return new Promise((resolve, reject) => {
      try {
        this.url = url
        this.shouldReconnect = true

        this.ws = new WebSocket(url)

        this.ws.onopen = (event) => {
          console.log('[WebSocket] 连接成功')
          this.reconnectAttempts = 0
          if (this.onOpenCallback) {
            this.onOpenCallback(event)
          }
          resolve(event)
        }

        this.ws.onmessage = (event) => {
          let data = event.data
          // 尝试解析 JSON
          try {
            data = JSON.parse(event.data)
          } catch (e) {
            // 不是 JSON，保持原样
          }
          if (this.onMessageCallback) {
            this.onMessageCallback(data)
          }
        }

        this.ws.onclose = (event) => {
          console.log('[WebSocket] 连接关闭', event.code, event.reason)
          if (this.onCloseCallback) {
            this.onCloseCallback(event)
          }
          if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnect()
          }
        }

        this.ws.onerror = (error) => {
          console.error('[WebSocket] 连接错误', error)
          if (this.onErrorCallback) {
            this.onErrorCallback(error)
          }
          reject(error)
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  reconnect() {
    this.reconnectAttempts += 1
    console.log(`[WebSocket] 尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`)
    setTimeout(() => {
      if (this.shouldReconnect && this.url) {
        this.connect(this.url).catch(() => {
          // 重连失败会在 onerror 中继续触发重连
        })
      }
    }, this.reconnectDelay)
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const data = typeof message === 'object' ? JSON.stringify(message) : message
      this.ws.send(data)
      return true
    }
    console.warn('[WebSocket] 连接未建立，无法发送消息')
    return false
  }

  disconnect() {
    this.shouldReconnect = false
    if (this.ws) {
      this.ws.close(1000, 'User disconnected')
      this.ws = null
    }
  }

  onMessage(callback) {
    this.onMessageCallback = callback
  }

  onOpen(callback) {
    this.onOpenCallback = callback
  }

  onClose(callback) {
    this.onCloseCallback = callback
  }

  onError(callback) {
    this.onErrorCallback = callback
  }

  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN
  }

  getReadyState() {
    return this.ws ? this.ws.readyState : WebSocket.CLOSED
  }
}

// 单例模式
const wsService = new WebSocketService()
export default wsService
