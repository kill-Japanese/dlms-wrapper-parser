import { Tree, Typography, Tag, Space, Empty } from 'antd'
import {
  FileTextOutlined,
  DatabaseOutlined,
  ApiOutlined,
  NumberOutlined,
  FontSizeOutlined,
  CheckCircleOutlined
} from '@ant-design/icons'

const { Text } = Typography

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

function APDULayer({ data }) {
  if (!data) return null

  // 后端返回 snake_case 字段名
  const { tag, type_name, invoke_id, raw_hex, items, apdu_type } = data

  // 优先使用 apdu_type 或 type_name
  const displayType = apdu_type || type_name || `Tag 0x${tag?.toString(16).padStart(2, '0').toUpperCase()}`

  const treeData = items && items.length > 0 ? convertToTreeData({ type: 'array', value: items }) : []

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
      </Space>

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
