import { useState, useMemo } from 'react'
import {
  Modal,
  Input,
  List,
  Empty,
  Tag,
  Space,
  Typography,
  Select,
  Row,
  Col,
  Button
} from 'antd'
import { SearchOutlined, DatabaseOutlined } from '@ant-design/icons'
import useDataModelStore from '../../store/datamodelStore.js'

const { Text } = Typography

// 模拟数模对象数据（与 DataModelPage 保持一致）
const mockObjects = [
  { id: 1, obis: '1.0.1.8.0.255', name: '有功总电能（正向）', class: 3, attributes: 6 },
  { id: 2, obis: '1.0.2.8.0.255', name: '有功总电能（反向）', class: 3, attributes: 6 },
  { id: 3, obis: '1.0.3.8.0.255', name: '无功总电能（正向）', class: 3, attributes: 6 },
  { id: 4, obis: '1.0.4.8.0.255', name: '无功总电能（反向）', class: 3, attributes: 6 },
  { id: 5, obis: '1.0.1.7.0.255', name: '有功功率', class: 1, attributes: 3 },
  { id: 6, obis: '1.0.32.7.0.255', name: '电压', class: 1, attributes: 3 },
  { id: 7, obis: '1.0.31.7.0.255', name: '电流', class: 1, attributes: 3 },
  { id: 8, obis: '1.0.13.7.0.255', name: '功率因数', class: 1, attributes: 3 },
  { id: 9, obis: '0.0.1.0.0.255', name: '设备地址', class: 12, attributes: 2 },
  { id: 10, obis: '0.0.96.1.0.255', name: '表号', class: 0, attributes: 2 },
  { id: 11, obis: '0.0.1.0.9.255', name: '时钟', class: 8, attributes: 3 },
  { id: 12, obis: '1.0.0.2.0.255', name: '铭牌信息', class: 1, attributes: 3 },
  { id: 13, obis: '0.0.94.91.0.255', name: '制造厂商', class: 12, attributes: 2 },
  { id: 14, obis: '1.0.21.7.0.255', name: 'A相电压', class: 1, attributes: 3 },
  { id: 15, obis: '1.0.22.7.0.255', name: 'B相电压', class: 1, attributes: 3 },
  { id: 16, obis: '1.0.23.7.0.255', name: 'C相电压', class: 1, attributes: 3 },
  { id: 17, obis: '1.0.33.7.0.255', name: 'A相电流', class: 1, attributes: 3 },
  { id: 18, obis: '1.0.34.7.0.255', name: 'B相电流', class: 1, attributes: 3 },
  { id: 19, obis: '1.0.35.7.0.255', name: 'C相电流', class: 1, attributes: 3 },
  { id: 20, obis: '1.0.81.7.0.255', name: '频率', class: 1, attributes: 3 },
]

// 类ID名称映射
const classNames = {
  0: 'Data',
  1: 'Register',
  3: 'Extended Register',
  8: 'Clock',
  9: 'Script',
  12: 'Profile',
  15: 'Association LN',
  17: 'SAP Assignment',
  19: 'Image Transfer',
  20: 'IO Control',
  21: 'Single Action Schedule',
  22: 'Schedule',
  23: 'Special Days',
  24: 'Clock Base',
  30: 'Push Setup',
  33: 'Capture Object',
  40: 'Register Monitor',
  41: 'Action Schedule',
  42: 'Register Table',
  47: 'Demand Register',
  70: 'Disconnect Control',
  71: 'Limiter',
  72: 'Modem Configuration',
  100: 'DLMS Server',
  101: 'IEC Local Port Setup',
  102: 'IEC HDLC Setup',
  103: 'IEC Twisted Pair Setup',
  104: 'Utility Tables',
  105: 'Modem',
  106: 'Auto Answer',
  107: 'Auto Connect',
  111: 'Security Setup',
  112: 'Parameter Monitor',
  113: 'Wireless MODEM',
  115: 'M-Bus Client',
  116: 'M-Bus Slave',
  117: 'PSTN Diagnostic',
  118: 'PSTN Auto Answer',
  119: 'GPRS Modem',
  122: 'SMTP Client',
  123: 'Diagnostic',
  124: 'IP Configuration',
  125: 'TCP UDP Setup',
  129: 'Disconnect Control'
}

