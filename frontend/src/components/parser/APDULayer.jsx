import { Tree, Typography, Tag, Space, Empty, Select, Row, Col, Card, Table, Tooltip } from 'antd'
import {
  FileTextOutlined,
  DatabaseOutlined,
  ApiOutlined,
  NumberOutlined,
  FontSizeOutlined,
  CheckCircleOutlined,
  SettingOutlined,
  InfoCircleOutlined,
  BulbOutlined,
  ClockCircleOutlined,
  ProfileOutlined
} from '@ant-design/icons'
import { useState, useMemo } from 'react'

const { Text } = Typography
const { Option } = Select

// 数据类型对应的图标
const typeIcons = {
  structure: <DatabaseOutlined style={{ color: '#1677ff' }} />,
  array: <DatabaseOutlined style={{ color: '#52c41a' }} />,
  'long-unsigned': <NumberOutlined style={{ color: '#faad14' }} />,
  'double-long-unsigned': <NumberOutlined style={{ color: '#faad14' }} />,
  unsigned: <NumberOutlined style={{ color: '#faad14' }} />,
  integer: <NumberOutlined style={{ color: '#faad14' }} />,
  'long-integer': <NumberOutlined style={{ color: '#faad14' }} />,
  'double-long-integer': <NumberOutlined style={{ color: '#faad14' }} />,
  long: <NumberOutlined style={{ color: '#faad14' }} />,
  'octet-string': <FontSizeOutlined style={{ color: '#722ed1' }} />,
  string: <FontSizeOutlined style={{ color: '#722ed1' }} />,
  'visible-string': <FontSizeOutlined style={{ color: '#722ed1' }} />,
  'utf8-string': <FontSizeOutlined style={{ color: '#722ed1' }} />,
  boolean: <CheckCircleOutlined style={{ color: '#13c2c2' }} />,
  'null-data': <ApiOutlined style={{ color: '#8c8c8c' }} />,
  enum: <NumberOutlined style={{ color: '#eb2f96' }} />,
  'date-time': <ClockCircleOutlined style={{ color: '#13c2c2' }} />,
  date: <ClockCircleOutlined style={{ color: '#13c2c2' }} />,
  time: <ClockCircleOutlined style={{ color: '#13c2c2' }} />,
  default: <FileTextOutlined style={{ color: '#8c8c8c' }} />
}

// 已知 class 名称映射
const CLASS_NAMES = {
  1: 'Data',
  3: 'Register',
  4: 'Extended Register',
  5: 'Demand Register',
  6: 'Register Activation',
  7: 'Profile Generic',
  8: 'Clock',
  9: 'Script Table',
  10: 'Schedule',
  11: 'Special Days Table',
  15: 'Association LN',
  17: 'SAP Assignment',
  18: 'Image Transfer',
  19: 'IEC Local Port Setup',
  20: 'IEC HDLC Setup',
  21: 'IEC Twisted Pair Setup',
  22: 'TCP UDP Setup',
  23: 'IPv4 Setup',
  24: 'IPv6 Setup',
  25: 'PPP Setup',
  26: 'GPRS Modem Setup',
  27: 'SMTP Setup',
  28: 'GNSS Setup',
  29: 'MBus Client Setup',
  30: 'MBus Slave Setup',
  31: 'PSTN Modem Setup',
  32: 'Auto Answer',
  33: 'Auto Connect',
  34: 'Disconnect Control',
  35: 'Limiter',
  36: 'MBus Diagnostic',
  37: 'Register Monitor',
  38: 'Utility Tables',
  39: 'Communication Port Protection',
  40: 'Push Setup',
  41: 'Message Handler',
  42: 'Parameter Monitor',
  43: 'Wireless Mode Q channel',
  44: 'MBUS Slave',
  45: 'Wireless Mode S-FSK',
  46: 'Wireless Mode S-FSK HHW',
  47: 'GPRS Diagnostic',
  48: 'Wireless S-FSK HHW',
  49: 'PLL',
  50: 'Tariff Plan',
  51: 'Communication Port Protection',
  52: 'Account',
  53: 'Credit',
  54: 'Payment',
  55: 'Token',
  56: 'Operator',
  57: 'Currency',
  58: 'Special Days Table',
  59: 'Demand Register Extended',
  60: 'Register Extended',
  61: 'Status Mapping',
  62: 'Security Setup',
  63: 'Security Suite',
  64: 'Security Setup',
  65: 'Tariff Configuration',
  66: 'Time Zone',
  67: 'Calendar',
  68: 'Action Schedule',
  69: 'Schedule Table',
  70: 'Disconnect Control',
  71: 'Limiter',
  72: 'Service',
  73: 'Register Table',
  74: 'Profile Table',
  75: 'Device Table',
  76: 'Program',
  77: 'Program Invocation',
  78: 'Activity Calendar',
  79: 'DLMS Port',
  80: 'Wireless Modem',
  81: 'Wireless Diagnostic',
  82: 'Wireless Status',
}

