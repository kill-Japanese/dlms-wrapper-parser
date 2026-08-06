import { useState, useEffect } from 'react'
import {
  Row,
  Col,
  Card,
  Button,
  Space,
  Typography,
  Badge,
  Tag,
  List,
  Input,
  Timeline,
  Empty,
  Tabs,
  Statistic,
  Divider,
  message,
  Select,
  Switch,
  InputNumber,
  Tooltip,
  Popconfirm,
  Modal,
  Form
} from 'antd'
import {
  ThunderboltOutlined,
  PlayCircleOutlined,
  StopOutlined,
  SendOutlined,
  DesktopOutlined,
  RocketOutlined,
  SettingOutlined,
  EditOutlined,
  ReloadOutlined,
  SaveOutlined,
  CheckOutlined,
  CloseOutlined,
  PlusOutlined,
  DeleteOutlined,
  TableOutlined,
  ProfileOutlined
} from '@ant-design/icons'
import useStreamStore from '../store/streamStore.js'
import {
  getTcpStatus,
  getTcpConfig,
  updateTcpConfig,
  startTcpServer,
  stopTcpServer,
  restartTcpServer,
  getTcpClients,
  renameDevice,
  sendTcpData
} from '../services/streamApi.js'
import {
  getProfileCaptureList,
  deleteProfileCapture
} from '../services/profileCapture.js'
import CaptureObjectsEditor from '../components/parser/CaptureObjectsEditor.jsx'

const { Title, Text } = Typography
const { TextArea } = Input
const { Option } = Select

