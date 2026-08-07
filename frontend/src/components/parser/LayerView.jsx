import { Card, Row, Col, Empty, Space, Typography, Tag, Alert, Table, Descriptions, Statistic } from 'antd'
import {
  GiftOutlined,
  LockOutlined,
  CompressOutlined,
  FileTextOutlined,
  WarningOutlined,
  DatabaseOutlined,
  ExportOutlined,
  CheckCircleOutlined
} from '@ant-design/icons'
import useParserStore from '../../store/parserStore.js'
import WrapperLayer from './WrapperLayer.jsx'
import CipherLayer from './CipherLayer.jsx'
import CompressionLayer from './CompressionLayer.jsx'
import APDULayer from './APDULayer.jsx'

const { Text } = Typography

// 判断数据是否有效（非空）
function checkHasData(data) {
  if (data === null || data === undefined) {
    return false
  }
  if (Array.isArray(data)) {
    return data.length > 0
  }
  if (typeof data === 'object') {
    return Object.keys(data).length > 0
  }
  return data !== ''
}

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

  const hasValidWrapper = parseResult.wrapper &&
    typeof parseResult.wrapper === 'object' &&
    Object.keys(parseResult.wrapper).length > 0

  const hasValidApdu = parseResult.apdu &&
    typeof parseResult.apdu === 'object' &&
    Object.keys(parseResult.apdu).length > 0

  const hasValidCiphering = parseResult.ciphering &&
    typeof parseResult.ciphering === 'object' &&
    Object.keys(parseResult.ciphering).length > 0

  const hasValidCompression = parseResult.compression &&
    typeof parseResult.compression === 'object' &&
    Object.keys(parseResult.compression).length > 0

  // 情况2：打包结果（有 raw_hex 和 frame_length，但没有 wrapper/apdu）
  const isPackageResult = !hasValidWrapper && !hasValidApdu &&
    parseResult.raw_hex && parseResult.frame_length !== undefined

  if (isPackageResult) {
    return (
      <div style={{ padding: '16px 0' }}>
        <Alert
          message="打包成功"
          description={
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Text>打包流程：APDU → V.44压缩 → general-glo-ciphering</Text>
              {parseResult.compress !== undefined && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  V.44压缩: {parseResult.compress ? '已启用' : '未启用'}
                </Text>
              )}
              {parseResult.encrypt !== undefined && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  AES-GCM加密: {parseResult.encrypt ? '已启用' : '未启用'}
                </Text>
              )}
              {parseResult.sc_flags && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  SC标志: {parseResult.sc_flags}
                </Text>
              )}
            </Space>
          }
          type="success"
          showIcon
          icon={<CheckCircleOutlined />}
          style={{ marginBottom: 16 }}
        />
        <Card
          size="small"
          title={
            <Space>
              <ExportOutlined />
              <Text strong>打包输出</Text>
              <Tag color="green">{parseResult.frame_length} 字节</Tag>
            </Space>
          }
          style={{ borderLeft: '3px solid var(--ant-green-5)' }}
          bodyStyle={{ padding: 12 }}
        >
          <Descriptions size="small" column={1} bordered>
            <Descriptions.Item label="帧长度">
              <Statistic value={parseResult.frame_length} suffix="bytes" valueStyle={{ fontSize: 14 }} />
            </Descriptions.Item>
            <Descriptions.Item label="十六进制数据">
              <div style={{
                maxHeight: 200, overflow: 'auto',
                padding: 8, background: '#fafafa', borderRadius: 4,
                fontFamily: 'monospace', fontSize: 12, wordBreak: 'break-all'
              }}>
                {parseResult.raw_hex}
              </div>
            </Descriptions.Item>
            {parseResult.apdu_hex && (
              <Descriptions.Item label="原始APDU">
                <Text code style={{ fontSize: 11, wordBreak: 'break-all' }}>{parseResult.apdu_hex}</Text>
              </Descriptions.Item>
            )}
          </Descriptions>
        </Card>
      </div>
    )
  }

  // 情况3：有APDU数据但无Wrapper（直接解析原始APDU）
  // 情况4：有Wrapper的正常解析结果
  if (!hasValidWrapper && !hasValidApdu && !hasValidCiphering && !hasValidCompression) {
    // 完全没有有效数据 → 显示错误
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
                  请检查输入的十六进制数据是否为有效的 DLMS 帧格式。
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

  // 构建层列表（根据实际数据动态构建）
  const layers = []

  if (hasValidWrapper) {
    layers.push({
      key: 'wrapper',
      title: 'Wrapper 层',
      icon: <GiftOutlined />,
      color: 'blue',
      data: parseResult.wrapper,
      component: WrapperLayer
    })
  }

  if (hasValidCiphering) {
    layers.push({
      key: 'ciphering',
      title: '加密层',
      icon: <LockOutlined />,
      color: 'orange',
      data: parseResult.ciphering,
      component: CipherLayer
    })
  }

  if (hasValidCompression) {
    layers.push({
      key: 'compression',
      title: '压缩层',
      icon: <CompressOutlined />,
      color: 'green',
      data: parseResult.compression,
      component: CompressionLayer
    })
  }

  if (hasValidApdu) {
    layers.push({
      key: 'apdu',
      title: 'APDU 层',
      icon: <FileTextOutlined />,
      color: 'purple',
      data: parseResult.apdu,
      component: APDULayer
    })
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

      {/* 数模匹配结果 */}
      {parseResult.matched_objects && parseResult.matched_objects.length > 0 && (
        <Card
          size="small"
          title={
            <Space>
              <DatabaseOutlined />
              <Text strong>数模匹配</Text>
              <Tag color="cyan">{parseResult.matched_objects.length} 个对象</Tag>
            </Space>
          }
          style={{ marginTop: 16, borderLeft: '3px solid var(--ant-cyan-5)' }}
          bodyStyle={{ padding: 12 }}
        >
          <Table
            size="small"
            pagination={false}
            dataSource={parseResult.matched_objects.map((obj, i) => ({ ...obj, key: i }))}
            columns={[
              { title: '名称', dataIndex: 'name', key: 'name', width: 180 },
              { title: 'Class', dataIndex: 'class_id', key: 'class_id', width: 70 },
              { title: 'OBIS', dataIndex: 'obis', key: 'obis', width: 160 },
              { title: '属性ID', dataIndex: 'attribute_id', key: 'attribute_id', width: 70 },
              { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
              { title: '单位', dataIndex: 'unit', key: 'unit', width: 70 },
            ]}
          />
        </Card>
      )}
    </div>
  )
}

export default LayerView
