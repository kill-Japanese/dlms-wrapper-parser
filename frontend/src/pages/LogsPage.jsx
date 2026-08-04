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

const levelColors = {
  info: 'blue',
  warn: 'orange',
  warning: 'orange',
  error: 'red',
  success: 'green',
  debug: 'default'
}

function LogsPage() {
  const {
    activeTab,
    filter,
    parseLogs,
    dataLogs,
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

  // 过滤后的解析日志
  const filteredParseLogs = parseLogs.filter((log) => {
    if (filter.level !== 'all' && log.level !== filter.level) return false
    if (filter.keyword) {
      const keyword = filter.keyword.toLowerCase()
      const searchText = `${log.message || ''} ${log.step || ''} ${log.details || ''}`.toLowerCase()
      if (!searchText.includes(keyword)) return false
    }
    return true
  })

  // 过滤后的数据交互日志
  const filteredDataLogs = dataLogs.filter((log) => {
    if (filter.type !== 'all' && log.direction !== filter.type) return false
    if (filter.keyword) {
      const keyword = filter.keyword.toLowerCase()
      const searchText = `${log.device || ''} ${log.hex || ''}`.toLowerCase()
      if (!searchText.includes(keyword)) return false
    }
    return true
  })

  const parseLogItems = [
    {
      key: 'parse',
      label: (
        <Space>
          <FileTextOutlined />
          解析日志
          <Tag color="blue" style={{ marginLeft: 0 }}>
            {parseLogs.length}
          </Tag>
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
                  { value: 'warn', label: 'Warning' },
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
                        {(log.level || 'info').toUpperCase()}
                      </Tag>
                      {log.step && (
                        <Tag color="default" style={{ fontSize: 11 }}>
                          {log.step}
                        </Tag>
                      )}
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {log.timestamp}
                      </Text>
                    </Space>
                    <Text>{log.message}</Text>
                    {log.details && (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {typeof log.details === 'object'
                          ? JSON.stringify(log.details)
                          : String(log.details)}
                      </Text>
                    )}
                  </Space>
                </List.Item>
              )}
            />
          ) : (
            <Empty description="暂无解析日志" style={{ marginTop: 60 }} />
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
          <Tag color="green" style={{ marginLeft: 0 }}>
            {dataLogs.length}
          </Tag>
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
                        <Text strong>{log.device || '未知设备'}</Text>
                        {log.length !== undefined && (
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {log.length} bytes
                          </Text>
                        )}
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {log.timestamp}
                        </Text>
                      </Space>
                      {log.hex && (
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
                      )}
                    </Space>
                  </Space>
                </List.Item>
              )}
            />
          ) : (
            <Empty description="暂无数据交互日志" style={{ marginTop: 60 }} />
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
