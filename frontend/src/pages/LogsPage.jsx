import {
  Card,
  Tabs,
  List,
  Tag,
  Space,
  Input,
  Select,
  Button,
  Empty,
  Typography,
  Row,
  Col,
  message
} from 'antd'
import {
  FileTextOutlined,
  ClearOutlined,
  SearchOutlined,
  ArrowDownOutlined,
  ArrowUpOutlined
} from '@ant-design/icons'
import useLogStore from '../store/logStore.js'

const { Title, Text } = Typography

// 模拟解析日志
const mockParseLogs = [
  {
    id: 1,
    timestamp: '2024-01-15 10:30:15',
    level: 'info',
    message: '解析成功 - Wrapper层解析完成',
    details: { layer: 'wrapper', length: 128 }
  },
  {
    id: 2,
    timestamp: '2024-01-15 10:30:16',
    level: 'info',
    message: '解析成功 - 加密层解密完成',
    details: { layer: 'cipher', algorithm: 'AES-GCM' }
  },
  {
    id: 3,
    timestamp: '2024-01-15 10:30:17',
    level: 'info',
    message: '解析成功 - 压缩层解压完成',
    details: { layer: 'compression', ratio: 0.65 }
  },
  {
    id: 4,
    timestamp: '2024-01-15 10:30:18',
    level: 'info',
    message: '解析成功 - APDU解析完成',
    details: { layer: 'apdu', type: 'GET-RESPONSE' }
  },
  {
    id: 5,
    timestamp: '2024-01-15 10:31:00',
    level: 'error',
    message: '解析失败 - 无效的Hex格式',
    details: { error: 'Invalid hex string' }
  },
  {
    id: 6,
    timestamp: '2024-01-15 10:32:00',
    level: 'warning',
    message: '警告 - System Title不匹配',
    details: { expected: '12345678', actual: '87654321' }
  }
]

// 模拟数据交互日志
const mockDataLogs = [
  {
    id: 1,
    timestamp: '2024-01-15 10:30:15.123',
    direction: 'in',
    device: 'device-001',
    hex: 'E6E700...',
    length: 128
  },
  {
    id: 2,
    timestamp: '2024-01-15 10:30:15.345',
    direction: 'out',
    device: 'device-001',
    hex: 'E6E700...',
    length: 64
  },
  {
    id: 3,
    timestamp: '2024-01-15 10:30:16.000',
    direction: 'in',
    device: 'device-001',
    hex: 'E6E700...',
    length: 256
  },
  {
    id: 4,
    timestamp: '2024-01-15 10:30:20.000',
    direction: 'in',
    device: 'device-002',
    hex: 'E6E700...',
    length: 100
  }
]

const levelColors = {
  info: 'blue',
  warning: 'orange',
  error: 'red',
  success: 'green'
}