// Clock 属性名称映射
const CLOCK_ATTRIBUTES = {
  1: 'logical_name',
  2: 'time',
  3: 'time_zone',
  4: 'status',
  5: 'daylights_savings_begin',
  6: 'daylights_savings_end',
  7: 'daylights_savings_deviation',
  8: 'daylights_savings_enabled',
  9: 'clock_base',
}

// 通用属性名映射（常用 class）
const CLASS_ATTRIBUTE_NAMES = {
  1: { 1: 'logical_name', 2: 'value' },
  3: { 1: 'logical_name', 2: 'value', 3: 'scaler_unit', 4: 'status', 5: 'capture_time' },
  4: { 1: 'logical_name', 2: 'value', 3: 'scaler_unit', 4: 'status', 5: 'capture_time', 6: 'capture_period' },
  5: { 1: 'logical_name', 2: 'current_value', 3: 'scaler_unit', 4: 'status', 5: 'capture_time', 6: 'last_average_value', 7: 'last_average_start_time', 8: 'last_average_end_time', 9: 'last_average_period' },
  7: { 1: 'logical_name', 2: 'buffer', 3: 'capture_objects', 4: 'capture_period', 5: 'sort_method', 6: 'object_list', 7: 'profile_entries', 8: 'profile_entries_in_use', 9: 'entry_descriptions' },
  8: CLOCK_ATTRIBUTES,
  15: { 1: 'logical_name', 2: 'object_list', 3: 'associated_partners_id', 4: 'application_context_name', 5: 'xDLMS_context_info', 6: 'authentication_mechanism_name', 7: 'secret', 8: 'association_status', 9: 'security_setup_reference', 10: 'user_list', 11: 'current_user', 12: 'user_list_configuration' },
  40: { 1: 'logical_name', 2: 'push_object_list', 3: 'send_destination_and_method', 4: 'communication_window', 5: 'repetition_delay', 6: 'number_of_retries', 7: 'push_client_setup_reference' },
  64: { 1: 'logical_name', 2: 'security_policy', 3: 'security_suite', 4: 'client_system_title', 5: 'server_system_title', 6: 'certificates' },
}

// 获取属性名称
function getAttributeName(classId, attrId) {
  const classAttrs = CLASS_ATTRIBUTE_NAMES[classId]
  if (classAttrs && classAttrs[attrId]) {
    return classAttrs[attrId]
  }
  return `Attribute ${attrId}`
}

