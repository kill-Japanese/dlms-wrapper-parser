import { Tree, Typography, Tag, Space, Empty, Select, Row, Col, Card, Table } from 'antd'
import {
  FileTextOutlined,
  DatabaseOutlined,
  ApiOutlined,
  NumberOutlined,
  FontSizeOutlined,
  CheckCircleOutlined,
  SettingOutlined,
  InfoCircleOutlined,
  BulbOutlined
} from '@ant-design/icons'
import { useState } from 'react'

const { Text } = Typography
const { Option } = Select

// 数据类型对应的图标
const typeIcons = {
  structure: <DatabaseOutlined style={{ color: '#1677ff' }} />,
  array: <DatabaseOutlined style={{ color: '#52c41a' }} />,
  'long-unsigned': <NumberOutlined style={{ color: '#faad14' }} />,
  'double-long-unsigned': <NumberOutlined style={{ color: '#faad14' }} />,
  'unsigned': <NumberOutlined style={{ color: '#faad14' }} />,
  integer: <NumberOutlined style={{ color: '#faad14' }} />,
  'long-integer': <NumberOutlined style={{ color: '#faad14' }} />,
  'double-long-integer': <NumberOutlined style={{ color: '#faad14' }} />,
  'octet-string': <FontSizeOutlined style={{ color: '#722ed1' }} />,
  string: <FontSizeOutlined style={{ color: '#722ed1' }} />,
  boolean: <CheckCircleOutlined style={{ color: '#13c2c2' }} />,
  'null-data': <ApiOutlined style={{ color: '#8c8c8c' }} />,
  default: <FileTextOutlined style={{ color: '#8c8c8c' }} />
}

// 将数据转换为Tree组件需要的格式
const convertToTreeData = (data, parentKey = '') => {
  if (!data) return []

  const nodes = []

  if (data.type === 'structure' || data.type === 'array') {
    const key = `${parentKey || 'root'}-${data.type}`
    const children = Array.isArray(data.value)
      ? data.value.map((item, index) => {
          const childKey = `${key}-${index}`
          if (item.type === 'structure' || item.type === 'array') {
            return {
              key: childKey,
              title: (
                <Space>
                  {typeIcons[item.type] || typeIcons.default}
                  <Text strong>{item.name || `Item ${index}`}</Text>
                  <Tag color="blue" style={{ fontSize: 11 }}>
                    {item.type}
                  </Tag>
                </Space>
              ),
              icon: typeIcons[item.type] || typeIcons.default,
              children: convertToTreeData(item, childKey)
            }
          }
          return {
            key: childKey,
            title: (
              <Space>
                {typeIcons[item.type] || typeIcons.default}
                <Text>{item.name || `Item ${index}`}</Text>
                <Tag style={{ fontSize: 11 }}>{item.type}</Tag>
                <Text type="secondary" style={{ fontSize: 12 }}>=</Text>
                <Text code>{formatValue(item)}</Text>
              </Space>
            ),
            icon: typeIcons[item.type] || typeIcons.default,
            isLeaf: true
          }
        })
      : []

    nodes.push({
      key,
      title: (
        <Space>
          {typeIcons[data.type] || typeIcons.default}
          <Text strong>{data.name || data.type}</Text>
          <Tag color="blue" style={{ fontSize: 11 }}>
            {data.type}
          </Tag>
          <Text type="secondary" style={{ fontSize: 12 }}>
            ({Array.isArray(data.value) ? data.value.length : 0} 项)
          </Text>
        </Space>
      ),
      icon: typeIcons[data.type] || typeIcons.default,
      children
    })
  } else if (data.type) {
    const key = `${parentKey || 'root'}-leaf`
    nodes.push({
      key,
      title: (
        <Space>
          {typeIcons[data.type] || typeIcons.default}
          <Text>{data.name || data.type}</Text>
          <Tag style={{ fontSize: 11 }}>{data.type}</Tag>
          <Text type="secondary" style={{ fontSize: 12 }}>=</Text>
          <Text code>{formatValue(data)}</Text>
        </Space>
      ),
      icon: typeIcons[data.type] || typeIcons.default,
      isLeaf: true
    })
  }

  return nodes
}

// 格式化值显示
const formatValue = (item) => {
  if (item.value === undefined || item.value === null) return 'null'
  if (typeof item.value === 'object') {
    return JSON.stringify(item.value)
  }
  return String(item.value)
}

// 已知 class 名称映射
const CLASS_NAMES = {
  1: 'Data',
  3: 'Register',
  4: 'Extended Register',
  5: 'Demand Register',
  7: 'Profile Generic',
  8: 'Clock',
  9: 'Script Table',
  15: 'Association LN',
  40: 'Push Setup',
  64: 'Security Setup',
  70: 'Disconnect Control',
}

