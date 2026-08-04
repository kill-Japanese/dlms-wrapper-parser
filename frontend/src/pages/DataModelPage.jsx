import { useState } from 'react'
import { Row, Col, Card, Button, Input, List, Empty, Space, Typography, Tag, Upload, message } from 'antd'
import {
  UploadOutlined,
  SearchOutlined,
  DatabaseOutlined,
  ThunderboltOutlined
} from '@ant-design/icons'
import useDataModelStore from '../store/datamodelStore.js'

const { Title, Text } = Typography

// 模拟数据
const mockObjects = [
  { id: 1, obis: '1.0.1.8.0.255', name: '有功总电能', class: 3, attributes: 6 },
  { id: 2, obis: '1.0.2.8.0.255', name: '有功总电能（反向）', class: 3, attributes: 6 },
  { id: 3, obis: '1.0.1.7.0.255', name: '有功功率', class: 1, attributes: 3 },
  { id: 4, obis: '0.0.1.0.0.255', name: '设备地址', class: 12, attributes: 2 },
  { id: 5, obis: '0.0.96.1.0.255', name: '表号', class: 0, attributes: 2 },
  { id: 6, obis: '1.0.32.7.0.255', name: '电压', class: 1, attributes: 3 },
  { id: 7, obis: '1.0.31.7.0.255', name: '电流', class: 1, attributes: 3 },
  { id: 8, obis: '0.0.1.0.9.255', name: '时钟', class: 8, attributes: 3 }
]

function DataModelPage() {
  const { objects, selectedObject, searchQuery, setSelectedObject, setSearchQuery } = useDataModelStore()
  const [uploading, setUploading] = useState(false)

  // 使用模拟数据
  const displayObjects = mockObjects.filter(
    (obj) =>
      obj.obis.toLowerCase().includes(searchQuery.toLowerCase()) ||
      obj.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleUpload = (file) => {
    setUploading(true)
    // 模拟上传
    setTimeout(() => {
      message.success(`文件 "${file.name}" 上传成功`)
      setUploading(false)
    }, 1000)
    return false // 阻止自动上传
  }

  const handleSelectObject = (obj) => {
    setSelectedObject(obj)
  }

  return (
    <div className="page-container">
      <Card
        title={
          <Space>
            <DatabaseOutlined />
            <Title level={5} style={{ margin: 0 }}>
              数据模型管理
            </Title>
          </Space>
        }
        extra={
          <Upload beforeUpload={handleUpload} showUploadList={false}>
            <Button type="primary" icon={<UploadOutlined />} loading={uploading}>
              上传数模
            </Button>
          </Upload>
        }
        style={{ height: '100%' }}
        bodyStyle={{ height: 'calc(100% - 57px)', padding: 0 }}
      >
        <Row style={{ height: '100%' }}>
          {/* 左侧对象列表 */}
          <Col span={10} style={{ height: '100%', borderRight: '1px solid #f0f0f0' }}>
            <div style={{ padding: 12 }}>
              <Input
                placeholder="搜索 OBIS 码或名称..."
                prefix={<SearchOutlined />}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                allowClear
              />
            </div>
            <div style={{ overflow: 'auto', height: 'calc(100% - 56px)' }}>
              {displayObjects.length > 0 ? (
                <List
                  dataSource={displayObjects}
                  renderItem={(item) => (
                    <List.Item
                      style={{
                        cursor: 'pointer',
                        padding: '12px 16px',
                        background: selectedObject?.id === item.id ? '#e6f4ff' : 'transparent',
                        borderLeft: selectedObject?.id === item.id ? '3px solid #1677ff' : '3px solid transparent'
                      }}
                      onClick={() => handleSelectObject(item)}
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
                <Empty description="暂无对象" style={{ marginTop: 60 }} />
              )}
            </div>
          </Col>

          {/* 右侧对象详情 */}
          <Col span={14} style={{ height: '100%', overflow: 'auto' }}>
            {selectedObject ? (
              <div style={{ padding: 16 }}>
                <Space direction="vertical" size="large" style={{ width: '100%' }}>
                  <div>
                    <Title level={5} style={{ marginBottom: 8 }}>
                      基本信息
                    </Title>
                    <Space direction="vertical" size="small">
                      <Space>
                        <Text type="secondary">OBIS 码:</Text>
                        <Text code copyable>{selectedObject.obis}</Text>
                      </Space>
                      <Space>
                        <Text type="secondary">名称:</Text>
                        <Text>{selectedObject.name}</Text>
                      </Space>
                      <Space>
                        <Text type="secondary">接口类:</Text>
                        <Tag color="blue">Class {selectedObject.class}</Tag>
                      </Space>
                      <Space>
                        <Text type="secondary">属性数量:</Text>
                        <Text>{selectedObject.attributes}</Text>
                      </Space>
                    </Space>
                  </div>

                  <div>
                    <Title level={5} style={{ marginBottom: 8 }}>
                      属性列表
                    </Title>
                    <List
                      size="small"
                      bordered
                      dataSource={Array.from({ length: selectedObject.attributes }, (_, i) => ({
                        id: i + 1,
                        name: `Attribute ${i + 1}`
                      }))}
                      renderItem={(attr) => (
                        <List.Item>
                          <Space>
                            <Tag>#{attr.id}</Tag>
                            <Text>{attr.name}</Text>
                          </Space>
                        </List.Item>
                      )}
                    />
                  </div>

                  <div>
                    <Title level={5} style={{ marginBottom: 8 }}>
                      方法列表
                    </Title>
                    <List
                      size="small"
                      bordered
                      dataSource={[
                        { id: 1, name: 'read' },
                        { id: 2, name: 'write' }
                      ]}
                      renderItem={(method) => (
                        <List.Item>
                          <Space>
                            <Tag color="green">#{method.id}</Tag>
                            <Text>{method.name}</Text>
                          </Space>
                        </List.Item>
                      )}
                    />
                  </div>
                </Space>
              </div>
            ) : (
              <Empty
                image={<DatabaseOutlined style={{ fontSize: 64, color: '#d9d9d9' }} />}
                description="请选择一个对象查看详情"
                style={{ marginTop: 100 }}
              />
            )}
          </Col>
        </Row>
      </Card>
    </div>
  )
}

export default DataModelPage