// 尝试将 octet-string 解析为 date-time
function tryParseDateTimeFromOctetString(value) {
  if (!value || typeof value !== 'string') return null
  
  // 移除可能的引号和空格
  let hexStr = value.replace(/"/g, '').replace(/\s/g, '')
  
  // 检查是否是 24 个十六进制字符（12 字节）
  if (hexStr.length !== 24) return null
  
  try {
    const bytes = new Uint8Array(hexStr.match(/.{1,2}/g).map(byte => parseInt(byte, 16)))
    
    const year = (bytes[0] << 8) | bytes[1]
    const month = bytes[2]
    const day = bytes[3]
    // const dayOfWeek = bytes[4]
    const hour = bytes[5]
    const minute = bytes[6]
    const second = bytes[7]
    const hundredths = bytes[8]
    // const deviation = (bytes[9] << 8) | bytes[10]
    // const status = bytes[11]
    
    // 合理性检查
    if (year < 2000 || year > 2100) return null
    if (month < 1 || month > 12) return null
    if (day < 1 || day > 31) return null
    if (hour > 23) return null
    if (minute > 59) return null
    if (second > 59) return null
    
    return {
      year, month, day, hour, minute, second, hundredths,
      iso: `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')} ${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}:${String(second).padStart(2, '0')}.${String(hundredths).padStart(2, '0')}`
    }
  } catch {
    return null
  }
}

// 格式化值显示
function formatValue(item) {
  if (item.value === undefined || item.value === null) return 'null'
  
  // 如果是结构或数组，返回元素个数
  if (Array.isArray(item.value)) {
    return `[${item.value.length} elements]`
  }
  
  if (typeof item.value === 'object') {
    // 如果是 date-time 对象，显示格式化字符串
    if (item.value.iso) {
      return item.value.iso
    }
    return JSON.stringify(item.value)
  }
  
  return String(item.value)
}

// 将 CosemDataItem 转换为树形结构数据
function convertItemsToTreeData(items, parentKey = 'items') {
  if (!items || items.length === 0) return []
  
  return items.map((item, index) => {
    const key = `${parentKey}-${index}`
    const classId = item.class_id
    const className = CLASS_NAMES[classId] || `Class ${classId}`
    const attrId = item.attribute_id
    const attrName = getAttributeName(classId, attrId)
    const dataType = item.data_type || item.type || 'unknown'
    
    // 对于 octet-string 类型，尝试解析为 date-time
    let displayValue = item.value
    let displayType = dataType
    let parsedDateTime = null
    
    if (dataType === 'octet-string' || dataType === 'octet_string') {
      // 尝试解析为 date-time（12 字节 octet-string）
      parsedDateTime = tryParseDateTimeFromOctetString(item.value)
      if (parsedDateTime) {
        displayType = 'date-time'
        displayValue = parsedDateTime
      }
    }
    
    // 如果值是数组或对象（结构），递归处理
    if (Array.isArray(item.value)) {
      // 检查是否是结构数组（每个元素都是对象）
      const childItems = item.value.map((child, childIdx) => ({
        class_id: 0,
        obis: '',
        attribute_id: 0,
        data_type: child.type || typeof child.value,
        type: child.type || typeof child.value,
        value: child.value !== undefined ? child.value : child,
        name: child.name || `Element ${childIdx}`
      }))
      
      return {
        key,
        title: (
          <Space size="small" wrap>
            {typeIcons[displayType] || typeIcons.default}
            <Tag color="blue" style={{ fontSize: 11 }}>
              {classId}
            </Tag>
            <Text strong>{className}</Text>
            <Text code style={{ fontSize: 11 }}>{item.obis}</Text>
            <Tag style={{ fontSize: 11 }}>Attr {attrId}</Tag>
            <Text type="secondary" style={{ fontSize: 11 }}>{attrName}</Text>
            <Tag color="green" style={{ fontSize: 11 }}>
              {displayType}
            </Tag>
            <Text type="secondary" style={{ fontSize: 11 }}>
              ({item.value.length} 项)
            </Text>
          </Space>
        ),
        icon: typeIcons[displayType] || typeIcons.default,
        children: childItems.length > 0 ? convertNestedToTreeData(childItems, key) : [],
      }
    }
    
    // 叶子节点
    return {
      key,
      title: (
        <Space size="small" wrap>
          {typeIcons[displayType] || typeIcons.default}
          <Tag color="blue" style={{ fontSize: 11 }}>
            {classId}
          </Tag>
          <Text strong>{className}</Text>
          <Tooltip title={item.obis}>
            <Text code style={{ fontSize: 11, maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', display: 'inline-block', verticalAlign: 'bottom' }}>
              {item.obis}
            </Text>
          </Tooltip>
          <Tag style={{ fontSize: 11 }}>Attr {attrId}</Tag>
          <Text type="secondary" style={{ fontSize: 11 }}>{attrName}</Text>
          <Tag color={parsedDateTime ? 'cyan' : 'default'} style={{ fontSize: 11 }}>
            {displayType}
          </Tag>
          <Text type="secondary" style={{ fontSize: 12 }}>=</Text>
          <Text code>{formatValue({ ...item, value: displayValue })}</Text>
        </Space>
      ),
      icon: typeIcons[displayType] || typeIcons.default,
      isLeaf: true,
    }
  })
}

// 嵌套结构转树形数据
function convertNestedToTreeData(items, parentKey) {
  return items.map((item, index) => {
    const key = `${parentKey}-${index}`
    const dataType = item.data_type || item.type || 'unknown'
    const isContainer = Array.isArray(item.value) && item.value.length > 0 && 
      typeof item.value[0] === 'object' && item.value[0] !== null
    
    if (isContainer) {
      const childItems = item.value.map((child, childIdx) => ({
        class_id: 0,
        obis: '',
        attribute_id: 0,
        data_type: child.type || typeof child.value,
        type: child.type || typeof child.value,
        value: child.value !== undefined ? child.value : child,
        name: child.name || `Element ${childIdx}`
      }))
      
      return {
        key,
        title: (
          <Space size="small">
            {typeIcons[dataType] || typeIcons.default}
            <Text>{item.name || `Item ${index}`}</Text>
            <Tag color="blue" style={{ fontSize: 11 }}>{dataType}</Tag>
            <Text type="secondary" style={{ fontSize: 11 }}>
              ({item.value.length} 项)
            </Text>
          </Space>
        ),
        icon: typeIcons[dataType] || typeIcons.default,
        children: convertNestedToTreeData(childItems, key),
      }
    }
    
    return {
      key,
      title: (
        <Space size="small" wrap>
          {typeIcons[dataType] || typeIcons.default}
          <Text>{item.name || `Item ${index}`}</Text>
          <Tag style={{ fontSize: 11 }}>{dataType}</Tag>
          <Text type="secondary" style={{ fontSize: 12 }}>=</Text>
          <Text code>{formatValue(item)}</Text>
        </Space>
      ),
      icon: typeIcons[dataType] || typeIcons.default,
      isLeaf: true,
    }
  })
}

function APDULayer({ data, dataModel }) {
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

  const treeData = useMemo(() => {
    if (!items || items.length === 0) return []
    return convertItemsToTreeData(items)
  }, [items])

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
      title: 'Class',
      dataIndex: 'class_id',
      key: 'class_id',
      width: 100,
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
      width: 150,
      render: (val) => <Text code style={{ fontSize: 11 }}>{val}</Text>
    },
    {
      title: 'Attr',
      dataIndex: 'attribute_id',
      key: 'attribute_id',
      width: 50,
    },
    {
      title: 'Data Index',
      dataIndex: 'data_index',
      key: 'data_index',
      width: 80,
      render: (val) => val !== undefined && val !== null ? val : '-'
    },
  ]

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
                  自动识别: {push_setup_version_name || '未知'}
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
            maxHeight: 450,
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
