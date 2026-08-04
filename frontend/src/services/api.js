import axios from 'axios'

// 规范化 baseURL，确保完整域名后面加上 /api 路径
// 例如：https://example.com -> https://example.com/api
// 但 /api 本身保持不变
const normalizeBaseURL = (url) => {
  if (!url) return '/api'
  // 如果是相对路径（以 / 开头），保持不变
  if (url.startsWith('/')) return url
  // 如果是完整 URL（http:// 或 https://），确保末尾有 /api
  if (url.startsWith('http://') || url.startsWith('https://')) {
    // 去掉末尾的斜杠
    const trimmed = url.replace(/\/+$/, '')
    // 如果已经以 /api 结尾，直接返回
    if (trimmed.endsWith('/api')) return trimmed
    // 否则加上 /api
    return trimmed + '/api'
  }
  return url
}

// 从 localStorage 获取后端地址（如果用户手动配置过），否则使用环境变量，最后用默认值
const getBaseURL = () => {
  const savedUrl = localStorage.getItem('api_base_url')
  if (savedUrl) {
    return normalizeBaseURL(savedUrl)
  }
  const envUrl = import.meta.env.VITE_API_BASE_URL
  if (envUrl) {
    return normalizeBaseURL(envUrl)
  }
  return '/api'
}

const api = axios.create({
  baseURL: getBaseURL(),
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 动态更新 baseURL 的方法（用户输入的是后端根地址，如 https://example.com）
export const updateBaseURL = (url) => {
  const normalized = normalizeBaseURL(url)
  api.defaults.baseURL = normalized
  if (url) {
    // 保存原始输入的地址，方便用户下次编辑
    localStorage.setItem('api_base_url', url)
  } else {
    localStorage.removeItem('api_base_url')
  }
}

// 获取用户配置的原始后端地址（不含 /api，用于显示）
export const getBackendURL = () => {
  const savedUrl = localStorage.getItem('api_base_url')
  if (savedUrl) return savedUrl
  const envUrl = import.meta.env.VITE_API_BASE_URL
  if (envUrl) return envUrl
  return '/api'
}

// 获取当前 baseURL（含 /api）
export const getCurrentBaseURL = () => {
  return api.defaults.baseURL
}

// 构建健康检查 URL（健康检查在根路径，不在 /api 下）
const getHealthCheckURL = () => {
  const base = api.defaults.baseURL
  // 如果 baseURL 以 /api 结尾，替换成 /health
  if (base.endsWith('/api')) {
    return base.slice(0, -4) + '/health'
  }
  // 如果是相对路径 /api，替换成 /health
  if (base === '/api') {
    return '/health'
  }
  // 否则直接在末尾加 /health
  return base.replace(/\/+$/, '') + '/health'
}

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加 token 等公共请求头
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    // 统一处理响应数据
    return response.data
  },
  (error) => {
    // 统一处理错误
    const status = error.response?.status
    const data = error.response?.data
    const message = data?.message || data?.error || error.message

    // 构造更友好的错误对象
    const enhancedError = {
      status,
      message,
      error: error,
      data,
      // 便捷方法：获取用户友好的错误信息
      getUserMessage: () => {
        if (status === 404) {
          return '接口不存在，请检查后端版本是否支持该功能'
        } else if (status === 500) {
          return `服务器错误：${message || '未知错误'}`
        } else if (status === 401) {
          return '未授权，请重新登录'
        } else if (status === 403) {
          return '没有权限执行此操作'
        } else if (status === 400) {
          return `请求参数错误：${message || '请检查输入'}`
        } else if (!status) {
          return '无法连接到后端服务，请检查后端是否启动'
        }
        return message || '未知错误'
      }
    }

    if (status === 401) {
      // 未授权，清除token并跳转登录
      localStorage.removeItem('token')
    }

    return Promise.reject(enhancedError)
  }
)

// 健康检查接口（使用完整 URL，绕过 baseURL）
export function checkHealth() {
  const healthURL = getHealthCheckURL()
  return axios.get(healthURL, { timeout: 10000 }).then((response) => response.data)
}

export default api