function LogsPage() {
  const {
    activeTab,
    filter,
    setActiveTab,
    setFilter,
    clearParseLogs,
    clearDataLogs
  } = useLogStore()

  const handleClearLogs = () => {
    if (activeTab === 'parse') {
      clearParseLogs()
      message.info('解析日志已清空')
    } else {
      clearDataLogs()
      message.info('数据日志已清空')
    }
  }

  // 过滤后的日志
  const filteredParseLogs = mockParseLogs.filter((log) => {
    if (filter.level !== 'all' && log.level !== filter.level) return false
    if (filter.keyword && !log.message.toLowerCase().includes(filter.keyword.toLowerCase())) return false
    return true
  })

  const filteredDataLogs = mockDataLogs.filter((log) => {
    if (filter.type !== 'all' && log.direction !== filter.type) return false
    if (filter.keyword && !log.device.toLowerCase().includes(filter.keyword.toLowerCase())) return false
    return true
  })

  const parseLogItems = [
    {
      key: 'parse',
      label: (
        <Space>
          <FileTextOutlined />
          解析日志
        </Space>
      ),
      children: (
        <div>
          {/* 过滤栏 */}
          <Row gutter={[8, 8]} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Select
                value={filter.level}
                onChange={(value) => setFilter({ level: value })}
                style={{ width: '100%' }}
                options={[
                  { value: 'all', label: '全部级别' },
                  { value: 'info', label: 'Info' },
                  { value: 'warning', label: 'Warning' },
                  { value: 'error', label: 'Error' }
                ]}
              />
            </Col>
            <Col span={12}>
              <Input
                placeholder="搜索关键词..."
                prefix={<SearchOutlined />}
                value={filter.keyword}
                onChange={(e) => setFilter({ keyword: e.target.value })}
                allowClear
              />
            </Col>
            <Col span={6} style={{ textAlign: 'right' }}>
              <Button icon={<ClearOutlined />} onClick={handleClearLogs}>
                清空
              </Button>
            </Col>
          </Row>

          {/* 日志列表 */}
          {filteredParseLogs.length > 0 ? (
            <List
              dataSource={filteredParseLogs}
              renderItem={(log) => (
                <List.Item style={{ padding: '12px 16px' }}>
                  <Space direction="vertical" size={4} style={{ width: '100%' }}>
                    <Space>
                      <Tag color={levelColors[log.level] || 'default'}>
                        {log.level.toUpperCase()}
                      </Tag>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {log.timestamp}
                      </Text>
                    </Space>
                    <Text>{log.message}</Text>
                    {log.details && (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {JSON.stringify(log.details)}
                      </Text>
                    )}
                  </Space>
                </List.Item>
              )}
            />
          ) : (
            <Empty description="暂无日志" style={{ marginTop: 60 }} />
          )}
        </div>
      )
    },
    {
      key: 'data',
      label: (
        <Space>
          <ArrowDownOutlined />
          数据交互日志
        </Space>
      ),
      children: (
        <div>
          {/* 过滤栏 */}
          <Row gutter={[8, 8]} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Select
                value={filter.type}
                onChange={(value) => setFilter({ type: value })}
                style={{ width: '100%' }}
                options={[
                  { value: 'all', label: '全部方向' },
                  { value: 'in', label: '上行（设备→服务器）' },
                  { value: 'out', label: '下行（服务器→设备）' }
                ]}
              />
            </Col>
            <Col span={12}>
              <Input
                placeholder="搜索设备..."
                prefix={<SearchOutlined />}
                value={filter.keyword}
                onChange={(e) => setFilter({ keyword: e.target.value })}
                allowClear
              />
            </Col>
            <Col span={6} style={{ textAlign: 'right' }}>
              <Button icon={<ClearOutlined />} onClick={handleClearLogs}>
                清空
              </Button>
            </Col>
          </Row>

          {/* 日志列表 */}
          {filteredDataLogs.length > 0 ? (
            <List
              dataSource={filteredDataLogs}
              renderItem={(log) => (
                <List.Item style={{ padding: '12px 16px' }}>
                  <Space style={{ width: '100%' }} align="start">
                    <div style={{ marginTop: 4 }}>
                      {log.direction === 'in' ? (
                        <ArrowUpOutlined style={{ color: '#52c41a' }} />
                      ) : (
                        <ArrowDownOutlined style={{ color: '#1890ff' }} />
                      )}
                    </div>
                    <Space direction="vertical" size={4} style={{ flex: 1 }}>
                      <Space>
                        <Tag color={log.direction === 'in' ? 'green' : 'blue'}>
                          {log.direction === 'in' ? '上行' : '下行'}
                        </Tag>
                        <Text strong>{log.device}</Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {log.length} bytes
                        </Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {log.timestamp}
                        </Text>
                      </Space>
                      <Text
                        code
                        style={{
                          fontSize: 12,
                          wordBreak: 'break-all',
                          display: 'block'
                        }}
                      >
                        {log.hex}
                      </Text>
                    </Space>
                  </Space>
                </List.Item>
              )}
            />
          ) : (
            <Empty description="暂无日志" style={{ marginTop: 60 }} />
          )}
        </div>
      )
    }
  ]

  return (
    <div className="page-container">
      <Card
        title={
          <Space>
            <FileTextOutlined />
            <Title level={5} style={{ margin: 0 }}>
              日志查看
            </Title>
          </Space>
        }
        style={{ height: '100%' }}
        bodyStyle={{ height: 'calc(100% - 57px)', overflow: 'auto' }}
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={parseLogItems}
        />
      </Card>
    </div>
  )
}

export default LogsPage
