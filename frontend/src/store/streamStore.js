import { create } from 'zustand'

const useStreamStore = create((set, get) => ({
  // WebSocket连接状态
  connected: false,

  // TCP服务器状态: 'stopped' | 'running' | 'starting' | 'stopping'
  tcpStatus: 'stopped',

  // TCP端口
  tcpPort: 4059,

  // 已连接设备列表
  connectedDevices: [],

  // 帧列表
  frames: [],

  // 选中的帧ID
  selectedFrameId: null,

  // 发送面板数据
  sendPanel: {
    targetDevice: null,
    hexData: '',
    autoIncrementCounter: true
  },

  // Actions
  setConnected: (connected) => set({ connected }),

  setTcpStatus: (status) => set({ tcpStatus: status }),

  setTcpPort: (port) => set({ tcpPort: port }),

  addDevice: (device) => set((state) => ({
    connectedDevices: [...state.connectedDevices, device]
  })),

  removeDevice: (deviceId) => set((state) => ({
    connectedDevices: state.connectedDevices.filter((d) => d.id !== deviceId)
  })),

  updateDevice: (deviceId, updates) => set((state) => ({
    connectedDevices: state.connectedDevices.map((d) =>
      d.id === deviceId ? { ...d, ...updates } : d
    )
  })),

  setDevices: (devices) => set({ connectedDevices: devices }),

  addFrame: (frame) => set((state) => ({
    frames: [
      ...state.frames,
      {
        id: frame.id || Date.now(),
        timestamp: frame.timestamp || new Date().toISOString(),
        ...frame
      }
    ]
  })),

  setFrames: (frames) => set({ frames }),

  selectFrame: (frameId) => set({ selectedFrameId: frameId }),

  getSelectedFrame: () => {
    const { frames, selectedFrameId } = get()
    return frames.find((f) => f.id === selectedFrameId) || null
  },

  clearFrames: () => set({ frames: [], selectedFrameId: null }),

  setSendPanel: (updates) => set((state) => ({
    sendPanel: { ...state.sendPanel, ...updates }
  })),

  reset: () => set({
    connected: false,
    tcpStatus: 'stopped',
    connectedDevices: [],
    frames: [],
    selectedFrameId: null
  })
}))

export default useStreamStore
