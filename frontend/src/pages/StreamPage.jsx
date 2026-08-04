import { useState } from 'react'
import {
  Row,
  Col,
  Card,
  Button,
  Space,
  Typography,
  Badge,
  Tag,
  List,
  Input,
  Timeline,
  Empty,
  Tabs,
  Statistic,
  Divider,
  message
} from 'antd'
import {
  ThunderboltOutlined,
  PlayCircleOutlined,
  StopOutlined,
  SendOutlined,
  DesktopOutlined,
  RocketOutlined
} from '@ant-design/icons'
import useStreamStore from '../store/streamStore.js'

const { Title, Text } = Typography
const { TextArea } = Input

// 模拟帧数据
const mockFrames = [
  {
    id: 1,
    timestamp: '2024-01-15 10:30:15.123',
    direction: 'in',
    device: 'device-001',
    hex: 'E6E700...',
    length: 128,
    type: 'AARQ'
  },
  {
    id: 2,
    timestamp: '2024-01-15 10:30:15.345',
    direction: 'out',
    device: 'device-001',
    hex: 'E6E700...',
    length: 64,
    type: 'AARE'
  },
  {
    id: 3,
    timestamp: '2024-01-15 10:30:16.000',
    direction: 'in',
    device: 'device-001',
    hex: 'E6E700...',
    length: 256,
    type: 'GET-RESPONSE'
  }
]

