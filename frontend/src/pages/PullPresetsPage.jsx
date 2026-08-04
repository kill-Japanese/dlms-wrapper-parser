import { useState, useEffect } from 'react'
import {
  Row,
  Col,
  Card,
  Button,
  Space,
  Typography,
  Switch,
  message,
  InputNumber,
  Form,
  Divider,
  Tooltip
} from 'antd'
import {
  PlayCircleOutlined,
  PlusOutlined,
  ThunderboltOutlined,
  SettingOutlined,
  SaveOutlined,
  SyncOutlined
} from '@ant-design/icons'
import usePullStore from '../store/pullStore.js'
import {
  getPullPresets,
  savePullPresets,
  executePullPreset,
  executePullOperations
} from '../services/pullApi.js'
import PresetList from '../components/pull/PresetList.jsx'
import PresetEditor from '../components/pull/PresetEditor.jsx'
import ObjectSelector from '../components/pull/ObjectSelector.jsx'
import PullResult from '../components/pull/PullResult.jsx'

const { Title, Text } = Typography

function PullPresetsPage() {
  const {
    presets,
    activePreset,
    executionResult,
    loading,
    objectSelectorVisible,
    selectorTargetPresetId,
    setActivePreset,
    setObjectSelectorVisible,
    setSelectorTargetPresetId,
    addOperation,
    loadPresets,
    savePresets: savePresetsToApi,
    executePreset
  } = usePullStore()

  const [viewMode, setViewMode] = useState('list') // list | edit
  const [useWithList, setUseWithList] = useState(true)
  const [withWrapper, setWithWrapper] = useState(true)
  const [srcWport, setSrcWport] = useState(1)
  const [dstWport, setDstWport] = useState(16)
  const [executing, setExecuting] = useState(false)

  // 加载预设列表
  useEffect(() => {
    loadPresets(getPullPresets).catch(() => {
      // 后端不可用时使用本地数据
      console.log('使用本地预设数据')
    })
  }, [])

  const handleCreatePreset = () => {
    const newPreset = {
      id: `preset-${Date.now()}`,
      name: '新预设',
      description: '',
      operations: []
    }
    usePullStore.getState().addPreset(newPreset)
    setActivePreset(newPreset)
    setViewMode('edit')
  }

  const handleEditPreset = (preset) => {
    setActivePreset(preset)
    setViewMode('edit')
  }

  const handleSavePreset = () => {
    // 保存到后端
    savePresetsToApi(savePullPresets)
      .then(() => {
        message.success('预设已同步到服务器')
      })
      .catch(() => {
        message.warning('已保存到本地，服务器同步失败')
      })
  }

  const handleExecutePreset = async (preset) => {
    setExecuting(true)
    try {
      const options = {
        useWithList,
        withWrapper,
        srcWport,
        dstWport
      }
      await executePreset(executePullPreset, preset.id, options)
      message.success(`已生成 ${preset.name} 的请求帧`)
    } catch (error) {
      message.error(`执行失败: ${error.message}`)
    } finally {
      setExecuting(false)
    }
  }

  const handleOpenObjectSelector = () => {
    if (activePreset) {
      setSelectorTargetPresetId(activePreset.id)
      setObjectSelectorVisible(true)
    }
  }

  const handleObjectsSelected = (operations) => {
    const targetId = selectorTargetPresetId || activePreset?.id
    if (targetId && operations.length > 0) {
      operations.forEach((op) => {
        addOperation(targetId, op)
      })
      message.success(`已添加 ${operations.length} 个操作到预设`)
    }
    setObjectSelectorVisible(false)
    setSelectorTargetPresetId(null)
  }

  const handleSyncFromServer = async () => {
    try {
      await loadPresets(getPullPresets)
      message.success('已从服务器同步预设')
    } catch (error) {
      message.warning('服务器同步失败，使用本地数据')
    }
  }

  return (
    <div className="page-container" style={{ height: '100%' }}>
      <Row gutter={16} style={{ height: '100%' }}>
        {/* 左侧：预设列表 */}
        <Col span={8} style={{ height: '100%' }}>
          <Card
            title={
              <Space>
                <ThunderboltOutlined />
                <Title level={5} style={{ margin: 0 }}>
                  预设列表
                </Title>
              </Space>
            }
            extra={
              <Space>
                <Tooltip title="从服务器同步">
                  <Button
                    size="small"
                    icon={<SyncOutlined />}
                    onClick={handleSyncFromServer}
                  />
                </Tooltip>
                <Button
                  type="primary"
                  size="small"
                  icon={<PlusOutlined />}
                  onClick={handleCreatePreset}
                >
                  新建
                </Button>
              </Space>
            }
            style={{ height: '100%' }}
            bodyStyle={{ height: 'calc(100% - 57px)', padding: 0, overflow: 'auto' }}
          >
            <PresetList
              onEdit={handleEditPreset}
              onExecute={handleExecutePreset}
              onAdd={handleCreatePreset}
            />
          </Card>
        </Col>

        {/* 中间：编辑器 / 执行设置 */}
        <Col span={9} style={{ height: '100%' }}>
          {viewMode === 'edit' && activePreset ? (
            <Card
              title={
                <Space>
                  <SettingOutlined />
                  <Title level={5} style={{ margin: 0 }}>
                    编辑预设
                  </Title>
                  <Button
                    size="small"
                    onClick={() => {
                      setActivePreset(null)
                      setViewMode('list')
                    }}
                  >
                    返回列表
                  </Button>
                </Space>
              }
              style={{ height: '100%' }}
              bodyStyle={{ height: 'calc(100% - 57px)', padding: 12 }}
            >
              <PresetEditor
                preset={activePreset}
                onSave={() => {
                  handleSavePreset()
                }}
                onClose={() => {
                  setActivePreset(null)
                  setViewMode('list')
                }}
                onOpenObjectSelector={handleOpenObjectSelector}
              />
            </Card>
          ) : (
            <Card
              title={
                <Space>
                  <PlayCircleOutlined />
                  <Title level={5} style={{ margin: 0 }}>
                    执行设置
                  </Title>
                </Space>
              }
              style={{ height: '100%' }}
              bodyStyle={{ padding: 16 }}
            >
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <div>
                  <Text type="secondary" style={{ marginBottom: 8, display: 'block' }}>
                    选择左侧预设进行编辑或执行
                  </Text>
                </div>

                <Divider />

                <div>
                  <Title level={5} style={{ marginBottom: 12 }}>
                    执行选项
                  </Title>
                  <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Space>
                        <Text>WithList 模式</Text>
                        <Tooltip title="启用后使用 GetRequest WithList 在一帧中请求多个对象">
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            (一帧多对象)
                          </Text>
                        </Tooltip>
                      </Space>
                      <Switch
                        checked={useWithList}
                        onChange={setUseWithList}
                      />
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Space>
                        <Text>封装 Wrapper</Text>
                        <Tooltip title="启用后将 APDU 封装为 DLMS Wrapper 帧">
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            (TCP/IP 通信)
                          </Text>
                        </Tooltip>
                      </Space>
                      <Switch
                        checked={withWrapper}
                        onChange={setWithWrapper}
                      />
                    </div>

                    <Row gutter={16}>
                      <Col span={12}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <Text style={{ whiteSpace: 'nowrap' }}>源 WPort:</Text>
                          <InputNumber
                            min={0}
                            max={65535}
                            value={srcWport}
                            onChange={setSrcWport}
                            style={{ flex: 1 }}
                          />
                        </div>
                      </Col>
                      <Col span={12}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <Text style={{ whiteSpace: 'nowrap' }}>目的 WPort:</Text>
                          <InputNumber
                            min={0}
                            max={65535}
                            value={dstWport}
                            onChange={setDstWport}
                            style={{ flex: 1 }}
                          />
                        </div>
                      </Col>
                    </Row>
                  </Space>
                </div>

                <Divider />

                <div>
                  <Title level={5} style={{ marginBottom: 12 }}>
                    快速操作
                  </Title>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Button
                      type="primary"
                      icon={<SaveOutlined />}
                      block
                      onClick={handleSavePreset}
                    >
                      同步预设到服务器
                    </Button>
                  </Space>
                </div>
              </Space>
            </Card>
          )}
        </Col>

        {/* 右侧：执行结果 */}
        <Col span={7} style={{ height: '100%' }}>
          <PullResult result={executionResult} />
        </Col>
      </Row>

      {/* 对象选择器弹窗 */}
      <ObjectSelector
        visible={objectSelectorVisible}
        onClose={() => {
          setObjectSelectorVisible(false)
          setSelectorTargetPresetId(null)
        }}
        onSelect={handleObjectsSelected}
        multiSelect={true}
      />
    </div>
  )
}

export default PullPresetsPage
