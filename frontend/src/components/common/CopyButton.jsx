import { useState } from 'react'
import { Tooltip, message } from 'antd'
import { CopyOutlined, CheckOutlined } from '@ant-design/icons'

function CopyButton({ text, size = 'small', style }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      message.success('已复制到剪贴板')
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      message.error('复制失败')
    }
  }

  return (
    <Tooltip title={copied ? '已复制' : '复制'}>
      <span
        onClick={handleCopy}
        style={{
          cursor: 'pointer',
          color: copied ? '#52c41a' : '#1677ff',
          display: 'inline-flex',
          alignItems: 'center',
          fontSize: size === 'small' ? 14 : 16,
          ...style
        }}
      >
        {copied ? <CheckOutlined /> : <CopyOutlined />}
      </span>
    </Tooltip>
  )
}

export default CopyButton
