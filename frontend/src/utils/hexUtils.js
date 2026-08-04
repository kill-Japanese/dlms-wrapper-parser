/**
 * 验证十六进制字符串
 * @param {string} hex - 十六进制字符串（可包含空格、换行等）
 * @returns {boolean} 是否为有效的十六进制
 */
export function validateHex(hex) {
  if (!hex || typeof hex !== 'string') return false
  const clean = hex.replace(/[\s\n\r\t]/g, '')
  if (clean.length === 0) return false
  return /^[0-9A-Fa-f]*$/.test(clean) && clean.length % 2 === 0
}

/**
 * 去除十六进制字符串中的空格和非hex字符
 * @param {string} hex - 十六进制字符串
 * @returns {string} 清理后的十六进制字符串
 */
export function stripHex(hex) {
  if (!hex || typeof hex !== 'string') return ''
  return hex.replace(/[^0-9A-Fa-f]/g, '').toUpperCase()
}

/**
 * 格式化十六进制字符串（每字节空格分隔，每16字节换行）
 * @param {string} hex - 十六进制字符串
 * @param {number} bytesPerLine - 每行字节数，默认16
 * @param {boolean} addOffset - 是否添加偏移量
 * @returns {string} 格式化后的字符串
 */
export function formatHex(hex, bytesPerLine = 16, addOffset = false) {
  const clean = stripHex(hex)
  if (!clean) return ''

  const lines = []
  for (let i = 0; i < clean.length; i += bytesPerLine * 2) {
    const offset = i / 2
    const lineBytes = clean.slice(i, i + bytesPerLine * 2)

    // 按字节分隔，每8字节加一个额外空格
    let hexStr = ''
    for (let j = 0; j < lineBytes.length; j += 2) {
      if (j > 0) hexStr += ' '
      if (j > 0 && j % 16 === 0) hexStr += ' '
      hexStr += lineBytes.slice(j, j + 2)
    }

    let line = ''
    if (addOffset) {
      line += offset.toString(16).padStart(8, '0') + '  '
    }
    line += hexStr
    lines.push(line)
  }

  return lines.join('\n')
}

/**
 * 十六进制字符串转字节数组
 * @param {string} hex - 十六进制字符串
 * @returns {Uint8Array} 字节数组
 */
export function hexToBytes(hex) {
  const clean = stripHex(hex)
  const bytes = new Uint8Array(clean.length / 2)
  for (let i = 0; i < clean.length; i += 2) {
    bytes[i / 2] = parseInt(clean.slice(i, i + 2), 16)
  }
  return bytes
}

/**
 * 字节数组转十六进制字符串
 * @param {Uint8Array|Array<number>} bytes - 字节数组
 * @returns {string} 十六进制字符串
 */
export function bytesToHex(bytes) {
  if (!bytes || bytes.length === 0) return ''
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0').toUpperCase())
    .join('')
}

/**
 * 字节数组转带空格的十六进制字符串
 * @param {Uint8Array|Array<number>} bytes - 字节数组
 * @param {string} separator - 分隔符
 * @returns {string} 格式化的十六进制字符串
 */
export function bytesToFormattedHex(bytes, separator = ' ') {
  if (!bytes || bytes.length === 0) return ''
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0').toUpperCase())
    .join(separator)
}

/**
 * 十六进制字符串转字符串（ASCII）
 * @param {string} hex - 十六进制字符串
 * @returns {string} ASCII字符串
 */
export function hexToAscii(hex) {
  const clean = stripHex(hex)
  let str = ''
  for (let i = 0; i < clean.length; i += 2) {
    const code = parseInt(clean.slice(i, i + 2), 16)
    str += code >= 32 && code <= 126 ? String.fromCharCode(code) : '.'
  }
  return str
}

/**
 * 字符串转十六进制
 * @param {string} str - 字符串
 * @returns {string} 十六进制字符串
 */
export function asciiToHex(str) {
  if (!str) return ''
  let hex = ''
  for (let i = 0; i < str.length; i++) {
    hex += str.charCodeAt(i).toString(16).padStart(2, '0')
  }
  return hex.toUpperCase()
}

/**
 * 计算十六进制数据的字节长度
 * @param {string} hex - 十六进制字符串
 * @returns {number} 字节数
 */
export function hexByteLength(hex) {
  return Math.floor(stripHex(hex).length / 2)
}

/**
 * 反转字节序（大小端转换）
 * @param {string} hex - 十六进制字符串
 * @returns {string} 反转后的十六进制字符串
 */
export function reverseBytes(hex) {
  const clean = stripHex(hex)
  let reversed = ''
  for (let i = clean.length - 2; i >= 0; i -= 2) {
    reversed += clean.slice(i, i + 2)
  }
  return reversed
}

/**
 * 十六进制转十进制数字
 * @param {string} hex - 十六进制字符串
 * @param {boolean} signed - 是否有符号
 * @returns {number} 十进制数字
 */
export function hexToDecimal(hex, signed = false) {
  const clean = stripHex(hex)
  if (!clean) return 0

  if (signed) {
    // 处理有符号数
    const unsigned = parseInt(clean, 16)
    const bitLength = clean.length * 4
    const signBit = 1 << (bitLength - 1)
    if (unsigned & signBit) {
      return unsigned - (1 << bitLength)
    }
    return unsigned
  }

  return parseInt(clean, 16)
}

/**
 * 十进制数字转十六进制
 * @param {number} dec - 十进制数字
 * @param {number} byteLength - 字节长度（用于填充）
 * @returns {string} 十六进制字符串
 */
export function decimalToHex(dec, byteLength = 0) {
  let hex = Math.abs(dec).toString(16)
  if (dec < 0) {
    // 处理负数（补码）
    const max = Math.pow(2, byteLength * 8)
    hex = (max + dec).toString(16)
  }
  if (byteLength > 0) {
    hex = hex.padStart(byteLength * 2, '0')
  }
  return hex.toUpperCase()
}

/**
 * 比较两个十六进制字符串是否相等（忽略空格和大小写）
 * @param {string} hex1 - 十六进制字符串1
 * @param {string} hex2 - 十六进制字符串2
 * @returns {boolean} 是否相等
 */
export function hexEquals(hex1, hex2) {
  return stripHex(hex1) === stripHex(hex2)
}

export default {
  validateHex,
  stripHex,
  formatHex,
  hexToBytes,
  bytesToHex,
  bytesToFormattedHex,
  hexToAscii,
  asciiToHex,
  hexByteLength,
  reverseBytes,
  hexToDecimal,
  decimalToHex,
  hexEquals
}
