import { useState, useEffect } from 'react'
import {
  Form,
  Input,
  Button,
  Space,
  Table,
  InputNumber,
  Card,
  Row,
  Col,
  Popconfirm,
  message,
  Divider,
  Typography
} from 'antd'
import {
  PlusOutlined,
  DeleteOutlined,
  UpOutlined,
  DownOutlined,
  DatabaseOutlined,
  SaveOutlined
} from '@ant-design/icons'
import usePullStore from '../../store/pullStore.js'

const { Text } = Typography
const { TextArea } = Input

function PresetEditor({ preset, onSave, onClose, onOpenObjectSelector }) {
  const [form] = Form.useForm()
  const [operations, setOperations] = useState([])
  const { updatePreset } = usePullStore()

  useEffect(() => {
    if (preset) {
      form.setFieldsValue({
        name: preset.name,
        description: preset.description
      })
      setOperations(preset.operations || [])
    } else {
      form.resetFields()
      setOperations([])
    }
  }, [preset])

  const handleAddOperation = () => {
    const newOp = {
      class_id: 3,
      obis: '0.0.0.0.0.0',
      attribute_id: 2,
      name: `操作 ${operations.length + 1}`
    }
    setOperations([...operations, newOp])
  }

  const handleAddFromDataModel = () => {
    onOpenObjectSelector && onOpenObjectSelector()
  }

  const handleUpdateOperation = (index, field, value) => {
    const newOps = [...operations]
    newOps[index] = { ...newOps[index], [field]: value }
    setOperations(newOps)
  }

  const handleDeleteOperation = (index) => {
    const newOps = operations.filter((_, i) => i !== index)
    setOperations(newOps)
  }

  const handleMoveUp = (index) => {
    if (index === 0) return
    const newOps = [...operations]
    ;[newOps[index - 1], newOps[index]] = [newOps[index], newOps[index - 1]]
    setOperations(newOps)
  }

  const handleMoveDown = (index) => {
    if (index === operations.length - 1) return
    const newOps = [...operations]
    ;[newOps[index + 1], newOps[index]] = [newOps[index], newOps[index + 1]]
    setOperations(newOps)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      const updatedPreset = {
        ...preset,
        name: values.name,
        description: values.description,
        operations
      }
      updatePreset(preset.id, updatedPreset)
      message.success('预设已保存')
      onSave && onSave(updatedPreset)
    } catch (error) {
      if (error.errorFields) {
        message.error('请填写完整的预设信息')
      }
    }
  }

  const columns = [
    {
      title: '序号',
      key: 'index',
      width: 60,
      render: (_, __, index) => index + 1
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 160,
      render: (text, record, index) => (
        <Input
          size="small"
          value={text}
          onChange={(e) => handleUpdateOperation(index, 'name', e.target.value)}
          placeholder="操作名称"
        />
      )
    },
    {
      title: '类ID',
      dataIndex: 'class_id',
      key: 'class_id',
      width: 90,
      render: (text, record, index) => (
        <InputNumber
          size="small"
          min={0}
          max={255}
          value={text}
          onChange={(val) => handleUpdateOperation(index, 'class_id', val || 0)}
          style={{ width: '100%' }}
        />
      )
    },
    {
      title: 'OBIS 码',
      dataIndex: 'obis',
      key: 'obis',
      width: 180,
      render: (text, record, index) => (
        <Input
          size="small"
          value={text}
          onChange={(e) => handleUpdateOperation(index, 'obis', e.target.value)}
          placeholder="A.B.C.D.E.F"
        />
      )
    },
    {
      title: '属性ID',
      dataIndex: 'attribute_id',
      key: 'attribute_id',
      width: 90,
      render: (text, record, index) => (
        <InputNumber
          size="small"
          min={1}
          max={255}
          value={text}
          onChange={(val) => handleUpdateOperation(index, 'attribute_id', val || 2)}
          style={{ width: '100%' }}
        />
      )
    },
    {
      title: '操作',
      key: 'actions',
      width: 130,
      render: (_, __, index) => (
        <Space size={4}>
          <Button
            size="small"
            type="text"
            icon={<UpOutlined />}
            onClick={() => handleMoveUp(index)}
            disabled={index === 0}
          />
          <Button
            size="small"
            type="text"
            icon={<DownOutlined />}
            onClick={() => handleMoveDown(index)}
            disabled={index === operations.length - 1}
          />
          <Popconfirm
            title="删除此操作？"
            onConfirm={() => handleDeleteOperation(index)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button size="small" type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      )
    }
  ]

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 基本信息 */}
      <Card
        size="small"
        title="基本信息"
        style={{ marginBottom: 12 }}
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="预设名称"
                rules={[{ required: true, message: '请输入预设名称' }]}
                style={{ marginBottom: 0 }}
              >
                <Input placeholder="请输入预设名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="description"
                label="描述"
                style={{ marginBottom: 0 }}
              >
                <TextArea
                  rows={1}
                  placeholder="预设描述（可选）"
                  autoSize={{ minRows: 1, maxRows: 2 }}
                />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Card>

      {/* 操作列表 */}
      <Card
        size="small"
        title={
          <Space>
            <Text strong>操作列表</Text>
            <Text type="secondary">({operations.length} 个操作)</Text>
          </Space>
        }
        extra={
          <Space>
            <Button
              size="small"
              icon={<DatabaseOutlined />}
              onClick={handleAddFromDataModel}
            >
              从数模选择
            </Button>
            <Button
              size="small"
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAddOperation}
            >
              添加操作
            </Button>
          </Space>
        }
        style={{ flex: 1, overflow: 'auto' }}
        bodyStyle={{ padding: 0, height: '100%' }}
      >
        <Table
          dataSource={operations}
          columns={columns}
          rowKey={(record, index) => index}
          size="small"
          pagination={false}
          scroll={{ y: 'calc(100% - 50px)' }}
        />
      </Card>

      {/* 底部操作 */}
      <div
        style={{
          padding: '12px 0',
          borderTop: '1px solid #f0f0f0',
          display: 'flex',
          justifyContent: 'flex-end'
        }}
      >
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" icon={<SaveOutlined />} onClick={handleSave}>
            保存预设
          </Button>
        </Space>
      </div>
    </div>
  )
}

export default PresetEditor
