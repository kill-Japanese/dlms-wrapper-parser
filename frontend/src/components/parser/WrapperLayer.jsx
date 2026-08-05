import { Descriptions, Tag, Typography } from 'antd'
import HexViewer from '../common/HexViewer.jsx'

const { Text } = Typography

function WrapperLayer({ data }) {
  if (!data) return null

  // 后端返回 snake_case 字段名
  const { version, src_wport, dst_wport, data_length, payload_hex, frame_type } = data

  return (
    <div>
      <Descriptions size="small" column={2} bordered>
        <Descriptions.Item label="版本">
          <Tag color="blue">v{version}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="帧类型">
          <Tag>{frame_type || 'DATA'}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="源 WPort">
          <Text code>{src_wport}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="目的 WPort">
          <Text code>{dst_wport}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="数据长度" span={2}>
          <Text strong>{data_length}</Text> bytes
        </Descriptions.Item>
      </Descriptions>

      {payload_hex && (
        <div style={{ marginTop: 12 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>载荷数据:</Text>
          <HexViewer hex={payload_hex} style={{ marginTop: 4, maxHeight: 80, overflow: 'auto' }} />
        </div>
      )}
    </div>
  )
}

export default WrapperLayer
