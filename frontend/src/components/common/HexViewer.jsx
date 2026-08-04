import { useState } from 'react'
import { Space, Button, message, Typography, Tooltip } from 'antd'
import { CopyOutlined, FormatPainterOutlined } from '@ant-design/icons'
import CopyButton from './CopyButton.jsx'
import { formatHex } from '../../utils/hexUtils.js'

const { Text } = Typography

function HexViewer({ hex, showCopy = true, showFormat = true, bytesPerRow = 16, style }) {
  const [formatted, setFormatted] = useState(true)

  const handleFormat = () => {
    setFormatted(!formatted)
    message.success(formatted ? '已切换为紧凑格式' : '已切换为格式化格式')
  }

  // 格式化显示（带地址和ASCII）
  const renderFormattedHex = () => {
    const cleanHex = hex.replace(/[^0-9A-Fa-f]/g, '')
    const rows = []

    for (let i = 0; i < cleanHex.length; i += bytesPerRow * 2) {
      const offset = i / 2
      const hexPart = cleanHex.slice(i, i + bytesPerRow * 2)
      const paddedHex = hexPart.padEnd(bytesPerRow * 2, ' ')

      // 按字节分隔
      let hexStr = ''
      for (let j = 0; j < bytesPerRow; j++) {
        hexStr += paddedHex.slice(j * 2, j * 2 + 2) + ' '
        if (j === 7) hexStr += ' '
      }

      // ASCII 表示
      let asciiStr = ''
      for (let j = 0; j < hexPart.length; j += 2) {
        const byte = parseInt(hexPart.slice(j, j + 2), 16)
        asciiStr += byte >= 32 && byte <= 126 ? String.fromCharCode(byte) : '.'
      }

      rows.push(
        <div key={offset} style={{ display: 'flex', lineHeight: '1.6' }}>
          <span style={{ color: '#8c8c8c', minWidth: 80, fontFamily: 'monospace' }}>
            {offset.toString(16).padStart(8, '0')}
          </span>
          <span style={{ flex: 1, fontFamily: 'monospace', color: '#262626' }}>
            {hexStr}
          </span>
          <span style={{ color: '#595959', fontFamily: 'monospace', marginLeft: 16 }}>
            {asciiStr}
          </span>
        </div>
      )
    }

    return rows
  }

  if (!hex) {
    return (
      <div style={{ color: '#bfbfbf', fontStyle: 'italic', ...style }}>
        无数据
      </div>
    )
  }

  return (
    <div style={{ ...style }}>
      <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {Math.floor(hex.replace(/[^0-9A-Fa-f]/g, '').length / 2)} bytes
        </Text>
        <Space size="small">
          {showFormat && (
            <Tooltip title={formatted ? '紧凑格式' : '格式化显示'}>
              <Button size="small" icon={<FormatPainterOutlined />} onClick={handleFormat} />
            </Tooltip>
          )}
          {showCopy && <CopyButton text={hex} />}
        </Space>
      </div>
      <div
        style={{
          background: '#fafafa',
          padding: 12,
          borderRadius: 4,
          border: '1px solid #f0f0f0',
          overflowX: 'auto',
          fontSize: 12
        }}
      >
        {formatted ? (
          renderFormattedHex()
        ) : (
          <div style={{ fontFamily: 'monospace', wordBreak: 'break-all', lineHeight: 1.6 }}>
            {hex}
          </div>
        )}
      </div>
    </div>
  )
}

export default HexViewer
