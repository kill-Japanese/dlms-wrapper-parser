import { Card, Row, Col, Empty, Space, Typography, Tag } from 'antd'
import {
  GiftOutlined,
  LockOutlined,
  CompressOutlined,
  FileTextOutlined
} from '@ant-design/icons'
import useParserStore from '../../store/parserStore.js'
import WrapperLayer from './WrapperLayer.jsx'
import CipherLayer from './CipherLayer.jsx'
import CompressionLayer from './CompressionLayer.jsx'
import APDULayer from './APDULayer.jsx'

const { Text } = Typography

function LayerView() {
  const { parseResult } = useParserStore()

  if (!parseResult) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          minHeight: 400
        }}
      >
        <Empty
          image={<FileTextOutlined style={{ fontSize: 64, color: '#d9d9d9' }} />}
          description={
            <Space direction="vertical" align="center">
              <Text type="secondary">暂无解析结果</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                请在左侧输入十六进制数据并点击解析
              </Text>
            </Space>
          }
        />
      </div>
    )
  }

  const layers = [
    {
      key: 'wrapper',
      title: 'Wrapper 层',
      icon: <GiftOutlined />,
      color: 'blue',
      data: parseResult.wrapper,
      component: WrapperLayer
    },
    {
      key: 'ciphering',
      title: '加密层',
      icon: <LockOutlined />,
      color: 'orange',
      data: parseResult.ciphering,
      component: CipherLayer
    },
    {
      key: 'compression',
      title: '压缩层',
      icon: <CompressOutlined />,
      color: 'green',
      data: parseResult.compression,
      component: CompressionLayer
    },
    {
      key: 'apdu',
      title: 'APDU 层',
      icon: <FileTextOutlined />,
      color: 'purple',
      data: parseResult.apdu,
      component: APDULayer
    }
  ]

  return (
    <Row gutter={[16, 16]}>
      {layers.map((layer) => {
        const LayerComponent = layer.component
        const hasData = layer.data && (typeof layer.data === 'object' && Object.keys(layer.data).length > 0)

        return (
          <Col span={24} key={layer.key}>
            <Card
              size="small"
              title={
                <Space>
                  {layer.icon}
                  <Text strong>{layer.title}</Text>
                  {hasData ? (
                    <Tag color="green">已解析</Tag>
                  ) : (
                    <Tag color="default">未启用</Tag>
                  )}
                </Space>
              }
              style={{ borderLeft: `3px solid var(--ant-${layer.color}-5)` }}
              bodyStyle={{ padding: 12 }}
            >
              {hasData ? (
                <LayerComponent data={layer.data} />
              ) : (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  该层未启用或无数据
                </Text>
              )}
            </Card>
          </Col>
        )
      })}
    </Row>
  )
}

export default LayerView
