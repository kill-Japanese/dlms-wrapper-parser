import { useState } from 'react'
import {
  Card,
  Table,
  Tag,
  Space,
  Typography,
  Collapse,
  Button,
  Input,
  Row,
  Col,
  Tabs,
  message,
  Alert,
  Divider
} from 'antd'
import {
  CopyOutlined,
  CheckCircleOutlined,
  FileTextOutlined,
  ThunderboltOutlined
} from '@ant-design/icons'
import CopyButton from '../common/CopyButton.jsx'

const { Text, Title } = Typography
const { Panel } = Collapse

function PullResult({ result }) {
  const [activeFrameIndex, setActiveFrameIndex] = useState(0)

  if (!result) {
    return (
      <Card style={{ height: '100%' }} bodyStyle={{ height: '100%' }}>
        <div
          style={{
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
            color: '#999'
          }}
        >
          <ThunderboltOutlined style={{ fontSize: 48, marginBottom: 12 }} />
          <Text type="secondary">执行结果将在这里显示</Text>
          <Text type="secondary" style={{ fontSize: 12, marginTop: 4 }}>
            选择一个预设并点击执行
          </Text>
        </div>
      </Card>
    )
  }

  const frames = result.frames || []
  const currentFrame = frames[activeFrameIndex]

  const columns = [
    {
      title: '#',
      key: 'index',
      width: 50,
      render: (_, __, index) => index + 1
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (text) => (
        <Tag color={text === 'with_list' ? 'green' : 'blue'}>
          {text === 'with_list' ? 'WithList' : 'Normal'}
        </Tag>
      )
    },
    {
      title: 'Invoke ID',
      dataIndex: 'invoke_id',
      key: 'invoke_id',
      width: 90
    },
    {
      title: '对象数',
      dataIndex: 'operation_count',
      key: 'operation_count',
      width: 80,
      render: (text) => text || '-'
    },
    {
      title: 'OBIS',
      dataIndex: 'obis',
      key: 'obis',
      render: (text) => text ? <Text code>{text}</Text> : '-'
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text) => text || '-'
    },
    {
      title: 'APDU 长度',
      dataIndex: 'apdu_length',
      key: 'apdu_length',
      width: 100,
      render: (text) => `${text} bytes`
    }
  ]

  return (
    <Card
      style={{ height: '100%' }}
      bodyStyle={{ height: 'calc(100% - 57px)', padding: 0, overflow: 'auto' }}
      title={
        <Space>
          <FileTextOutlined />
          <Title level={5} style={{ margin: 0 }}>
            执行结果
          </Title>
          {result.preset_name && (
            <Tag color="blue">{result.preset_name}</Tag>
          )}
          <Tag color="green">{result.operation_count} 个操作</Tag>
          <Tag color="purple">{result.frame_count} 帧</Tag>
          <Tag>{result.use_with_list ? 'WithList 模式' : 'Normal 模式'}</Tag>
        </Space>
      }
    >
      <div style={{ padding: 12 }}>
        {/* 帧列表 */}
        <div style={{ marginBottom: 12 }}>
          <Text type="secondary" style={{ marginBottom: 8, display: 'block' }}>
            生成的帧：
          </Text>
          <Table
            dataSource={frames}
            columns={columns}
            rowKey={(record, index) => index}
            size="small"
            pagination={false}
            onRow={(record, index) => ({
              style: {
                cursor: 'pointer',
                background: activeFrameIndex === index ? '#e6f4ff' : undefined
              },
              onClick: () => setActiveFrameIndex(index)
            })}
          />
        </div>

        {/* 当前帧详情 */}
        {currentFrame && (
          <Card
            size="small"
            title={
              <Space>
                <Text strong>帧 #{activeFrameIndex + 1} 详情</Text>
                <Tag color={currentFrame.type === 'with_list' ? 'green' : 'blue'}>
                  {currentFrame.type === 'with_list' ? 'GetRequest WithList' : 'GetRequest Normal'}
                </Tag>
              </Space>
            }
          >
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              {/* 帧信息 */}
              <Row gutter={16}>
                <Col span={8}>
                  <Text type="secondary">Invoke ID:</Text>
                  <Text> {currentFrame.invoke_id}</Text>
                </Col>
                <Col span={8}>
                  <Text type="secondary">APDU 长度:</Text>
                  <Text> {currentFrame.apdu_length} bytes</Text>
                </Col>
                <Col span={8}>
                  <Text type="secondary">Wrapper 长度:</Text>
                  <Text> {currentFrame.wrapper_length || '-'} bytes</Text>
                </Col>
              </Row>

              <Divider style={{ margin: '8px 0' }} />

              {/* APDU 数据 */}
              <div>
                <Space style={{ marginBottom: 8 }}>
                  <Text strong>APDU (Hex):</Text>
                  <CopyButton text={currentFrame.apdu_hex} />
                </Space>
                <div
                  style={{
                    padding: 12,
                    background: '#f6f6f6',
                    borderRadius: 4,
                    fontFamily: 'monospace',
                    fontSize: 12,
                    wordBreak: 'break-all',
                    maxHeight: 120,
                    overflow: 'auto'
                  }}
                >
                  {currentFrame.apdu_hex}
                </div>
              </div>

              {/* Wrapper 数据 */}
              {currentFrame.wrapper_hex && (
                <div>
                  <Space style={{ marginBottom: 8 }}>
                    <Text strong>Wrapper 帧 (Hex):</Text>
                    <CopyButton text={currentFrame.wrapper_hex} />
                  </Space>
                  <div
                    style={{
                      padding: 12,
                      background: '#f0f5ff',
                      borderRadius: 4,
                      fontFamily: 'monospace',
                      fontSize: 12,
                      wordBreak: 'break-all',
                      maxHeight: 120,
                      overflow: 'auto'
                    }}
                  >
                    {currentFrame.wrapper_hex}
                  </div>
                </div>
              )}
            </Space>
          </Card>
        )}

        {/* 操作列表详情 */}
        <div style={{ marginTop: 16 }}>
          <Collapse
            defaultActiveKey={['1']}
            size="small"
            items={[{
              key: '1',
              label: `操作详情 (${result.operation_count} 个)`,
              children: (
                <div>
                  {frames.flatMap((frame, fIdx) => {
                    if (frame.type === 'with_list') {
                      // WithList 模式，需要从 result 中获取操作信息
                      return (
                        <div key={fIdx}>
                          <Alert
                            message={`帧 ${fIdx + 1}: GetRequest WithList - 包含 ${frame.operation_count} 个对象`}
                            type="info"
                            showIcon
                            style={{ marginBottom: 8 }}
                          />
                        </div>
                      )
                    } else {
                      return (
                        <div key={fIdx} style={{ padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
                          <Row gutter={8}>
                            <Col span={2}>
                              <Text type="secondary">{fIdx + 1}.</Text>
                            </Col>
                            <Col span={6}>
                              <Text code>{frame.obis}</Text>
                            </Col>
                            <Col span={8}>
                              <Text>{frame.name}</Text>
                            </Col>
                            <Col span={4}>
                              <Tag color="blue">Class {frame.class_id}</Tag>
                            </Col>
                            <Col span={4}>
                              <Text type="secondary">Attr {frame.attribute_id}</Text>
                            </Col>
                          </Row>
                        </div>
                      )
                    }
                  })}
                </div>
              )
            }]}
          />
        </div>
      </div>
    </Card>
  )
}

export default PullResult
