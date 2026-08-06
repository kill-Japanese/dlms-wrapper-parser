import { Modal, Table, Input, InputNumber, Button, Space, Select, message, Typography } from 'antd'
import { PlusOutlined, DeleteOutlined, SaveOutlined } from '@ant-design/icons'
import { useState, useEffect, useCallback } from 'react'
import { saveProfileCapture, getProfileCaptureDetail } from '../../services/profileCapture.js'

const { Text } = Typography

// 已知 class 名称映射（与 APDULayer 保持一致）
const CLASS_NAMES = {
  1: 'Data', 3: 'Register', 4: 'Extended Register', 5: 'Demand Register',
  7: 'Profile Generic', 8: 'Clock', 9: 'Script Table', 15: 'Association LN',
  17: 'SAP Assignment', 18: 'Image Transfer', 22: 'Activity Calendar',
  23: 'IEC HDLC Setup', 40: 'Push Setup', 64: 'Security Setup',
  70: 'Disconnect Control'
}

/**
 * Capture Objects 编辑器弹窗
 * 
 * 用于手动配置 Profile Generic (Class 7) 的 capture_objects (属性3)
 * 用户可以添加/编辑/删除 capture object 定义
 */
function CaptureObjectsEditor({ visible, onClose, profileObis, onSuccess }) {
  const [captureObjects, setCaptureObjects] = useState([])
  const [profileName, setProfileName] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  // 加载已有配置
  const loadExistingConfig = useCallback(async () => {
    if (!profileObis) return
    setLoading(true)
    try {
      const detail = await getProfileCaptureDetail(profileObis)
      if (detail && detail.capture_objects) {
        setCaptureObjects(detail.capture_objects.map((co, idx) => ({
          key: idx,
          class_id: co.class_id || 0,
          instance_id: co.instance_id || co.obis || '',
          attribute_id: co.attribute_id || 0,
          data_index: co.data_index || 0,
          remark: co.remark || ''
        })))
        setProfileName(detail.profile_name || '')
      } else {
        setCaptureObjects([])
        setProfileName('')
      }
    } catch {
      setCaptureObjects([])
      setProfileName('')
    } finally {
      setLoading(false)
    }
  }, [profileObis])

  useEffect(() => {
    if (visible && profileObis) {
      loadExistingConfig()
    }
  }, [visible, profileObis, loadExistingConfig])

  // 添加一行
  const handleAdd = () => {
    setCaptureObjects(prev => [...prev, {
      key: Date.now(),
      class_id: 3,
      instance_id: '',
      attribute_id: 2,
      data_index: 0,
      remark: ''
    }])
  }

  // 删除一行
  const handleDelete = (key) => {
    setCaptureObjects(prev => prev.filter(item => item.key !== key))
  }

  // 更新某行某字段
  const handleUpdate = (key, field, value) => {
    setCaptureObjects(prev => prev.map(item =>
      item.key === key ? { ...item, [field]: value } : item
    ))
  }

  // 保存
  const handleSave = async () => {
    if (captureObjects.length === 0) {
      message.warning('请至少添加一个 capture object')
      return
    }
    if (!profileObis) {
      message.error('缺少 Profile OBIS')
      return
    }

    setSaving(true)
    try {
      const objects = captureObjects.map(co => ({
        class_id: co.class_id,
        instance_id: co.instance_id,
        attribute_id: co.attribute_id,
        data_index: co.data_index,
        remark: co.remark
      }))

      await saveProfileCapture(profileObis, objects, profileName, 'manual')
      message.success(`已保存 ${objects.length} 个 capture objects`)
      if (onSuccess) onSuccess()
      onClose()
    } catch (err) {
      message.error('保存失败: ' + (err.message || '未知错误'))
    } finally {
      setSaving(false)
    }
  }

  const columns = [
    {
      title: '#',
      width: 40,
      render: (_, __, index) => index + 1
    },
    {
      title: 'Class ID',
      dataIndex: 'class_id',
      width: 120,
      render: (val, record) => (
        <Select
          size="small"
          style={{ width: '100%' }}
          value={val}
          onChange={v => handleUpdate(record.key, 'class_id', v)}
          showSearch
          optionFilterProp="children"
        >
          {Object.entries(CLASS_NAMES).map(([id, name]) => (
            <Select.Option key={id} value={Number(id)}>
              {id} - {name}
            </Select.Option>
          ))}
        </Select>
      )
    },
    {
      title: 'OBIS',
      dataIndex: 'instance_id',
      width: 180,
      render: (val, record) => (
        <Input
          size="small"
          value={val}
          onChange={e => handleUpdate(record.key, 'instance_id', e.target.value)}
          placeholder="0-0:1.0.0.255"
        />
      )
    },
    {
      title: 'Attr',
      dataIndex: 'attribute_id',
      width: 60,
      render: (val, record) => (
        <InputNumber
          size="small"
          min={0}
          max={255}
          value={val}
          onChange={v => handleUpdate(record.key, 'attribute_id', v || 0)}
          style={{ width: '100%' }}
        />
      )
    },
    {
      title: 'Data Index',
      dataIndex: 'data_index',
      width: 80,
      render: (val, record) => (
        <InputNumber
          size="small"
          min={0}
          value={val}
          onChange={v => handleUpdate(record.key, 'data_index', v || 0)}
          style={{ width: '100%' }}
        />
      )
    },
    {
      title: '备注',
      dataIndex: 'remark',
      render: (val, record) => (
        <Input
          size="small"
          value={val}
          onChange={e => handleUpdate(record.key, 'remark', e.target.value)}
          placeholder="例如：正向有功总电能"
        />
      )
    },
    {
      title: '操作',
      width: 50,
      render: (_, record) => (
        <Button
          size="small"
          type="text"
          danger
          icon={<DeleteOutlined />}
          onClick={() => handleDelete(record.key)}
        />
      )
    }
  ]

  return (
    <Modal
      title={`Capture Objects 配置 - ${profileObis || ''}`}
      open={visible}
      onCancel={onClose}
      width={850}
      footer={[
        <Button key="cancel" onClick={onClose}>取消</Button>,
        <Button key="save" type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>
          保存配置
        </Button>
      ]}
    >
      <Space style={{ marginBottom: 12, width: '100%' }} direction="vertical">
        <Space>
          <Text strong>Profile 名称:</Text>
          <Input
            size="small"
            style={{ width: 250 }}
            value={profileName}
            onChange={e => setProfileName(e.target.value)}
            placeholder="例如：负荷记录1"
          />
        </Space>
        <Text type="secondary" style={{ fontSize: 12 }}>
          配置 Profile Generic (Class 7) 的 capture_objects (属性3)。
          每个 capture object 定义了 buffer 中对应字段的含义。
          配置保存后，下次解析 DataNotification 时将自动使用此配置解析 Profile buffer。
        </Text>
      </Space>

      <Table
        size="small"
        columns={columns}
        dataSource={captureObjects}
        pagination={false}
        rowKey="key"
        loading={loading}
        scroll={{ y: 350 }}
        footer={() => (
          <Button type="dashed" block icon={<PlusOutlined />} onClick={handleAdd}>
            添加 Capture Object
          </Button>
        )}
      />
    </Modal>
  )
}

export default CaptureObjectsEditor