function ObjectSelector({ visible, onClose, onSelect, multiSelect = true }) {
  const [searchQuery, setSearchQuery] = useState('')
  const [classFilter, setClassFilter] = useState(null)
  const [selectedItems, setSelectedItems] = useState([])

  // 获取所有类ID
  const classIds = useMemo(() => {
    const ids = [...new Set(mockObjects.map((obj) => obj.class))].sort((a, b) => a - b)
    return ids
  }, [])

  // 过滤对象
  const filteredObjects = useMemo(() => {
    return mockObjects.filter((obj) => {
      // 类过滤
      if (classFilter !== null && classFilter !== undefined && classFilter !== '') {
        if (obj.class !== classFilter) return false
      }
      // 搜索过滤
      if (searchQuery) {
        const q = searchQuery.toLowerCase()
        return (
          obj.obis.toLowerCase().includes(q) ||
          obj.name.toLowerCase().includes(q) ||
          String(obj.class).includes(q)
        )
      }
      return true
    })
  }, [searchQuery, classFilter])

  const handleSelect = (obj) => {
    if (multiSelect) {
      const idx = selectedItems.findIndex((item) => item.id === obj.id)
      if (idx >= 0) {
        setSelectedItems(selectedItems.filter((item) => item.id !== obj.id))
      } else {
        setSelectedItems([...selectedItems, obj])
      }
    } else {
      // 单选，直接确认
      handleConfirm([obj])
    }
  }

  const handleConfirm = (items = selectedItems) => {
    if (items.length === 0) {
      return
    }
    // 转换为操作项格式
    const operations = items.map((obj) => ({
      class_id: obj.class,
      obis: obj.obis,
      attribute_id: 2,
      name: obj.name
    }))
    onSelect && onSelect(operations)
    setSelectedItems([])
    setSearchQuery('')
    setClassFilter(null)
  }

  const handleCancel = () => {
    setSelectedItems([])
    setSearchQuery('')
    setClassFilter(null)
    onClose && onClose()
  }

  const isSelected = (obj) => {
    return selectedItems.some((item) => item.id === obj.id)
  }

  return (
    <Modal
      title={
        <Space>
          <DatabaseOutlined />
          <span>从数模选择对象</span>
          {multiSelect && selectedItems.length > 0 && (
            <Tag color="blue">已选 {selectedItems.length}</Tag>
          )}
        </Space>
      }
      open={visible}
      onCancel={handleCancel}
      width={720}
      footer={[
        <Button key="cancel" onClick={handleCancel}>
          取消
        </Button>,
        <Button
          key="confirm"
          type="primary"
          onClick={() => handleConfirm()}
          disabled={selectedItems.length === 0}
        >
          确认添加 ({selectedItems.length})
        </Button>
      ]}
    >
      {/* 搜索和筛选 */}
      <div style={{ marginBottom: 16 }}>
        <Row gutter={12}>
          <Col span={16}>
            <Input
              placeholder="搜索 OBIS 码或名称..."
              prefix={<SearchOutlined />}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              allowClear
            />
          </Col>
          <Col span={8}>
            <Select
              placeholder="按类筛选"
              allowClear
              style={{ width: '100%' }}
              value={classFilter}
              onChange={setClassFilter}
              options={classIds.map((cid) => ({
                value: cid,
                label: `Class ${cid} - ${classNames[cid] || 'Unknown'}`
              }))}
            />
          </Col>
        </Row>
      </div>

      {/* 对象列表 */}
      <div
        style={{
          maxHeight: 400,
          overflow: 'auto',
          border: '1px solid #f0f0f0',
          borderRadius: 6
        }}
      >
        {filteredObjects.length > 0 ? (
          <List
            size="small"
            dataSource={filteredObjects}
            renderItem={(item) => (
              <List.Item
                style={{
                  cursor: 'pointer',
                  padding: '10px 16px',
                  background: isSelected(item) ? '#e6f4ff' : 'transparent',
                  borderBottom: '1px solid #f0f0f0'
                }}
                onClick={() => handleSelect(item)}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Text strong>{item.name}</Text>
                      <Tag color="blue">Class {item.class}</Tag>
                    </Space>
                  }
                  description={<Text code>{item.obis}</Text>}
                />
              </List.Item>
            )}
          />
        ) : (
          <Empty
            description="未找到匹配的对象"
            style={{ padding: '40px 0' }}
          />
        )}
      </div>

      {multiSelect && selectedItems.length > 0 && (
        <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid #f0f0f0' }}>
          <Text type="secondary">已选择 {selectedItems.length} 个对象，点击确认添加到预设</Text>
        </div>
      )}
    </Modal>
  )
}

export default ObjectSelector
