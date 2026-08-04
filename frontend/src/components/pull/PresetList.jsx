import { List, Button, Space, Typography, Tag, Popconfirm, Empty } from 'antd'
import {
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  CopyOutlined,
  PlusOutlined,
  MobileOutlined
} from '@ant-design/icons'
import usePullStore from '../../store/pullStore.js'

const { Text, Paragraph } = Typography

function PresetList({ onEdit, onExecute, onAdd }) {
  const { presets, deletePreset, addPreset } = usePullStore()

  const handleDelete = (id, e) => {
    e.stopPropagation()
    deletePreset(id)
  }

  const handleCopy = (preset, e) => {
    e.stopPropagation()
    const newPreset = {
      ...preset,
      id: `preset-${Date.now()}`,
      name: `${preset.name} (副本)`
    }
    addPreset(newPreset)
  }

  if (presets.length === 0) {
    return (
      <div style={{ padding: '40px 0' }}>
        <Empty
          description="暂无预设"
          style={{ marginBottom: 16 }}
        />
        <div style={{ textAlign: 'center' }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={onAdd}>
            创建第一个预设
          </Button>
        </div>
      </div>
    )
  }

  return (
    <List
      dataSource={presets}
      renderItem={(preset) => (
        <List.Item
          style={{
            cursor: 'pointer',
            padding: '12px 16px',
            borderBottom: '1px solid #f0f0f0'
          }}
          onClick={() => onEdit && onEdit(preset)}
          actions={[
            <Button
              key="execute"
              type="primary"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={(e) => {
                e.stopPropagation()
                onExecute && onExecute(preset)
              }}
            >
              执行
            </Button>,
            <Button
              key="edit"
              size="small"
              icon={<EditOutlined />}
              onClick={(e) => {
                e.stopPropagation()
                onEdit && onEdit(preset)
              }}
            >
              编辑
            </Button>,
            <Button
              key="copy"
              size="small"
              icon={<CopyOutlined />}
              onClick={(e) => handleCopy(preset, e)}
            >
              复制
            </Button>,
            <Popconfirm
              key="delete"
              title="确定删除这个预设吗？"
              description={`将删除预设 "${preset.name}"`}
              onConfirm={(e) => handleDelete(preset.id, e)}
              okText="删除"
              cancelText="取消"
              okButtonProps={{ danger: true }}
            >
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          ]}
        >
          <List.Item.Meta
            avatar={<MobileOutlined style={{ fontSize: 20, color: '#1677ff' }} />}
            title={
              <Space>
                <Text strong>{preset.name}</Text>
                <Tag color="blue">{preset.operations?.length || 0} 个操作</Tag>
              </Space>
            }
            description={
              <Space direction="vertical" size={2} style={{ width: '100%' }}>
                <Paragraph
                  type="secondary"
                  ellipsis={{ rows: 1 }}
                  style={{ marginBottom: 0 }}
                >
                  {preset.description || '暂无描述'}
                </Paragraph>
                <Space size={8}>
                  {preset.device_name ? (
                    <Tag color="green" style={{ margin: 0 }}>
                      {preset.device_name}
                    </Tag>
                  ) : preset.system_title ? (
                    <Tag color="cyan" style={{ margin: 0, fontFamily: 'monospace' }}>
                      ST: {preset.system_title}
                    </Tag>
                  ) : (
                    <Tag color="default" style={{ margin: 0 }}>
                      未配置设备
                    </Tag>
                  )}
                  {preset.key_type && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      密钥: {preset.key_type}
                    </Text>
                  )}
                </Space>
              </Space>
            }
          />
        </List.Item>
      )}
    />
  )
}

export default PresetList
