import { Table, Tag, Space, Typography, Button, Alert, Tooltip, Card } from 'antd'
import {
  TableOutlined,
  EditOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined
} from '@ant-design/icons'

const { Text } = Typography

/**
 * 格式化字段值用于表格展示
 */
function formatCellValue(field) {
  if (!field) return '-'
  const val = field.formatted_value
  if (val === null || val === undefined) {
    return String(field.raw_value ?? 'null')
  }
  // date-time 对象
  if (typeof val === 'object' && val.iso) {
    return val.iso
  }
  if (typeof val === 'object') {
    return JSON.stringify(val)
  }
  return String(val)
}

/**
 * Profile Buffer 深度解析结果展示
 *
 * 展示 DataNotification 中 Profile Generic (Class 7) buffer 的逐元素解析结果。
 * buffer 是一个 array of structure，每个 structure 是一条记录，
 * 每个 structure 的元素对应一个 capture object。
 *
 * 支持两种展示模式:
 * 1. 多条记录: 矩阵表格 (行=记录, 列=capture object)
 * 2. 单条记录: 逐字段表格 (行=字段)
 *
 * Props:
 * - profileBuffer: 后端 push_resolved.resolved_items[].profile_buffer 对象
 * - onConfigure: 点击"配置 capture_objects"按钮的回调
 */
