import { create } from 'zustand'

const STORAGE_KEY = 'dlms_tcp_config'
const DEVICE_NAMES_KEY = 'dlms_device_names'

// 从 localStorage 加载 TCP 配置
const loadConfigFromStorage = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      return JSON.parse(saved)
    }
  } catch (e) {
    console.error('加载TCP配置失败:', e)
  }
  return {
    port: 4059,
    protocol: 'tcp',
    enabled: true,
    auto_start: false
  }
}

// 保存 TCP 配置到 localStorage
const saveConfigToStorage = (config) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
  } catch (e) {
    console.error('保存TCP配置失败:', e)
  }
}

// 从 localStorage 加载设备名称映射
const loadDeviceNamesFromStorage = () => {
  try {
    const saved = localStorage.getItem(DEVICE_NAMES_KEY)
    if (saved) {
      return JSON.parse(saved)
    }
  } catch (e) {
    console.error('加载设备名称失败:', e)
  }
  return {}
}

// 保存设备名称到 localStorage
const saveDeviceNamesToStorage = (names) => {
  try {
    localStorage.setItem(DEVICE_NAMES_KEY, JSON.stringify(names))
  } catch (e) {
    console.error('保存设备名称失败:', e)
  }
}

const useStreamStore = create((set, get) => ({
  // WebSocket连接状态
  connected: false,

  // TCP服务器状态: 'stopped' | 'running' | 'starting' | 'stopping'
  tcpStatus: 'stopped',

  // TCP/UDP 配置
  tcpConfig: loadConfigFromStorage(),

  // 已连接设备列表
  // 每个设备包含: system_title, device_name, ip, port, connected, last_seen, connection_id
  connectedDevices: [],

  // 设备名称持久化映射 (system_title -> device_name)
  deviceNames: loadDeviceNamesFromStorage(),

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

  // 更新 TCP 配置
  setTcpConfig: (config) => set((state) => {
    const newConfig = { ...state.tcpConfig, ...config }
    saveConfigToStorage(newConfig)
    return { tcpConfig: newConfig }
  }),

  // 设置设备列表
  setDevices: (devices) => set({ connectedDevices: devices }),

  // 添加设备
  addDevice: (device) => set((state) => {
    // 检查是否已存在（按 system_title 或 connection_id）
    const exists = state.connectedDevices.some(
      (d) => d.connection_id === device.connection_id ||
        (device.system_title && d.system_title === device.system_title)
    )
    if (exists) {
      // 更新已存在的设备
      return {
        connectedDevices: state.connectedDevices.map((d) =>
          d.connection_id === device.connection_id ||
          (device.system_title && d.system_title === device.system_title)
            ? { ...d, ...device, connected: true }
            : d
        )
      }
    }
    return {
      connectedDevices: [...state.connectedDevices, { ...device, connected: true }]
    }
  }),

  // 更新设备
  updateDevice: (deviceId, updates) => set((state) => ({
    connectedDevices: state.connectedDevices.map((d) =>
      d.connection_id === deviceId || d.system_title === deviceId
        ? { ...d, ...updates }
        : d
    )
  })),

  // 移除设备
  removeDevice: (deviceId) => set((state) => ({
    connectedDevices: state.connectedDevices.filter((d) =>
      d.connection_id !== deviceId && d.system_title !== deviceId
    )
  })),

  // 重命名设备
  renameDevice: (systemTitle, newName) => set((state) => {
    const newDeviceNames = { ...state.deviceNames, [systemTitle]: newName }
    saveDeviceNamesToStorage(newDeviceNames)
    return {
      deviceNames: newDeviceNames,
      connectedDevices: state.connectedDevices.map((d) =>
        d.system_title === systemTitle
          ? { ...d, device_name: newName }
          : d
      )
    }
  }),

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
