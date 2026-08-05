import { useState, useEffect, useCallback } from 'react'
import {
  Row,
  Col,
  Card,
  Button,
  Input,
  List,
  Empty,
  Space,
  Typography,
  Tag,
  Upload,
  message,
  Select,
  Spin,
  Table,
  Tooltip,
  Divider,
  Alert,
  Modal
} from 'antd'
import {
  UploadOutlined,
  SearchOutlined,
  DatabaseOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  CodeOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  GithubOutlined
} from '@ant-design/icons'
import useDataModelStore from '../store/datamodelStore.js'

const { Title, Text } = Typography
const { Option } = Select

// COSEM 常见类名称映射（IC / Interface Class）
const CLASS_NAMES = {
  0: 'General Protection',
  1: 'Data',
  2: 'Array',
  3: 'Register',
  4: 'Extended Register',
  5: 'Demand Register',
  6: 'Register Activation',
  7: 'Profile Generic',
  8: 'Clock',
  9: 'Script Table',
  10: 'Schedule',
  11: 'Special Days Table',
  12: 'Activity Calendar',
  13: 'Association LN',
  14: 'Association SN',
  15: 'SAP Assignment',
  16: 'Image Transfer',
  17: 'IEC Local Port Setup',
  18: 'IEC HDLC Setup',
  19: 'Security Setup',
  20: 'Disconnect Control',
  21: 'Limiter',
  22: 'MCU Firmware Update',
  23: 'Modem Configuration',
  24: 'Auto Answer',
  25: 'Auto Connect',
  26: 'PPP Setup',
  27: 'GPRS Modem Configuration',
  28: 'SMTP Setup',
  29: 'Register Monitor',
  30: 'Utility Tables',
  31: 'Single Action Schedule',
  32: 'IEC Local Port',
  33: 'IEC HDLC',
  34: 'IEC Twisted Pair',
  35: 'MBus Client',
  36: 'Wireless Mode Q',
  37: 'MBus Slave',
  38: 'PSTN Modem',
  39: 'GPRS Modem',
  40: 'SMTP Client',
  41: 'Data Protection',
  42: 'Push Setup',
  43: 'Register Table',
  44: 'Status Mapping',
  45: 'Disconnect Control Extended',
  46: 'Time / 256',
  47: 'Special Days Table (2)',
  48: 'IPv4 Setup',
  49: 'IPv6 Setup',
  50: 'TCP UDP Setup',
  64: 'Security Setup',
  70: 'S-FSK PHY Layer',
  71: 'S-FSK MAC Layer',
  72: 'S-FSK Network Layer',
  73: 'S-FSK Application Layer',
  98: 'S-FSK Commissioning',
  99: 'S-FSK Diagnostics',
  100: 'S-FSK MAC Sync',
  101: 'S-FSK MAC Function Addressing',
  102: 'S-FSK MAC Service Node',
  103: 'S-FSK MAC Switching',
  104: 'S-FSK MAC Message',
  105: 'S-FSK MAC PDUE',
  106: 'S-FSK MAC Routing',
  107: 'S-FSK MAC Superframe',
  108: 'S-FSK MAC Neighbour Discovery',
  109: 'S-FSK MAC Coordinator',
  110: 'S-FSK MAC Device',
  111: 'S-FSK MAC Reduced',
  112: 'S-FSK MAC Commissioning',
  113: 'S-FSK MAC Diagnostic',
  120: 'Prime OFDM PHY',
  121: 'Prime OFDM MAC',
  122: 'Prime OFDM Convergence',
  123: 'Prime OFDM Data Message',
  124: 'Prime OFDM Data Management',
  125: 'Prime OFDM Data Control',
  126: 'Prime OFDM Data Protection',
  127: 'Prime OFDM Data Routing',
  128: 'Prime OFDM Data Fragmentation',
  129: 'Prime OFDM Data Reassembly',
  130: 'Prime OFDM Data ARQ',
  131: 'Prime OFDM Data Multicast',
  132: 'Prime OFDM Data Power Spectra',
  133: 'Prime OFDM Data Tone Map',
  134: 'Prime OFDM Data Channel Estimation',
  135: 'Prime OFDM Data SNR',
  136: 'Prime OFDM Data BER',
  137: 'Prime OFDM Data Throughput',
  138: 'Prime OFDM Data Statistics',
  139: 'Prime OFDM Data Discovery',
  140: 'Prime OFDM Data Registration',
  141: 'Prime OFDM Data Authentication',
  142: 'Prime OFDM Data Key Exchange',
  143: 'Prime OFDM Data Security',
  144: 'Prime OFDM Data Power Control',
  145: 'Prime OFDM Data Rate Adaptation',
  146: 'Prime OFDM Data Topology',
  147: 'Prime OFDM Data Neighbour',
  148: 'Prime OFDM Data Routing Table',
  149: 'Prime OFDM Data Routing Protocol',
  150: 'Prime OFDM Data Routing Metrics',
  151: 'Prime OFDM Data Routing Discovery',
  152: 'Prime OFDM Data Routing Maintenance',
  153: 'Prime OFDM Data Routing Error',
  154: 'Prime OFDM Data Routing Multicast',
  155: 'Prime OFDM Data Routing Broadcast',
  156: 'Prime OFDM Data Routing Unicast',
  157: 'Prime OFDM Data Routing Anycast',
  158: 'Prime OFDM Data Routing Geocast',
  159: 'Prime OFDM Data Routing Path',
  160: 'Prime OFDM Data Routing Tree',
  161: 'Prime OFDM Data Routing Mesh',
  162: 'Prime OFDM Data Routing Star',
  163: 'Prime OFDM Data Routing Ring',
  164: 'Prime OFDM Data Routing Bus',
  165: 'Prime OFDM Data Routing Hybrid',
  166: 'Prime OFDM Data Routing Dynamic',
  167: 'Prime OFDM Data Routing Static',
  168: 'Prime OFDM Data Routing Centralized',
  169: 'Prime OFDM Data Routing Distributed',
  170: 'Prime OFDM Data Routing Hierarchical',
  171: 'Prime OFDM Data Routing Flat',
  172: 'Prime OFDM Data Routing Proactive',
  173: 'Prime OFDM Data Routing Reactive',
  174: 'Prime OFDM Data Routing Hybrid',
  225: 'S-FSK Physical Layer',
  226: 'S-FSK MAC Layer',
  227: 'S-FSK Convergence Layer',
  228: 'S-FSK Management Message',
  229: 'S-FSK Data Link Management',
  230: 'S-FSK Data Link Control',
  231: 'S-FSK Data Link Protection',
  232: 'S-FSK Data Link Routing',
  233: 'S-FSK Data Link Fragmentation',
  234: 'S-FSK Data Link Reassembly',
  235: 'S-FSK Data Link ARQ',
  236: 'S-FSK Data Link Multicast',
  237: 'S-FSK Data Link Power Spectra',
  238: 'S-FSK Data Link Tone Map',
  239: 'S-FSK Data Link Channel Estimation',
  240: 'S-FSK Data Link SNR',
  241: 'S-FSK Data Link BER',
  242: 'S-FSK Data Link Throughput',
  243: 'S-FSK Data Link Statistics',
  244: 'S-FSK Data Link Discovery',
  245: 'S-FSK Data Link Registration',
  246: 'S-FSK Data Link Authentication',
  247: 'S-FSK Data Link Key Exchange',
  248: 'S-FSK Data Link Security',
  249: 'S-FSK Data Link Power Control',
  250: 'S-FSK Data Link Rate Adaptation',
  251: 'S-FSK Data Link Topology',
  252: 'S-FSK Data Link Neighbour',
  253: 'S-FSK Data Link Routing Table',
  254: 'S-FSK Data Link Routing Protocol',
  255: 'S-FSK Data Link Routing Metrics'
}

