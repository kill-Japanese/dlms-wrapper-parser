import { Space, Tag, Tooltip } from 'antd'
import { InfoCircleOutlined } from '@ant-design/icons'
import CopyButton from './CopyButton.jsx'

function OBISDisplay({ obis, name, showCopy = true, size = 'default' }) {
  if (!obis) return null

  // 格式化OBIS码显示
  const formatOBIS = (code) => {
    // 移除所有非数字字符
    const cleaned = code.replace(/[^0-9]/g, '')
    if (cleaned.length >= 12) {
      return `${cleaned.slice(0, 2)}.${cleaned.slice(2, 4)}.${cleaned.slice(4, 6)}.${cleaned.slice(6, 8)}.${cleaned.slice(8, 10)}.${cleaned.slice(10, 12)}`
    }
    return code
  }

  const formattedOBIS = formatOBIS(obis)

  return (
    <Space size={size === 'small' ? 4 : 8}>
      <Tag color="blue" style={{ fontFamily: 'monospace', fontSize: size === 'small' ? 11 : 12 }}>
        {formattedOBIS}
      </Tag>
      {name && <span style={{ fontSize: size === 'small' ? 12 : 14 }}>{name}</span>}
      {showCopy && <CopyButton text={formattedOBIS} size={size} />}
      <Tooltip title={`OBIS 码: ${formattedOBIS}\n原始值: ${obis}`}>
        <InfoCircleOutlined style={{ color: '#8c8c8c', fontSize: size === 'small' ? 12 : 14 }} />
      </Tooltip>
    </Space>
  )
}

export default OBISDisplay