function APDULayer({ data }) {
  const [selectedVersion, setSelectedVersion] = useState(null)
  const [autoDetect, setAutoDetect] = useState(true)

  if (!data) return null

  // 后端返回 snake_case 字段名
  const {
    tag,
    type_name,
    invoke_id,
    raw_hex,
    items,
    apdu_type,
    push_setup_version,
    push_setup_version_name,
    push_object_list,
    has_class40_template,
    item_count
  } = data

  // 优先使用 apdu_type 或 type_name
  const displayType = apdu_type || type_name || `Tag 0x${tag?.toString(16).padStart(2, '0').toUpperCase()}`

  const treeData = items && items.length > 0 ? convertToTreeData({ type: 'array', value: items }) : []

  // 是否是 DataNotification 类型
  const isDataNotification = type_name === 'DataNotification' || apdu_type === 'DataNotification'

  // Push object list 表格列定义
  const pushObjColumns = [
    {
      title: '#',
      dataIndex: 'index',
      key: 'index',
      width: 40,
      render: (_, __, index) => index + 1
    },
    {
      title: 'Class ID',
      dataIndex: 'class_id',
      key: 'class_id',
      width: 80,
      render: (val) => (
        <Space>
          <Tag color="blue">{val}</Tag>
          <Text type="secondary" style={{ fontSize: 11 }}>
            {CLASS_NAMES[val] || ''}
          </Text>
        </Space>
      )
    },
    {
      title: 'OBIS',
      dataIndex: 'obis',
      key: 'obis',
      width: 180,
      render: (val) => <Text code>{val}</Text>
    },
    {
      title: 'Attr',
      dataIndex: 'attribute_id',
      key: 'attribute_id',
      width: 60,
    },
    {
      title: 'Data Index',
      dataIndex: 'data_index',
      key: 'data_index',
      width: 90,
      render: (val) => val !== undefined && val !== null ? val : '-'
    },
  ]

  // 显示的版本号（自动检测或手动选择）
  const displayVersion = autoDetect ? push_setup_version : selectedVersion
  const displayVersionName = autoDetect ? push_setup_version_name : (selectedVersion !== null ? `v${selectedVersion}` : '')

  return (
    <div>
      <Space style={{ marginBottom: 12 }} wrap>
        <Tag color="purple">{displayType}</Tag>
        {invoke_id !== undefined && invoke_id !== null && (
          <Tag>Invoke ID: {invoke_id}</Tag>
        )}
        {tag !== undefined && (
          <Tag color="cyan">Tag: 0x{tag?.toString(16).padStart(2, '0').toUpperCase()}</Tag>
        )}
        {item_count !== undefined && (
          <Tag color="green">{item_count} 个数据项</Tag>
        )}
      </Space>

      {/* Class 40 版本信息 - 仅 DataNotification 显示 */}
      {isDataNotification && (
        <Card
          size="small"
          style={{ marginBottom: 12 }}
          title={
            <Space>
              <SettingOutlined />
              <Text strong>Push Setup (Class 40) 版本</Text>
            </Space>
          }
          extra={
            <Space size="small">
              {has_class40_template && (
                <Tag color="success" icon={<BulbOutlined />}>
                  含模版
                </Tag>
              )}
              {autoDetect ? (
                <Tag color="blue" icon={<InfoCircleOutlined />}>
                  自动识别: {displayVersionName || '未知'}
                </Tag>
              ) : (
                <Tag color="orange">手动选择</Tag>
              )}
            </Space>
          }
        >
          <Row gutter={8} align="middle">
            <Col>
              <Text type="secondary" style={{ fontSize: 12 }}>版本:</Text>
            </Col>
            <Col flex="120px">
              <Select
                size="small"
                style={{ width: '100%' }}
                value={autoDetect ? 'auto' : selectedVersion}
                onChange={(val) => {
                  if (val === 'auto') {
                    setAutoDetect(true)
                    setSelectedVersion(null)
                  } else {
                    setAutoDetect(false)
                    setSelectedVersion(val)
                  }
                }}
              >
                <Option value="auto">自动检测</Option>
                <Option value={0}>v0 - 基础版</Option>
                <Option value={1}>v1 - 推送目标</Option>
                <Option value={2}>v2 - 通信窗口</Option>
                <Option value={3}>v3 - 增强版</Option>
              </Select>
            </Col>
            <Col flex="auto">
              {has_class40_template ? (
                <Text type="success" style={{ fontSize: 12 }}>
                  ✓ 检测到 Class 40 属性2 作为数据模版
                  {push_object_list?.length > 0 && `（共 ${push_object_list.length} 个对象）`}
                </Text>
              ) : (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  未检测到 Class 40 模版
                </Text>
              )}
            </Col>
          </Row>

          {/* Push Object List 表格 */}
          {push_object_list && push_object_list.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <Table
                size="small"
                dataSource={push_object_list}
                columns={pushObjColumns}
                pagination={false}
                scroll={{ y: 200 }}
                rowKey={(record, index) => index}
              />
            </div>
          )}
        </Card>
      )}

      {raw_hex && (
        <div style={{ marginBottom: 12 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>原始数据:</Text>
          <div style={{ 
            marginTop: 4, 
            maxHeight: 60, 
            overflow: 'auto',
            padding: 6,
            background: '#fafafa',
            borderRadius: 4,
            fontFamily: 'monospace',
            fontSize: 12
          }}>
            {raw_hex}
          </div>
        </div>
      )}

      {treeData.length > 0 ? (
        <div
          style={{
            maxHeight: 400,
            overflow: 'auto',
            padding: 8,
            background: '#fafafa',
            borderRadius: 4,
            border: '1px solid #f0f0f0'
          }}
        >
          <Tree
            showLine
            showIcon
            defaultExpandAll
            treeData={treeData}
            blockNode
          />
        </div>
      ) : (
        <Empty
          image={<ApiOutlined style={{ fontSize: 32, color: '#d9d9d9' }} />}
          description="无解析数据结构"
          style={{ padding: 20 }}
        />
      )}
    </div>
  )
}

export default APDULayer