function ProfileBufferTable({ profileBuffer, onConfigure }) {
  if (!profileBuffer) return null

  const {
    profile_obis: profileObis,
    capture_objects_source: source,
    capture_objects: captureObjects = [],
    entries = [],
    entry_count: entryCount = 0,
    // 兼容旧格式 (单条记录)
    fields: legacyFields = [],
    field_count: legacyFieldCount,
    warning,
    raw_structure: rawStructure
  } = profileBuffer

  // 来源标签配置
  const sourceConfig = {
    manual: { color: 'success', text: '手动配置', icon: <CheckCircleOutlined /> },
    data_model: { color: 'blue', text: '数据模型', icon: <CheckCircleOutlined /> },
    standard: { color: 'orange', text: '标准库（仅结构）', icon: <InfoCircleOutlined /> },
    unknown: { color: 'error', text: '未知', icon: <WarningOutlined /> }
  }
  const srcCfg = sourceConfig[source] || sourceConfig.unknown

  // 如果无法解析（source=unknown），显示警告和配置按钮
  if (source === 'unknown') {
    return (
      <Card size="small" style={{ marginBottom: 12, borderColor: '#faad14' }}>
        <Alert
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          message={
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Space>
                <Text strong>Profile Buffer 无法深度解析</Text>
                <Tag color="blue">{profileObis}</Tag>
              </Space>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {warning || '未找到 capture_objects 定义，无法解析 buffer 中的每个元素。'}
              </Text>
              {rawStructure && Array.isArray(rawStructure) && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  原始数据包含 {rawStructure.length} 个元素
                </Text>
              )}
              <Button
                type="primary"
                size="small"
                icon={<EditOutlined />}
                onClick={() => onConfigure && onConfigure(profileObis)}
              >
                配置 Capture Objects
              </Button>
            </Space>
          }
        />
      </Card>
    )
  }

  // 决定使用 entries 还是 legacy fields
  const hasEntries = entries && entries.length > 0
  const useEntries = hasEntries
  const displayEntries = useEntries ? entries : [{ fields: legacyFields, entry_index: 0 }]
  const firstEntryFields = displayEntries[0]?.fields || []
  const totalFields = firstEntryFields.length

  // ===== 多条记录: 矩阵表格 (行=记录, 列=capture object) =====
  if (useEntries && entryCount > 1) {
    // 构建列: 第一列是序号, 后续列是各 capture object
    const matrixColumns = [
      {
        title: '#',
        width: 50,
        fixed: 'left',
        render: (_, __, index) => <Text strong>{index + 1}</Text>
      },
      ...firstEntryFields.map((field, colIdx) => {
        const co = field.capture_object || {}
        return {
          title: (
            <Tooltip title={`${co.class_name || ''} ${co.obis || ''} attr=${co.attribute_id || ''}`}>
              <Space direction="vertical" size={0} style={{ fontSize: 11 }}>
                <Space size={2}>
                  <Tag color="blue" style={{ fontSize: 10, margin: 0 }}>
                    C{co.class_id || '?'}
                  </Tag>
                  {co.remark && <Text type="secondary" style={{ fontSize: 10 }}>{co.remark}</Text>}
                </Space>
                <Text code style={{ fontSize: 10 }}>{co.obis || '-'}</Text>
                <Text type="secondary" style={{ fontSize: 10 }}>
                  A{co.attribute_id || '?'} {co.attribute_name || ''}
                </Text>
              </Space>
            </Tooltip>
          ),
          width: 140,
          render: (_, entry) => {
            const f = entry.fields?.[colIdx]
            const val = formatCellValue(f)
            const unit = f?.unit
            return (
              <Space size="small">
                <Text code style={{ fontSize: 11 }}>{val}</Text>
                {unit && <Tag color="cyan" style={{ fontSize: 10 }}>{unit}</Tag>}
              </Space>
            )
          }
        }
      })
    ]

    return (
      <Card
        size="small"
        style={{ marginBottom: 12 }}
        title={
          <Space>
            <TableOutlined style={{ color: '#1677ff' }} />
            <Text strong>Profile Buffer 深度解析</Text>
            <Tag color="blue">{profileObis}</Tag>
            <Tag color={srcCfg.color} icon={srcCfg.icon}>{srcCfg.text}</Tag>
            <Text type="secondary" style={{ fontSize: 12 }}>
              ({entryCount} 条记录, {totalFields} 个字段)
            </Text>
          </Space>
        }
        extra={
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => onConfigure && onConfigure(profileObis)}
          >
            编辑配置
          </Button>
        }
      >
        <Table
          size="small"
          columns={matrixColumns}
          dataSource={displayEntries}
          pagination={false}
          rowKey="entry_index"
          scroll={{ x: 'max-content', y: 300 }}
        />
      </Card>
    )
  }

  // ===== 单条记录: 逐字段表格 (行=字段) =====
  const singleColumns = [
    {
      title: '#',
      width: 40,
      render: (_, __, index) => index + 1
    },
    {
      title: 'Class',
      dataIndex: ['capture_object', 'class_id'],
      width: 90,
      render: (val, record) => {
        const co = record.capture_object || {}
        return (
          <Space size="small">
            <Tag color="blue">{co.class_id}</Tag>
            <Text type="secondary" style={{ fontSize: 11 }}>
              {co.class_name || ''}
            </Text>
          </Space>
        )
      }
    },
    {
      title: 'OBIS',
      dataIndex: ['capture_object', 'obis'],
      width: 150,
      render: (val, record) => {
        const co = record.capture_object || {}
        return (
          <Tooltip title={co.obis_name || ''}>
            <Text code style={{ fontSize: 11 }}>{co.obis || '-'}</Text>
          </Tooltip>
        )
      }
    },
    {
      title: '属性',
      dataIndex: ['capture_object', 'attribute_id'],
      width: 60,
      render: (val, record) => {
        const co = record.capture_object || {}
        return (
          <Space size="small">
            <Tag style={{ fontSize: 11 }}>A{co.attribute_id}</Tag>
            <Text type="secondary" style={{ fontSize: 11 }}>
              {co.attribute_name || ''}
            </Text>
          </Space>
        )
      }
    },
    {
      title: '值',
      dataIndex: 'formatted_value',
      ellipsis: true,
      render: (val, record) => {
        const displayVal = formatCellValue(record)
        const unit = record.unit
        return (
          <Space size="small">
            <Text code>{displayVal}</Text>
            {unit && <Tag color="cyan" style={{ fontSize: 11 }}>{unit}</Tag>}
          </Space>
        )
      }
    },
    {
      title: '备注',
      dataIndex: ['capture_object', 'remark'],
      width: 120,
      render: (val) => val ? <Text type="secondary" style={{ fontSize: 11 }}>{val}</Text> : '-'
    }
  ]

  return (
    <Card
      size="small"
      style={{ marginBottom: 12 }}
      title={
        <Space>
          <TableOutlined style={{ color: '#1677ff' }} />
          <Text strong>Profile Buffer 深度解析</Text>
          <Tag color="blue">{profileObis}</Tag>
          <Tag color={srcCfg.color} icon={srcCfg.icon}>
            {srcCfg.text}
          </Tag>
          <Text type="secondary" style={{ fontSize: 12 }}>
            ({totalFields} 个字段)
          </Text>
        </Space>
      }
      extra={
        <Button
          size="small"
          icon={<EditOutlined />}
          onClick={() => onConfigure && onConfigure(profileObis)}
        >
          编辑配置
        </Button>
      }
    >
      <Table
        size="small"
        columns={singleColumns}
        dataSource={firstEntryFields}
        pagination={false}
        rowKey="field_index"
        scroll={{ y: 250 }}
      />
    </Card>
  )
}

export default ProfileBufferTable
