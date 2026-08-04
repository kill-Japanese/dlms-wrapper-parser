import dayjs from 'dayjs'

/**
 * 格式化字节大小
 * @param {number} bytes - 字节数
 * @param {number} decimals - 小数位数
 * @returns {string} 格式化后的字符串
 */
export function formatBytes(bytes, decimals = 2) {
  if (bytes === 0) return '0 B'
  if (!bytes) return 'N/A'

  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']

  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
}

/**
 * 格式化时间
 * @param {string|Date|number} date - 日期
 * @param {string} format - 格式化字符串
 * @returns {string} 格式化后的时间字符串
 */
export function formatTime(date, format = 'YYYY-MM-DD HH:mm:ss') {
  if (!date) return 'N/A'
  return dayjs(date).format(format)
}

/**
 * 格式化相对时间
 * @param {string|Date|number} date - 日期
 * @returns {string} 相对时间字符串
 */
export function formatRelativeTime(date) {
  if (!date) return 'N/A'
  return dayjs(date).fromNow()
}

/**
 * 格式化十六进制数据（每字节空格分隔，每16字节换行）
 * @param {string} hex - 十六进制字符串
 * @param {number} bytesPerLine - 每行字节数
 * @returns {string} 格式化后的字符串
 */
export function formatHexDisplay(hex, bytesPerLine = 16) {
  const clean = hex.replace(/[^0-9A-Fa-f]/g, '')
  let result = ''

  for (let i = 0; i < clean.length; i += 2) {
    if (i > 0) {
      result += ' '
      if ((i / 2) % bytesPerLine === 0) {
        result += '\n'
      } else if ((i / 2) % 8 === 0) {
        result += ' '
      }
    }
    result += clean.slice(i, i + 2).toUpperCase()
  }

  return result
}

/**
 * 格式化数字（千分位）
 * @param {number} num - 数字
 * @param {number} decimals - 小数位数
 * @returns {string} 格式化后的数字字符串
 */
export function formatNumber(num, decimals = 0) {
  if (num === undefined || num === null || isNaN(num)) return 'N/A'
  return Number(num).toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  })
}

/**
 * 格式化百分比
 * @param {number} value - 小数值 (0-1)
 * @param {number} decimals - 小数位数
 * @returns {string} 格式化后的百分比字符串
 */
export function formatPercent(value, decimals = 1) {
  if (value === undefined || value === null || isNaN(value)) return 'N/A'
  return (value * 100).toFixed(decimals) + '%'
}

/**
 * 截断文本
 * @param {string} text - 文本
 * @param {number} maxLength - 最大长度
 * @returns {string} 截断后的文本
 */
export function truncateText(text, maxLength = 50) {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + '...'
}

/**
 * 格式化持续时间
 * @param {number} ms - 毫秒数
 * @returns {string} 格式化后的持续时间
 */
export function formatDuration(ms) {
  if (!ms || ms < 0) return '0ms'

  if (ms < 1000) {
    return `${ms}ms`
  }

  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)

  if (hours > 0) {
    return `${hours}h ${minutes % 60}m ${seconds % 60}s`
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`
  }
  return `${seconds}s`
}

export default {
  formatBytes,
  formatTime,
  formatRelativeTime,
  formatHexDisplay,
  formatNumber,
  formatPercent,
  truncateText,
  formatDuration
}
