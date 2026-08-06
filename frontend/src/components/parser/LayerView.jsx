import { Card, Row, Col, Empty, Space, Typography, Tag, Alert } from 'antd'
import {
  GiftOutlined,
  LockOutlined,
  CompressOutlined,
  FileTextOutlined,
  WarningOutlined
} from '@ant-design/icons'
import useParserStore from '../../store/parserStore.js'
import WrapperLayer from './WrapperLayer.jsx'
import CipherLayer from './CipherLayer.jsx'
import CompressionLayer from './CompressionLayer.jsx'
import APDULayer from './APDULayer.jsx'

const { Text } = Typography

function LayerView() {
  const { parseResult, error } = useParserStore()

  // 情况1：完全没有解析结果（还没解析过）
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

  // 情况2：有解析结果但解析失败（wrapper 层无效）
  const hasValidWrapper = parseResult.wrapper &&
    typeof parseResult.wrapper === 'object' &&
    Object.keys(parseResult.wrapper).length > 0

  if (!hasValidWrapper) {
    // 获取错误信息
    const errorMessage = error ||
      parseResult.error ||
      parseResult.message ||
      (parseResult.errors && parseResult.errors.length > 0
        ? parseResult.errors.join('; ')
        : '无法解析帧格式')

    return (
      <div style={{ padding: '16px 0' }}>
        <Alert
          message="解析失败"
          description={
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Text type="danger">{errorMessage}</Text>
              {parseResult.errors && parseResult.errors.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <Text strong style={{ color: '#ff4d4f' }}>
                    错误详情：
                  </Text>
                  <ul style={{ margin: '8px 0 0 20px', padding: 0 }}>
                    {parseResult.errors.map((err, index) => (
                      <li key={index} style={{ color: '#ff4d4f', marginBottom: 4 }}>
                        {err}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div style={{ marginTop: 8 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  请检查输入的十六进制数据是否为有效的 DLMS Wrapper 帧格式。
                </Text>
              </div>
            </Space>
          }
          type="error"
          showIcon
          icon={<WarningOutlined />}
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

  // 判断数据是否有效（非空）
  const checkHasData = (data) => {
    if (data === null || data === undefined) {
      return false
    }
    // 数组类型：有元素即为有数据
    if (Array.isArray(data)) {
      return data.length > 0
    }
    // 对象类型：有属性即为有数据
    if (typeof data === 'object') {
      return Object.keys(data).length > 0
    }
    // 其他类型（字符串、数字等）：非空即为有数据
    return data !== ''
  }

  return (
    <div>
      {/* 如果有警告，显示警告信息 */}
      {parseResult.errors && parseResult.errors.length > 0 && (
        <Alert
          message={`解析警告（${parseResult.errors.length} 条）`}
          description={
            <ul style={{ margin: '4px 0 0 20px', padding: 0 }}>
              {parseResult.errors.map((err, index) => (
                <li key={index} style={{ marginBottom: 2 }}>{err}</li>
              ))}
            </ul>
          }
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          closable
        />
      )}

      <Row gutter={[16, 16]}>
        {layers.map((layer) => {
          const LayerComponent = layer.component
          const hasData = checkHasData(layer.data)

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
                  <LayerComponent data={layer.data} pushResolved={parseResult.push_resolved} />
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
    </div>
  )
}

export default LayerView
