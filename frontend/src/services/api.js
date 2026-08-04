import axios from 'axios'

// 从 localStorage 获取后端地址（如果用户手动配置过），否则使用环境变量，最后用默认值
const getBaseURL = () => {
  const savedUrl = localStorage.getItem('api_base_url')
  if (savedUrl) {
    return savedUrl
  }
  return import.meta.env.VITE_API_BASE_URL || '/api'
}

const api = axios.create({
  baseURL: getBaseURL(),
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 动态更新 baseURL 的方法
export const updateBaseURL = (url) => {
  api.defaults.baseURL = url
  if (url) {
    localStorage.setItem('api_base_url', url)
  } else {
    localStorage.removeItem('api_base_url')
  }
}

// 获取当前 baseURL
export const getCurrentBaseURL = () => {
  return api.defaults.baseURL
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

// 健康检查接口
export function checkHealth() {
  return api.get('/health')
}

export default api
