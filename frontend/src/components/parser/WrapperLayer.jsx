import { Descriptions, Tag, Typography } from 'antd'
import HexViewer from '../common/HexViewer.jsx'

const { Text } = Typography

function WrapperLayer({ data }) {
  if (!data) return null

  const { version, srcWPort, dstWPort, length, header, type } = data

  return (
    <div>
      <Descriptions size="small" column={2} bordered>
        <Descriptions.Item label="版本">
          <Tag color="blue">v{version}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="帧类型">
          <Tag>{type || 'DATA'}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="源 WPort">
          <Text code>{srcWPort}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="目的 WPort">
          <Text code>{dstWPort}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="数据长度" span={2}>
          <Text strong>{length}</Text> bytes
        </Descriptions.Item>
      </Descriptions>

      {header && (
        <div style={{ marginTop: 12 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>帧头:</Text>
          <HexViewer hex={header} style={{ marginTop: 4 }} />
        </div>
      )}
    </div>
  )
}

export default WrapperLayer