function getClassName(classId) {
  return CLASS_NAMES[classId] || `Class ${classId}`
}

function DataModelPage() {
  const {
    isLoaded,
    objects,
    selectedObject,
    selectedObjectDetail,
    searchQuery,
    classes,
    selectedClassId,
    loading,
    uploading,
    importingGithub,
    uploadProgress,
    detailLoading,
    totalObjects,
    totalObjectHeaders,
    sourceFile,
    error,
    usingFallbackApi,
    setSearchQuery,
    setSelectedClassId,
    checkStatus,
    uploadFile,
    importFromGithub,
    loadObjects,
    search,
    selectObject
  } = useDataModelStore()

  const [searchInput, setSearchInput] = useState('')
  const [searchTimer, setSearchTimer] = useState(null)
  const [githubModalVisible, setGithubModalVisible] = useState(false)
  const [githubUrl, setGithubUrl] = useState(
    'https://raw.githubusercontent.com/kill-Japanese/dlms-wrapper-parser/main/sample_data/cosem_data_model.xlsx'
  )

  // 页面加载时检查状态
  useEffect(() => {
    checkStatus().then((status) => {
      if (status && status.loaded) {
        loadObjects()
      }
    })
  }, [])

  // 处理搜索输入（防抖）
  const handleSearchInput = useCallback((e) => {
    const value = e.target.value
    setSearchInput(value)
    setSearchQuery(value)

    if (searchTimer) {
      clearTimeout(searchTimer)
    }

    const timer = setTimeout(() => {
      if (isLoaded) {
        search(value)
      }
    }, 300)

    setSearchTimer(timer)
  }, [searchTimer, isLoaded, search, setSearchQuery])

  // 处理类过滤变化
  const handleClassFilterChange = useCallback((value) => {
    setSelectedClassId(value || null)
    // 延迟到下一个 tick，等 store 更新后再加载
    setTimeout(() => {
      if (searchInput) {
        search(searchInput)
      } else {
        loadObjects()
      }
    }, 0)
  }, [searchInput, search, loadObjects, setSelectedClassId])

  // 处理上传
  const handleUpload = useCallback(async (file) => {
    try {
      const hide = message.loading('正在上传并解析数模文件...', 0)
      await uploadFile(file)
      hide()

      // 检查是否有警告（如对象数为0）
      const state = useDataModelStore.getState()
      if (state.error) {
        message.warning(`上传成功，但有警告：${state.error}`)
      } else {
        message.success(`数模文件 "${file.name}" 上传成功，已加载对象列表`)
      }
    } catch (err) {
      message.error(`上传失败: ${err.message || '未知错误'}`)
    }
    return false // 阻止自动上传
  }, [uploadFile])

  // 处理 GitHub 导入
  const handleGithubImport = useCallback(async () => {
    if (!githubUrl.trim()) {
      message.warning('请输入 GitHub Raw URL')
      return
    }
    try {
      const hide = message.loading('正在从 GitHub 下载并解析数模文件...', 0)
      await importFromGithub(githubUrl.trim())
      hide()
      message.success('数据模型导入成功！')
      setGithubModalVisible(false)
    } catch (err) {
      message.error(`导入失败: ${err.message || '未知错误'}`)
    }
  }, [githubUrl, importFromGithub])

  // 处理选择对象
  const handleSelectObject = useCallback((obj) => {
    selectObject(obj)
  }, [selectObject])

  // 属性列表表格列
  const attributeColumns = [
    {
      title: '序号',
      dataIndex: 'attribute_id',
      key: 'attribute_id',
      width: 70,
      render: (id) => <Tag color="blue">#{id}</Tag>
    },
    {
      title: '属性名',
      dataIndex: 'name',
      key: 'name',
      render: (name) => (
        <Text strong style={{ fontFamily: 'monospace' }}>
          {name || '-'}
        </Text>
      )
    },
    {
      title: '数据类型',
      dataIndex: 'data_type',
      key: 'data_type',
      width: 180,
      render: (type) => (
        <Tag color="default">{type || '-'}</Tag>
      )
    },
    {
      title: '单位',
      dataIndex: 'unit',
      key: 'unit',
      width: 80,
      render: (unit) => unit || '-'
    },
    {
      title: '倍率',
      dataIndex: 'scaler',
      key: 'scaler',
      width: 80,
      render: (scaler) => (
        scaler !== 1.0 ? scaler : '-'
      )
    }
  ]

  // 方法列表表格列
  const methodColumns = [
    {
      title: '序号',
      dataIndex: 'method_id',
      key: 'method_id',
      width: 70,
      render: (id) => <Tag color="green">#{id}</Tag>
    },
    {
      title: '方法名',
      dataIndex: 'name',
      key: 'name',
      render: (name) => (
        <Text strong style={{ fontFamily: 'monospace' }}>
          {name || '-'}
        </Text>
      )
    },
    {
      title: '返回类型',
      dataIndex: 'data_type',
      key: 'data_type',
      width: 180,
      render: (type) => (
        <Tag color="default">{type || '-'}</Tag>
      )
    }
  ]

  // 获取对象计数显示
  const objectCount = totalObjectHeaders || objects.length || 0
  const isZeroObjects = isLoaded && objectCount === 0

  return (
    <div className="page-container">
      <Card
        title={
          <Space>
            <DatabaseOutlined />
            <Title level={5} style={{ margin: 0 }}>
              数据模型管理
            </Title>
            {isLoaded && (
              <Tag color="success">已加载</Tag>
            )}
            {usingFallbackApi && (
              <Tooltip title="当前使用兼容模式，后端版本较旧可能功能不全">
                <Tag color="orange">兼容模式</Tag>
              </Tooltip>
            )}
            {sourceFile && (
              <Tooltip title="当前加载的数模文件">
                <Text type="secondary" style={{ fontSize: 12 }}>
                  <FileTextOutlined /> {sourceFile}
                </Text>
              </Tooltip>
            )}
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<GithubOutlined />}
              onClick={() => setGithubModalVisible(true)}
            >
              从 GitHub 导入
            </Button>
            <Upload
              beforeUpload={handleUpload}
              showUploadList={false}
              accept=".xlsx,.xls"
            >
              <Button type="primary" icon={<UploadOutlined />} loading={uploading}>
                上传数模
              </Button>
            </Upload>
          </Space>
        }
        style={{ height: '100%' }}
        bodyStyle={{ height: 'calc(100% - 57px)', padding: 0 }}
      >
        {!isLoaded ? (
          // 空状态：未上传数模
          <div style={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Empty
              image={
                <DatabaseOutlined
                  style={{
                    fontSize: 80,
                    color: '#d9d9d9'
                  }}
                />
              }
              description={
                <Space direction="vertical" size="small">
                  <Text strong style={{ fontSize: 16 }}>
                    尚未加载数据模型
                  </Text>
                  <Text type="secondary">
                    请上传 COSEM 数据模型 Excel 文件，或直接从 GitHub 导入示例数模
                  </Text>
                  <Space>
                    <Button
                      type="primary"
                      icon={<GithubOutlined />}
                      onClick={() => setGithubModalVisible(true)}
                      loading={importingGithub}
                    >
                      从 GitHub 导入示例数模
                    </Button>
                    <Upload
                      beforeUpload={handleUpload}
                      showUploadList={false}
                      accept=".xlsx,.xls"
                    >
                      <Button icon={<UploadOutlined />} loading={uploading}>
                        上传数模文件
                      </Button>
                    </Upload>
                  </Space>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    支持 .xlsx / .xls 格式（标准行式 或 SABESP 对象分组式）
                  </Text>
                </Space>
              }
              style={{ marginTop: 0 }}
            />
            {uploading && (
              <div style={{ width: 300, marginTop: 24 }}>
                <div style={{ marginBottom: 8 }}>
                  <Text type="secondary">上传进度: {uploadProgress}%</Text>
                </div>
                <div style={{
                  width: '100%',
                  height: 8,
                  background: '#f0f0f0',
                  borderRadius: 4,
                  overflow: 'hidden'
                }}>
                  <div
                    style={{
                      width: `${uploadProgress}%`,
                      height: '100%',
                      background: '#1677ff',
                      transition: 'width 0.3s'
                    }}
                  />
                </div>
              </div>
            )}
          </div>
        ) : (
          <Row style={{ height: '100%' }}>
            {/* 左侧对象列表 */}
            <Col span={10} style={{ height: '100%', borderRight: '1px solid #f0f0f0', display: 'flex', flexDirection: 'column' }}>
              {/* 搜索和过滤栏 */}
              <div style={{ padding: 12, borderBottom: '1px solid #f0f0f0' }}>
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <Input
                    placeholder="搜索 OBIS 码、名称或描述..."
                    prefix={<SearchOutlined />}
                    value={searchInput}
                    onChange={handleSearchInput}
                    allowClear
                  />
                  <Select
                    placeholder="按类过滤"
                    allowClear
                    style={{ width: '100%' }}
                    value={selectedClassId || undefined}
                    onChange={handleClassFilterChange}
                    size="small"
                  >
                    {classes.map((cls) => (
                      <Option key={cls} value={cls}>
                        Class {cls} - {getClassName(cls)}
                      </Option>
                    ))}
                  </Select>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Text
                      type={isZeroObjects ? 'danger' : 'secondary'}
                      style={{ fontSize: 12 }}
                    >
                      {isZeroObjects && <WarningOutlined style={{ marginRight: 4 }} />}
                      共 {objectCount} 个对象
                    </Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      总条目: {totalObjects}
                    </Text>
                  </div>

                  {/* 错误/警告提示 */}
                  {error && (
                    <Alert
                      message={isZeroObjects ? '数据异常' : '加载错误'}
                      description={error}
                      type={isZeroObjects ? 'warning' : 'error'}
                      showIcon
                      size="small"
                      style={{ marginTop: 4 }}
                    />
                  )}

                  {/* 零对象时的建议 */}
                  {isZeroObjects && !loading && (
                    <Alert
                      message="未加载到对象数据"
                      description={
                        <Space direction="vertical" size={4} style={{ fontSize: 12 }}>
                          <span>可能的原因：</span>
                          <ol style={{ margin: '4px 0 4px 20px', padding: 0 }}>
                            <li>数模文件格式不正确</li>
                            <li>后端版本不兼容（建议升级后端）</li>
                            <li>文件中没有有效的对象定义</li>
                          </ol>
                          <Button size="small" type="primary" icon={<UploadOutlined />}>
                            重新上传
                          </Button>
                        </Space>
                      }
                      type="info"
                      showIcon
                      size="small"
                    />
                  )}
                </Space>
              </div>

              {/* 对象列表 */}
              <div style={{ flex: 1, overflow: 'auto' }}>
                <Spin spinning={loading} tip="加载中...">
                  {objects.length > 0 ? (
                    <List
                      dataSource={objects}
                      renderItem={(item) => (
                        <List.Item
                          style={{
                            cursor: 'pointer',
                            padding: '12px 16px',
                            background:
                              selectedObject?.obis === item.obis && selectedObject?.class_id === item.class_id
                                ? '#e6f4ff'
                                : 'transparent',
                            borderLeft:
                              selectedObject?.obis === item.obis && selectedObject?.class_id === item.class_id
                                ? '3px solid #1677ff'
                                : '3px solid transparent'
                          }}
                          onClick={() => handleSelectObject(item)}
                        >
                          <List.Item.Meta
                            title={
                              <Space>
                                <Text strong>{item.name || '未命名对象'}</Text>
                                <Tag color="blue">Class {item.class_id}</Tag>
                              </Space>
                            }
                            description={
                              <Space direction="vertical" size={0}>
                                <Text code>{item.obis}</Text>
                                {item.description && (
                                  <Text type="secondary" ellipsis style={{ fontSize: 12 }}>
                                    {item.description}
                                  </Text>
                                )}
                              </Space>
                            }
                          />
                        </List.Item>
                      )}
                    />
                  ) : (
                    <Empty
                      description={
                        loading ? '' :
                          error ? '加载失败，请检查错误信息' :
                          isZeroObjects ? '暂无对象数据' :
                          '未找到匹配的对象'
                      }
                      style={{ marginTop: 60 }}
                    />
                  )}
                </Spin>
              </div>
            </Col>

            {/* 右侧对象详情 */}
            <Col span={14} style={{ height: '100%', overflow: 'auto' }}>
              <Spin spinning={detailLoading} tip="加载详情...">
                {selectedObjectDetail ? (
                  <div style={{ padding: 16 }}>
                    <Space direction="vertical" size="large" style={{ width: '100%' }}>
                      {/* 基本信息 */}
                      <div>
                        <Title level={5} style={{ marginBottom: 8 }}>
                          <InfoCircleOutlined /> 基本信息
                        </Title>
                        <Row gutter={[16, 8]}>
                          <Col span={12}>
                            <Text type="secondary">OBIS 码:</Text>
                          </Col>
                          <Col span={12}>
                            <Text code copyable>{selectedObjectDetail.obis}</Text>
                          </Col>
                          <Col span={12}>
                            <Text type="secondary">名称:</Text>
                          </Col>
                          <Col span={12}>
                            <Text strong>{selectedObjectDetail.name}</Text>
                          </Col>
                          <Col span={12}>
                            <Text type="secondary">接口类:</Text>
                          </Col>
                          <Col span={12}>
                            <Space>
                              <Tag color="blue">Class {selectedObjectDetail.class_id}</Tag>
                              <Text>{getClassName(selectedObjectDetail.class_id)}</Text>
                            </Space>
                          </Col>
                          {selectedObjectDetail.version && (
                            <>
                              <Col span={12}>
                                <Text type="secondary">版本:</Text>
                              </Col>
                              <Col span={12}>
                                <Text>{selectedObjectDetail.version}</Text>
                              </Col>
                            </>
                          )}
                          <Col span={12}>
                            <Text type="secondary">属性数量:</Text>
                          </Col>
                          <Col span={12}>
                            <Text>{selectedObjectDetail.attributes.length}</Text>
                          </Col>
                          <Col span={12}>
                            <Text type="secondary">方法数量:</Text>
                          </Col>
                          <Col span={12}>
                            <Text>{selectedObjectDetail.methods.length}</Text>
                          </Col>
                        </Row>
                      </div>

                      <Divider style={{ margin: '8px 0' }} />

                      {/* 属性列表 */}
                      <div>
                        <Title level={5} style={{ marginBottom: 8 }}>
                          <CodeOutlined /> 属性列表
                          <Tag color="blue" style={{ marginLeft: 8 }}>
                            {selectedObjectDetail.attributes.length} 个属性
                          </Tag>
                        </Title>
                        {selectedObjectDetail.attributes.length > 0 ? (
                          <Table
                            size="small"
                            dataSource={selectedObjectDetail.attributes}
                            columns={attributeColumns}
                            rowKey="attribute_id"
                            pagination={false}
                            bordered
                          />
                        ) : (
                          <Empty description="无属性" style={{ marginTop: 20 }} />
                        )}
                      </div>

                      <Divider style={{ margin: '8px 0' }} />

                      {/* 方法列表 */}
                      <div>
                        <Title level={5} style={{ marginBottom: 8 }}>
                          <ThunderboltOutlined /> 方法列表
                          <Tag color="green" style={{ marginLeft: 8 }}>
                            {selectedObjectDetail.methods.length} 个方法
                          </Tag>
                        </Title>
                        {selectedObjectDetail.methods.length > 0 ? (
                          <Table
                            size="small"
                            dataSource={selectedObjectDetail.methods}
                            columns={methodColumns}
                            rowKey="method_id"
                            pagination={false}
                            bordered
                          />
                        ) : (
                          <Empty description="无方法" style={{ marginTop: 20 }} />
                        )}
                      </div>
                    </Space>
                  </div>
                ) : (
                  <Empty
                    image={<DatabaseOutlined style={{ fontSize: 64, color: '#d9d9d9' }} />}
                    description={selectedObject ? '正在加载对象详情...' : '请选择一个对象查看详情'}
                    style={{ marginTop: 100 }}
                  />
                )}
              </Spin>
            </Col>
          </Row>
        )}
      </Card>

      {/* GitHub 导入对话框 */}
      <Modal
        title={
          <Space>
            <GithubOutlined />
            <span>从 GitHub 导入数据模型</span>
          </Space>
        }
        open={githubModalVisible}
        onOk={handleGithubImport}
        onCancel={() => setGithubModalVisible(false)}
        confirmLoading={importingGithub}
        okText="导入"
        cancelText="取消"
        width={600}
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Text type="secondary">
              输入 GitHub Raw 文件 URL，系统将自动下载并解析 COSEM 数据模型 Excel 文件。
            </Text>
          </div>
          <Input
            value={githubUrl}
            onChange={(e) => setGithubUrl(e.target.value)}
            placeholder="https://raw.githubusercontent.com/.../xxx.xlsx"
            size="large"
            onPressEnter={handleGithubImport}
          />
          <Alert
            message="快速使用"
            description={
              <div>
                <div>默认使用本仓库内置的示例数据模型，包含常用 COSEM 对象（电表类）。</div>
                <div style={{ marginTop: 4, fontSize: 12, color: '#666' }}>
                  提示：GitHub 文件 URL 需要是 raw 格式（raw.githubusercontent.com）
                </div>
              </div>
            }
            type="info"
            showIcon
          />
        </Space>
      </Modal>
    </div>
  )
}

export default DataModelPage