function StreamPage() {
  const {
    tcpStatus,
    tcpConfig,
    connectedDevices,
    frames,
    selectedFrameId,
    sendPanel,
    setTcpStatus,
    setTcpConfig,
    setDevices,
    addDevice,
    updateDevice,
    removeDevice,
    renameDevice: renameDeviceInStore,
    selectFrame,
    setSendPanel,
    addFrame
  } = useStreamStore()

  const [selectedFrame, setSelectedFrame] = useState(null)
  const [configPanelVisible, setConfigPanelVisible] = useState(false)
  const [editingDevice, setEditingDevice] = useState(null)
  const [editingName, setEditingName] = useState('')
  const [configForm] = Form.useForm()
  const [configSaving, setConfigSaving] = useState(false)
  const [loadingDevices, setLoadingDevices] = useState(false)

  // Capture Objects 管理状态
  const [activeTab, setActiveTab] = useState('tcp')
  const [captureProfiles, setCaptureProfiles] = useState([])
  const [loadingProfiles, setLoadingProfiles] = useState(false)
  const [editorVisible, setEditorVisible] = useState(false)
  const [editorObis, setEditorObis] = useState('')
  const [addProfileModalVisible, setAddProfileModalVisible] = useState(false)
  const [newProfileObis, setNewProfileObis] = useState('')

  // 初始化：加载配置和状态
  useEffect(() => {
    loadTcpStatus()
    loadTcpConfigFromServer()
  }, [])

  // 加载 Capture Objects 配置列表
  const loadCaptureProfiles = async () => {
    setLoadingProfiles(true)
    try {
      const result = await getProfileCaptureList()
      setCaptureProfiles(Array.isArray(result) ? result : [])
    } catch (e) {
      console.log('获取Capture Objects列表失败:', e.message)
      setCaptureProfiles([])
    } finally {
      setLoadingProfiles(false)
    }
  }

  // 切换到 Capture Objects 标签时加载数据
  useEffect(() => {
    if (activeTab === 'capture') {
      loadCaptureProfiles()
    }
  }, [activeTab])

  // 打开编辑器
  const handleOpenEditor = (obis) => {
    setEditorObis(obis)
    setEditorVisible(true)
  }

  // 编辑器保存成功后刷新列表
  const handleEditorSuccess = () => {
    loadCaptureProfiles()
  }

  // 删除配置
  const handleDeleteProfile = async (obis) => {
    try {
      await deleteProfileCapture(obis)
      message.success(`已删除 ${obis} 的配置`)
      loadCaptureProfiles()
    } catch (e) {
      message.error(`删除失败: ${e.message}`)
    }
  }

  // 添加新 Profile
  const handleAddProfile = () => {
    const obis = newProfileObis.trim()
    if (!obis) {
      message.warning('请输入 Profile OBIS')
      return
    }
    setAddProfileModalVisible(false)
    setNewProfileObis('')
    handleOpenEditor(obis)
  }

  // 加载 TCP 状态
  const loadTcpStatus = async () => {
    try {
      const status = await getTcpStatus()
      if (status?.running !== undefined) {
        setTcpStatus(status.running ? 'running' : 'stopped')
        setTcpConfig({
          port: status.port,
          protocol: status.protocol
        })
      }
    } catch (e) {
      console.log('获取TCP状态失败:', e.message)
    }
  }

  // 从服务器加载配置
  const loadTcpConfigFromServer = async () => {
    try {
      const result = await getTcpConfig()
      if (result?.config) {
        setTcpConfig(result.config)
      }
    } catch (e) {
      console.log('获取TCP配置失败，使用本地配置:', e.message)
    }
  }

  // 加载设备列表
  const loadDevices = async () => {
    if (tcpStatus !== 'running') return
    setLoadingDevices(true)
    try {
      const result = await getTcpClients()
      if (result?.devices) {
        // 转换为前端格式
        const devices = result.devices.map((d) => ({
          system_title: d.system_title,
          device_name: d.device_name,
          ip: d.client_ip,
          port: d.client_port,
          connection_id: d.connection_id,
          connected: d.status === 'connected',
          last_seen: d.last_seen || d.last_frame_time,
          connected_at: d.connected_at,
          frames_received: d.frames_received
        }))
        setDevices(devices)
      }
    } catch (e) {
      console.log('获取设备列表失败:', e.message)
    } finally {
      setLoadingDevices(false)
    }
  }

  // 当服务器运行时，定期刷新设备列表
  useEffect(() => {
    if (tcpStatus === 'running') {
      loadDevices()
      const interval = setInterval(loadDevices, 5000)
      return () => clearInterval(interval)
    }
  }, [tcpStatus])

  // 选中帧详情
  useEffect(() => {
    if (selectedFrameId) {
      const frame = frames.find((f) => f.id === selectedFrameId)
      setSelectedFrame(frame || null)
    } else {
      setSelectedFrame(null)
    }
  }, [selectedFrameId, frames])

  // 启动服务器
  const handleStartServer = async () => {
    setTcpStatus('starting')
    try {
      await startTcpServer()
      setTcpStatus('running')
      message.success(`${tcpConfig.protocol.toUpperCase()} 服务器已启动，端口: ${tcpConfig.port}`)
      loadDevices()
    } catch (e) {
      setTcpStatus('stopped')
      message.error(`启动失败: ${e.message}`)
    }
  }

  // 停止服务器
  const handleStopServer = async () => {
    setTcpStatus('stopping')
    try {
      await stopTcpServer()
      setTcpStatus('stopped')
      message.info('服务器已停止')
    } catch (e) {
      setTcpStatus('running')
      message.error(`停止失败: ${e.message}`)
    }
  }

  // 打开配置面板
  const handleOpenConfig = () => {
    configForm.setFieldsValue(tcpConfig)
    setConfigPanelVisible(true)
  }

  // 保存配置
  const handleSaveConfig = async () => {
    try {
      const values = await configForm.validateFields()
      setConfigSaving(true)

      // 先保存到本地
      setTcpConfig(values)

      // 尝试同步到服务器
      try {
        await updateTcpConfig(values)
        message.success('配置已保存')
      } catch (e) {
        message.warning('已保存到本地，服务器同步失败')
      }

      setConfigPanelVisible(false)

      // 如果服务器正在运行，提示需要重启
      if (tcpStatus === 'running') {
        message.info('配置已更新，重启服务器后生效')
      }
    } catch (e) {
      if (e.errorFields) {
        message.error('请填写正确的配置信息')
      }
    } finally {
      setConfigSaving(false)
    }
  }

  // 重启服务器应用配置
  const handleRestartServer = async () => {
    setTcpStatus('stopping')
    try {
      await restartTcpServer()
      setTcpStatus('running')
      message.success('服务器已重启，新配置已生效')
      loadDevices()
    } catch (e) {
      message.error(`重启失败: ${e.message}`)
      setTcpStatus('running')
    }
  }

  // 开始编辑设备名称
  const handleStartRename = (device) => {
    setEditingDevice(device.system_title || device.connection_id)
    setEditingName(device.device_name || '')
  }

  // 保存设备名称
  const handleSaveRename = async (device) => {
    const systemTitle = device.system_title
    if (!systemTitle) {
      message.warning('设备尚未识别，无法重命名')
      setEditingDevice(null)
      return
    }

    try {
      renameDeviceInStore(systemTitle, editingName)
      // 尝试同步到后端
      try {
        await renameDevice(systemTitle, editingName)
      } catch (e) {
        console.log('同步设备名称到服务器失败:', e.message)
      }
      message.success('设备名称已更新')
    } catch (e) {
      message.error(`重命名失败: ${e.message}`)
    }
    setEditingDevice(null)
  }

  // 取消编辑
  const handleCancelRename = () => {
    setEditingDevice(null)
    setEditingName('')
  }

  // 发送数据
  const handleSend = async () => {
    if (!sendPanel.hexData) {
      message.warning('请输入要发送的十六进制数据')
      return
    }
    if (tcpStatus !== 'running') {
      message.warning('服务器未运行')
      return
    }

    try {
      const params = {
        hex_data: sendPanel.hexData
      }

      if (sendPanel.targetDevice) {
        params.system_title = sendPanel.targetDevice
      }

      await sendTcpData(params)
      message.success('数据已发送')
    } catch (e) {
      message.error(`发送失败: ${e.message}`)
    }
  }

  // 状态配置
  const statusConfig = {
    stopped: { status: 'default', text: '已停止', color: 'default' },
    starting: { status: 'processing', text: '启动中', color: 'blue' },
    running: { status: 'success', text: '运行中', color: 'green' },
    stopping: { status: 'processing', text: '停止中', color: 'orange' }
  }

  const currentStatus = statusConfig[tcpStatus] || statusConfig.stopped

  // 格式化时间
  const formatTime = (timeStr) => {
    if (!timeStr) return '-'
    try {
      const date = new Date(timeStr)
      return date.toLocaleTimeString('zh-CN', { hour12: false })
    } catch {
      return timeStr
    }
  }

  return (
    <div className="page-container">
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'tcp',
            label: (
              <Space>
                <ThunderboltOutlined />
                <span>TCP 管理</span>
              </Space>
            ),
            children: (
      <Card
        style={{ height: '100%' }}
        bodyStyle={{ height: 'calc(100% - 57px)', padding: 0 }}
        title={
          <Space>
            <ThunderboltOutlined />
            <Title level={5} style={{ margin: 0 }}>
              实时流 / {tcpConfig.protocol.toUpperCase()} 管理
            </Title>
            <Badge status={currentStatus.status} text={currentStatus.text} />
          </Space>
        }
        extra={
          <Space>
            <Text type="secondary">
              {tcpConfig.protocol.toUpperCase()} · 端口 {tcpConfig.port}
            </Text>
            <Button
              size="small"
              icon={<SettingOutlined />}
              onClick={handleOpenConfig}
            >
              配置
            </Button>
            {tcpStatus === 'running' || tcpStatus === 'stopping' ? (
              <Button
                danger
                icon={<StopOutlined />}
                onClick={handleStopServer}
                loading={tcpStatus === 'stopping'}
              >
                停止服务
              </Button>
            ) : (
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleStartServer}
                loading={tcpStatus === 'starting'}
              >
                启动服务
              </Button>
            )}
          </Space>
        }
      >
        <Row style={{ height: '100%' }}>
          {/* 左侧：设备列表 */}
          <Col span={6} style={{ height: '100%', borderRight: '1px solid #f0f0f0' }}>
            <div style={{ padding: 12 }}>
              <Space align="center" style={{ marginBottom: 8 }}>
                <DesktopOutlined />
                <Text strong>已连接设备</Text>
                <Tag color="green">{connectedDevices.length}</Tag>
                <Button
                  size="small"
                  type="text"
                  icon={<ReloadOutlined />}
                  onClick={loadDevices}
                  loading={loadingDevices}
                  disabled={tcpStatus !== 'running'}
                />
              </Space>
            </div>
            <div style={{ overflow: 'auto', height: 'calc(100% - 44px)' }}>
              {connectedDevices.length > 0 ? (
                <List
                  dataSource={connectedDevices}
                  renderItem={(device) => {
                    const displayName = device.device_name || device.system_title || device.connection_id
                    const isEditing = editingDevice === (device.system_title || device.connection_id)

                    return (
                      <List.Item
                        style={{ padding: '12px 16px', cursor: 'pointer' }}
                        actions={[
                          <Button
                            key="rename"
                            size="small"
                            type="text"
                            icon={<EditOutlined />}
                            onClick={(e) => {
                              e.stopPropagation()
                              handleStartRename(device)
                            }}
                          />
                        ]}
                      >
                        <List.Item.Meta
                          avatar={<DesktopOutlined style={{ fontSize: 20, color: device.connected ? '#52c41a' : '#999' }} />}
                          title={
                            <Space>
                              {isEditing ? (
                                <Input
                                  size="small"
                                  value={editingName}
                                  onChange={(e) => setEditingName(e.target.value)}
                                  onPressEnter={() => handleSaveRename(device)}
                                  style={{ width: 120 }}
                                  autoFocus
                                  suffix={
                                    <Space size={4}>
                                      <Button
                                        size="small"
                                        type="text"
                                        icon={<CheckOutlined />}
                                        onClick={() => handleSaveRename(device)}
                                        style={{ padding: 0 }}
                                      />
                                      <Button
                                        size="small"
                                        type="text"
                                        danger
                                        icon={<CloseOutlined />}
                                        onClick={handleCancelRename}
                                        style={{ padding: 0 }}
                                      />
                                    </Space>
                                  }
                                />
                              ) : (
                                <Text strong>{displayName}</Text>
                              )}
                              <Badge status={device.connected ? 'success' : 'default'} />
                            </Space>
                          }
                          description={
                            <Space direction="vertical" size={0}>
                              {device.system_title && (
                                <Text type="secondary" style={{ fontSize: 12, fontFamily: 'monospace' }}>
                                  ST: {device.system_title}
                                </Text>
                              )}
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                {device.ip}:{device.port}
                              </Text>
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                最后活动: {formatTime(device.last_seen)}
                              </Text>
                            </Space>
                          }
                        />
                      </List.Item>
                    )
                  }}
                />
              ) : (
                <Empty
                  description={tcpStatus === 'running' ? '暂无设备连接' : '服务器未启动'}
                  style={{ marginTop: 40 }}
                />
              )}
            </div>
          </Col>

          {/* 中间：帧时间线 */}
          <Col span={10} style={{ height: '100%', borderRight: '1px solid #f0f0f0' }}>
            <div style={{ padding: 12, borderBottom: '1px solid #f0f0f0' }}>
              <Space align="center">
                <RocketOutlined />
                <Text strong>帧时间线</Text>
                <Tag>{frames.length}</Tag>
              </Space>
            </div>
            <div style={{ overflow: 'auto', height: 'calc(100% - 44px)', padding: 16 }}>
              {frames.length > 0 ? (
                <Timeline
                  items={frames.map((frame) => ({
                    color: frame.direction === 'in' ? 'green' : 'blue',
                    children: (
                      <div
                        style={{
                          padding: 8,
                          borderRadius: 4,
                          background: selectedFrameId === frame.id ? '#e6f4ff' : '#fafafa',
                          cursor: 'pointer',
                          border: selectedFrameId === frame.id ? '1px solid #1677ff' : '1px solid #f0f0f0'
                        }}
                        onClick={() => selectFrame(frame.id)}
                      >
                        <Space direction="vertical" size={2} style={{ width: '100%' }}>
                          <Space>
                            <Tag color={frame.direction === 'in' ? 'green' : 'blue'}>
                              {frame.direction === 'in' ? '上行' : '下行'}
                            </Tag>
                            <Tag>{frame.type || 'UNKNOWN'}</Tag>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {frame.length || 0} bytes
                            </Text>
                          </Space>
                          {frame.system_title && (
                            <Text type="secondary" style={{ fontSize: 11, fontFamily: 'monospace' }}>
                              设备: {frame.system_title}
                            </Text>
                          )}
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {frame.timestamp}
                          </Text>
                        </Space>
                      </div>
                    )
                  }))}
                />
              ) : (
                <Empty description="暂无帧数据" style={{ marginTop: 60 }} />
              )}
            </div>
          </Col>

          {/* 右侧：帧详情 + 发送面板 */}
          <Col span={8} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Tabs
              defaultActiveKey="detail"
              items={[
                {
                  key: 'detail',
                  label: '帧详情',
                  children: (
                    <div style={{ padding: 12, overflow: 'auto', height: 'calc(100% - 46px)' }}>
                      {selectedFrame ? (
                        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                          <div>
                            <Text type="secondary">时间戳:</Text>
                            <div>{selectedFrame.timestamp}</div>
                          </div>
                          <div>
                            <Text type="secondary">方向:</Text>
                            <div>
                              <Tag color={selectedFrame.direction === 'in' ? 'green' : 'blue'}>
                                {selectedFrame.direction === 'in' ? '上行（设备→服务器）' : '下行（服务器→设备）'}
                              </Tag>
                            </div>
                          </div>
                          <div>
                            <Text type="secondary">帧类型:</Text>
                            <div>
                              <Tag>{selectedFrame.type || 'UNKNOWN'}</Tag>
                            </div>
                          </div>
                          <div>
                            <Text type="secondary">长度:</Text>
                            <div>{selectedFrame.length || 0} bytes</div>
                          </div>
                          {selectedFrame.system_title && (
                            <div>
                              <Text type="secondary">设备 System Title:</Text>
                              <div style={{ fontFamily: 'monospace' }}>{selectedFrame.system_title}</div>
                            </div>
                          )}
                          <div>
                            <Text type="secondary">十六进制数据:</Text>
                            <div
                              className="hex-viewer"
                              style={{
                                fontFamily: 'monospace',
                                fontSize: 12,
                                wordBreak: 'break-all'
                              }}
                            >
                              {selectedFrame.hex || '(无数据)'}
                            </div>
                          </div>
                        </Space>
                      ) : (
                        <Empty description="请选择一帧查看详情" style={{ marginTop: 60 }} />
                      )}
                    </div>
                  )
                },
                {
                  key: 'send',
                  label: '发送数据',
                  children: (
                    <div style={{ padding: 12, height: 'calc(100% - 46px)', display: 'flex', flexDirection: 'column' }}>
                      <Space direction="vertical" size="middle" style={{ width: '100%', flex: 1 }}>
                        <div>
                          <Text type="secondary">目标设备:</Text>
                          <Select
                            value={sendPanel.targetDevice || undefined}
                            onChange={(val) => setSendPanel({ targetDevice: val })}
                            placeholder="选择设备（不选则广播）"
                            style={{ width: '100%', marginTop: 4 }}
                            allowClear
                            disabled={connectedDevices.length === 0}
                          >
                            {connectedDevices.map((d) => (
                              <Option
                                key={d.system_title || d.connection_id}
                                value={d.system_title || d.connection_id}
                              >
                                {d.device_name || d.system_title || d.connection_id}
                                {d.ip ? ` (${d.ip})` : ''}
                              </Option>
                            ))}
                          </Select>
                        </div>
                        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                          <Text type="secondary">十六进制数据:</Text>
                          <TextArea
                            value={sendPanel.hexData}
                            onChange={(e) => setSendPanel({ hexData: e.target.value })}
                            placeholder="输入要发送的十六进制数据..."
                            style={{
                              flex: 1,
                              fontFamily: 'monospace',
                              fontSize: 13,
                              marginTop: 4
                            }}
                          />
                        </div>
                        <div>
                          <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                            <input
                              type="checkbox"
                              checked={sendPanel.autoIncrementCounter}
                              onChange={(e) => setSendPanel({ autoIncrementCounter: e.target.checked })}
                            />
                            自动递增Invocation Counter
                          </label>
                        </div>
                        <Button
                          type="primary"
                          icon={<SendOutlined />}
                          onClick={handleSend}
                          block
                          disabled={tcpStatus !== 'running'}
                        >
                          发送
                        </Button>
                      </Space>
                    </div>
                  )
                }
              ]}
            />
          </Col>
        </Row>
      </Card>
            ),
          },
          {
            key: 'capture',
            label: (
              <Space>
                <TableOutlined />
                <span>Capture Objects 配置</span>
              </Space>
            ),
            children: (
              <Card
                title={
                  <Space>
                    <ProfileOutlined />
                    <Title level={5} style={{ margin: 0 }}>
                      Profile Capture Objects 管理
                    </Title>
                  </Space>
                }
                extra={
                  <Space>
                    <Button
                      icon={<ReloadOutlined />}
                      onClick={loadCaptureProfiles}
                      loading={loadingProfiles}
                    >
                      刷新
                    </Button>
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => setAddProfileModalVisible(true)}
                    >
                      添加 Profile
                    </Button>
                  </Space>
                }
              >
                <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
                  配置 Profile Generic (Class 7) 的 capture_objects (属性3)。
                  配置保存后，解析 DataNotification 时将自动使用此配置深度解析 Profile buffer 中的每个元素。
                </Text>

                {captureProfiles.length > 0 ? (
                  <List
                    loading={loadingProfiles}
                    dataSource={captureProfiles}
                    renderItem={(item) => (
                      <List.Item
                        actions={[
                          <Button
                            key="edit"
                            size="small"
                            type="primary"
                            icon={<EditOutlined />}
                            onClick={() => handleOpenEditor(item.profile_obis)}
                          >
                            编辑
                          </Button>,
                          <Popconfirm
                            key="delete"
                            title="确认删除？"
                            description={`删除 ${item.profile_obis} 的配置`}
                            onConfirm={() => handleDeleteProfile(item.profile_obis)}
                            okText="删除"
                            cancelText="取消"
                            okButtonProps={{ danger: true }}
                          >
                            <Button size="small" danger icon={<DeleteOutlined />}>
                              删除
                            </Button>
                          </Popconfirm>
                        ]}
                      >
                        <List.Item.Meta
                          avatar={<TableOutlined style={{ fontSize: 24, color: '#1677ff' }} />}
                          title={
                            <Space>
                              <Text code>{item.profile_obis}</Text>
                              {item.profile_name && (
                                <Tag color="blue">{item.profile_name}</Tag>
                              )}
                              <Tag color="green">{item.capture_object_count} 个对象</Tag>
                              <Tag>来源: {item.source}</Tag>
                            </Space>
                          }
                          description={
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              创建: {item.created_at ? new Date(item.created_at).toLocaleString('zh-CN') : '-'}
                              {item.updated_at && ` | 更新: ${new Date(item.updated_at).toLocaleString('zh-CN')}`}
                              {item.used_count > 0 && ` | 使用次数: ${item.used_count}`}
                            </Text>
                          }
                        />
                      </List.Item>
                    )}
                  />
                ) : (
                  <Empty
                    description={loadingProfiles ? '加载中...' : '暂无配置，点击"添加 Profile"创建'}
                    style={{ marginTop: 60 }}
                  >
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => setAddProfileModalVisible(true)}
                      style={{ marginTop: 16 }}
                    >
                      添加 Profile
                    </Button>
                  </Empty>
                )}
              </Card>
            ),
          },
        ]}
      />

      {/* 配置弹窗 */}
      <Modal
        title={
          <Space>
            <SettingOutlined />
            <span>服务配置</span>
          </Space>
        }
        open={configPanelVisible}
        onCancel={() => setConfigPanelVisible(false)}
        footer={null}
        width={480}
        destroyOnClose
      >
        <Form form={configForm} layout="vertical">
          <Form.Item
            name="protocol"
            label="协议类型"
            rules={[{ required: true, message: '请选择协议类型' }]}
          >
            <Select>
              <Option value="tcp">TCP (面向连接)</Option>
              <Option value="udp">UDP (无连接)</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="port"
            label="监听端口"
            rules={[
              { required: true, message: '请输入端口号' },
              { type: 'number', min: 1, max: 65535, message: '端口号必须在 1-65535 之间' }
            ]}
          >
            <InputNumber style={{ width: '100%' }} min={1} max={65535} />
          </Form.Item>

          <Form.Item
            name="auto_start"
            label="自动启动"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Divider />

          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={() => setConfigPanelVisible(false)}>取消</Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSaveConfig}
              loading={configSaving}
            >
              保存配置
            </Button>
            {tcpStatus === 'running' && (
              <Popconfirm
                title="重启服务器？"
                description="重启后新配置将生效"
                onConfirm={handleRestartServer}
                okText="重启"
                cancelText="取消"
                okButtonProps={{ danger: true }}
              >
                <Button danger icon={<ReloadOutlined />}>
                  重启生效
                </Button>
              </Popconfirm>
            )}
          </Space>
        </Form>
      </Modal>

      {/* Capture Objects 编辑器弹窗 */}
      <CaptureObjectsEditor
        visible={editorVisible}
        onClose={() => setEditorVisible(false)}
        profileObis={editorObis}
        onSuccess={handleEditorSuccess}
      />

      {/* 添加新 Profile 弹窗 */}
      <Modal
        title={
          <Space>
            <PlusOutlined />
            <span>添加 Profile 配置</span>
          </Space>
        }
        open={addProfileModalVisible}
        onOk={handleAddProfile}
        onCancel={() => setAddProfileModalVisible(false)}
        okText="配置"
        cancelText="取消"
      >
        <p style={{ marginBottom: 12 }}>
          请输入 Profile Generic 的 OBIS 代码（例如：1-0:99.1.0.255）
        </p>
        <Input
          value={newProfileObis}
          onChange={(e) => setNewProfileObis(e.target.value)}
          placeholder="1-0:99.1.0.255"
          onPressEnter={handleAddProfile}
        />
      </Modal>
    </div>
  )
}

export default StreamPage