function StreamPage() {
  const {
    tcpStatus,
    tcpPort,
    connectedDevices,
    frames,
    selectedFrameId,
    sendPanel,
    setTcpStatus,
    selectFrame,
    setSendPanel
  } = useStreamStore()

  const [displayFrames] = useState(mockFrames)
  const selectedFrame = displayFrames.find((f) => f.id === selectedFrameId)

  const mockDevices = [
    { id: 'device-001', address: '192.168.1.100', wport: 1, connectedAt: '10:30:00', status: 'active' },
    { id: 'device-002', address: '192.168.1.101', wport: 2, connectedAt: '10:31:00', status: 'active' }
  ]

  const handleStartServer = () => {
    setTcpStatus('starting')
    setTimeout(() => {
      setTcpStatus('running')
      message.success(`TCP 服务器已启动，端口: ${tcpPort}`)
    }, 1000)
  }

  const handleStopServer = () => {
    setTcpStatus('stopping')
    setTimeout(() => {
      setTcpStatus('stopped')
      message.info('TCP 服务器已停止')
    }, 800)
  }

  const handleSend = () => {
    if (!sendPanel.hexData) {
      message.warning('请输入要发送的十六进制数据')
      return
    }
    message.success('数据已发送')
  }

  const statusConfig = {
    stopped: { status: 'default', text: '已停止', color: 'default' },
    starting: { status: 'processing', text: '启动中', color: 'blue' },
    running: { status: 'success', text: '运行中', color: 'green' },
    stopping: { status: 'processing', text: '停止中', color: 'orange' }
  }

  const currentStatus = statusConfig[tcpStatus] || statusConfig.stopped

  return (
    <div className="page-container">
      <Card
        style={{ height: '100%' }}
        bodyStyle={{ height: 'calc(100% - 57px)', padding: 0 }}
        title={
          <Space>
            <ThunderboltOutlined />
            <Title level={5} style={{ margin: 0 }}>
              实时流 / TCP 管理
            </Title>
            <Badge status={currentStatus.status} text={currentStatus.text} />
          </Space>
        }
        extra={
          <Space>
            <Text type="secondary">端口: {tcpPort}</Text>
            {tcpStatus === 'running' || tcpStatus === 'stopping' ? (
              <Button
                danger
                icon={<StopOutlined />}
                onClick={handleStopServer}
                loading={tcpStatus === 'stopping'}
              >
                停止服务
              </Button>
            ) : (
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleStartServer}
                loading={tcpStatus === 'starting'}
              >
                启动服务
              </Button>
            )}
          </Space>
        }
      >
        <Row style={{ height: '100%' }}>
          {/* 左侧：设备列表 */}
          <Col span={6} style={{ height: '100%', borderRight: '1px solid #f0f0f0' }}>
            <div style={{ padding: 12 }}>
              <Space align="center" style={{ marginBottom: 8 }}>
                <DesktopOutlined />
                <Text strong>已连接设备</Text>
                <Tag color="green">{mockDevices.length}</Tag>
              </Space>
            </div>
            <div style={{ overflow: 'auto', height: 'calc(100% - 44px)' }}>
              {mockDevices.length > 0 ? (
                <List
                  dataSource={mockDevices}
                  renderItem={(device) => (
                    <List.Item style={{ padding: '12px 16px', cursor: 'pointer' }}>
                      <List.Item.Meta
                        avatar={<DesktopOutlined style={{ fontSize: 20, color: '#52c41a' }} />}
                        title={
                          <Space>
                            <Text strong>{device.id}</Text>
                            <Badge status="success" />
                          </Space>
                        }
                        description={
                          <Space direction="vertical" size={0}>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {device.address}
                            </Text>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              WPort: {device.wport}
                            </Text>
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <Empty description="暂无设备" style={{ marginTop: 40 }} />
              )}
            </div>
          </Col>

          {/* 中间：帧时间线 */}
          <Col span={10} style={{ height: '100%', borderRight: '1px solid #f0f0f0' }}>
            <div style={{ padding: 12, borderBottom: '1px solid #f0f0f0' }}>
              <Space align="center">
                <RocketOutlined />
                <Text strong>帧时间线</Text>
              </Space>
            </div>
            <div style={{ overflow: 'auto', height: 'calc(100% - 44px)', padding: 16 }}>
              {displayFrames.length > 0 ? (
                <Timeline
                  items={displayFrames.map((frame) => ({
                    color: frame.direction === 'in' ? 'green' : 'blue',
                    children: (
                      <div
                        style={{
                          padding: 8,
                          borderRadius: 4,
                          background: selectedFrameId === frame.id ? '#e6f4ff' : '#fafafa',
                          cursor: 'pointer',
                          border: selectedFrameId === frame.id ? '1px solid #1677ff' : '1px solid #f0f0f0'
                        }}
                        onClick={() => selectFrame(frame.id)}
                      >
                        <Space direction="vertical" size={2} style={{ width: '100%' }}>
                          <Space>
                            <Tag color={frame.direction === 'in' ? 'green' : 'blue'}>
                              {frame.direction === 'in' ? '上行' : '下行'}
                            </Tag>
                            <Tag>{frame.type}</Tag>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {frame.length} bytes
                            </Text>
                          </Space>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {frame.timestamp}
                          </Text>
                        </Space>
                      </div>
                    )
                  }))}
                />
              ) : (
                <Empty description="暂无帧数据" style={{ marginTop: 60 }} />
              )}
            </div>
          </Col>

          {/* 右侧：帧详情 + 发送面板 */}
          <Col span={8} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Tabs
              defaultActiveKey="detail"
              items={[
                {
                  key: 'detail',
                  label: '帧详情',
                  children: (
                    <div style={{ padding: 12, overflow: 'auto', height: 'calc(100% - 46px)' }}>
                      {selectedFrame ? (
                        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                          <div>
                            <Text type="secondary">时间戳:</Text>
                            <div>{selectedFrame.timestamp}</div>
                          </div>
                          <div>
                            <Text type="secondary">方向:</Text>
                            <div>
                              <Tag color={selectedFrame.direction === 'in' ? 'green' : 'blue'}>
                                {selectedFrame.direction === 'in' ? '上行（设备→服务器）' : '下行（服务器→设备）'}
                              </Tag>
                            </div>
                          </div>
                          <div>
                            <Text type="secondary">帧类型:</Text>
                            <div>
                              <Tag>{selectedFrame.type}</Tag>
                            </div>
                          </div>
                          <div>
                            <Text type="secondary">长度:</Text>
                            <div>{selectedFrame.length} bytes</div>
                          </div>
                          <div>
                            <Text type="secondary">十六进制数据:</Text>
                            <div
                              className="hex-viewer"
                              style={{
                                fontFamily: 'monospace',
                                fontSize: 12,
                                wordBreak: 'break-all'
                              }}
                            >
                              {selectedFrame.hex}
                            </div>
                          </div>
                        </Space>
                      ) : (
                        <Empty description="请选择一帧查看详情" style={{ marginTop: 60 }} />
                      )}
                    </div>
                  )
                },
                {
                  key: 'send',
                  label: '发送数据',
                  children: (
                    <div style={{ padding: 12, height: 'calc(100% - 46px)', display: 'flex', flexDirection: 'column' }}>
                      <Space direction="vertical" size="middle" style={{ width: '100%', flex: 1 }}>
                        <div>
                          <Text type="secondary">目标设备:</Text>
                          <select
                            value={sendPanel.targetDevice || ''}
                            onChange={(e) => setSendPanel({ targetDevice: e.target.value })}
                            style={{ width: '100%', padding: '4px 8px', marginTop: 4 }}
                          >
                            <option value="">选择设备...</option>
                            {mockDevices.map((d) => (
                              <option key={d.id} value={d.id}>
                                {d.id}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                          <Text type="secondary">十六进制数据:</Text>
                          <TextArea
                            value={sendPanel.hexData}
                            onChange={(e) => setSendPanel({ hexData: e.target.value })}
                            placeholder="输入要发送的十六进制数据..."
                            style={{
                              flex: 1,
                              fontFamily: 'monospace',
                              fontSize: 13,
                              marginTop: 4
                            }}
                          />
                        </div>
                        <div>
                          <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                            <input
                              type="checkbox"
                              checked={sendPanel.autoIncrementCounter}
                              onChange={(e) => setSendPanel({ autoIncrementCounter: e.target.checked })}
                            />
                            自动递增Invocation Counter
                          </label>
                        </div>
                        <Button type="primary" icon={<SendOutlined />} onClick={handleSend} block>
                          发送
                        </Button>
                      </Space>
                    </div>
                  )
                }
              ]}
            />
          </Col>
        </Row>
      </Card>
    </div>
  )
}

export default StreamPage
