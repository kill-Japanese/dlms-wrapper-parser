import { useState } from 'react'
import { Row, Col, Card, Space, Divider, Typography, Collapse, Select, InputNumber, Checkbox, Tooltip, Input } from 'antd'
import {
  SecurityScanOutlined,
  DownOutlined,
  UpOutlined,
  KeyOutlined,
  SafetyCertificateOutlined,
  LockOutlined,
  UnlockOutlined
} from '@ant-design/icons'
import HexInput from '../components/parser/HexInput.jsx'
import ParseControls from '../components/parser/ParseControls.jsx'
import LayerView from '../components/parser/LayerView.jsx'
import useParserStore from '../store/parserStore.js'

const { Title, Text } = Typography
const { Panel } = Collapse
const { Option } = Select
const { Password } = Input

// 密钥类型选项
const KEY_TYPE_OPTIONS = [
  { value: 'guek', label: 'GUEK (单播加密密钥)' },
  { value: 'gubk', label: 'GUBK (广播密钥)' },
  { value: 'custom', label: '自定义' }
]

// 密钥字段配置
const KEY_FIELDS = [
  {
    key: 'guek',
    label: 'GUEK',
    fullName: 'Global Unicast Encryption Key',
    description: '全局单播加密密钥，用于单播通信加密解密',
    placeholder: '输入GUEK密钥（十六进制）'
  },
  {
    key: 'gubk',
    label: 'GUBK',
    fullName: 'Global Unicast Broadcast Key',
    description: '广播密钥，用于广播通信加密解密',
    placeholder: '输入GUBK密钥（十六进制）'
  },
  {
    key: 'ak',
    label: 'AK',
    fullName: 'Authentication Key',
    description: '认证密钥，用于消息认证',
    placeholder: '输入AK认证密钥（十六进制）'
  },
  {
    key: 'kek',
    label: 'KEK',
    fullName: 'Key Encryption Key',
    description: '密钥加密密钥，用于加密保护其他密钥',
    placeholder: '输入KEK密钥加密密钥（十六进制）'
  }
]

function SecurityConfigPanel() {
  const { securityConfig, updateSecurityConfig, securityPanelExpanded, toggleSecurityPanel } = useParserStore()

  const handleKeyTypeChange = (value) => {
    updateSecurityConfig({ selectedKeyType: value })
  }

  const handleKeyChange = (field, value) => {
    updateSecurityConfig({ [field]: value })
  }

  const handleCheckboxChange = (field, checked) => {
    updateSecurityConfig({ [field]: checked })
  }

  const genExtra = () => (
    <span
      onClick={(e) => {
        e.stopPropagation()
        toggleSecurityPanel()
      }}
      style={{ cursor: 'pointer' }}
    >
      {securityPanelExpanded ? <UpOutlined /> : <DownOutlined />}
    </span>
  )

  return (
    <Collapse
      activeKey={securityPanelExpanded ? ['security'] : []}
      onChange={() => toggleSecurityPanel()}
      ghost
      style={{ background: 'transparent' }}
    >
      <Panel
        header={
          <Space align="center">
            <SecurityScanOutlined />
            <Text strong>安全配置</Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              ({KEY_FIELDS.filter(f => securityConfig[f.key]).length} 个密钥已配置)
            </Text>
          </Space>
        }
        key="security"
        extra={genExtra()}
        style={{ border: 'none' }}
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          {/* 密钥类型选择 */}
          <div>
            <Space.Compact style={{ width: '100%' }}>
              <span style={{
                width: 100,
                display: 'inline-flex',
                alignItems: 'center',
                fontSize: 13
              }}>
                <KeyOutlined style={{ marginRight: 4 }} />
                密钥类型:
              </span>
              <Select
                value={securityConfig.selectedKeyType}
                onChange={handleKeyTypeChange}
                style={{ flex: 1 }}
                size="small"
                options={KEY_TYPE_OPTIONS}
              />
            </Space.Compact>
          </div>

          {/* 密钥输入区域 */}
          <div style={{
            padding: '8px 12px',
            background: '#fafafa',
            borderRadius: 6,
            border: '1px solid #f0f0f0'
          }}>
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              {KEY_FIELDS.map((field) => {
                // 根据选中的密钥类型决定显示哪些字段
                const isSelectedType = securityConfig.selectedKeyType === field.key
                const showField = securityConfig.selectedKeyType === 'custom' ||
                  field.key === 'guek' ||
                  field.key === securityConfig.selectedKeyType

                if (!showField) return null

                return (
                  <Tooltip
                    key={field.key}
                    title={`${field.fullName} - ${field.description}`}
                    placement="right"
                  >
                    <Space.Compact style={{ width: '100%' }}>
                      <span style={{
                        width: 80,
                        display: 'inline-flex',
                        alignItems: 'center',
                        fontSize: 12,
                        fontWeight: isSelectedType ? 600 : 400,
                        color: isSelectedType ? '#1677ff' : 'inherit'
                      }}>
                        {field.label}:
                      </span>
                      <Password
                        value={securityConfig[field.key]}
                        onChange={(e) => handleKeyChange(field.key, e.target.value)}
                        placeholder={field.placeholder}
                        size="small"
                        style={{ flex: 1 }}
                        iconRender={(visible) => (visible ? <UnlockOutlined /> : <LockOutlined />)}
                      />
                    </Space.Compact>
                  </Tooltip>
                )
              })}
            </Space>
          </div>

          {/* System Title 和 Invocation Counter */}
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <Space.Compact style={{ width: '100%' }}>
              <span style={{
                width: 100,
                display: 'inline-flex',
                alignItems: 'center',
                fontSize: 13
              }}>
                <SafetyCertificateOutlined style={{ marginRight: 4 }} />
                System Title:
              </span>
              <Input
                value={securityConfig.systemTitle}
                onChange={(e) => updateSecurityConfig({ systemTitle: e.target.value })}
                placeholder="系统标题（十六进制，8字节）"
                size="small"
                style={{ flex: 1 }}
              />
            </Space.Compact>

            <Space.Compact style={{ width: '100%' }}>
              <span style={{
                width: 100,
                display: 'inline-flex',
                alignItems: 'center',
                fontSize: 13
              }}>
                Invocation Counter:
              </span>
              <InputNumber
                value={securityConfig.invocationCounter}
                onChange={(value) => updateSecurityConfig({ invocationCounter: value || 0 })}
                min={0}
                size="small"
                style={{ flex: 1 }}
              />
            </Space.Compact>
          </Space>

          {/* 启用加密 / 启用压缩 */}
          <Space style={{ width: '100%', justifyContent: 'space-around' }}>
            <Checkbox
              checked={securityConfig.useCiphering}
              onChange={(e) => handleCheckboxChange('useCiphering', e.target.checked)}
            >
              启用加密
            </Checkbox>
            <Checkbox
              checked={securityConfig.useCompression}
              onChange={(e) => handleCheckboxChange('useCompression', e.target.checked)}
            >
              启用压缩
            </Checkbox>
          </Space>
        </Space>
      </Panel>
    </Collapse>
  )
}

function ParserPage() {
  const { direction } = useParserStore()

  return (
    <div className="page-container">
      <Row gutter={[16, 16]} style={{ height: '100%' }}>
        {/* 左侧面板 */}
        <Col xs={24} lg={10} xl={8}>
          <Card
            title={
              <Space>
                <Title level={5} style={{ margin: 0 }}>
                  {direction === 'unpack' ? '十六进制输入' : '数据打包'}
                </Title>
              </Space>
            }
            style={{ height: '100%' }}
            bodyStyle={{ height: 'calc(100% - 57px)', display: 'flex', flexDirection: 'column' }}
          >
            {/* Hex输入区 */}
            <div style={{ flex: 1, minHeight: 0, marginBottom: 16 }}>
              <HexInput />
            </div>

            {/* 解析控制按钮 */}
            <ParseControls />

            <Divider style={{ margin: '16px 0' }} />

            {/* 安全配置面板 */}
            <SecurityConfigPanel />
          </Card>
        </Col>

        {/* 右侧解析结果 */}
        <Col xs={24} lg={14} xl={16}>
          <Card
            title={
              <Title level={5} style={{ margin: 0 }}>
                解析结果
              </Title>
            }
            style={{ height: '100%' }}
            bodyStyle={{ height: 'calc(100% - 57px)', overflow: 'auto' }}
          >
            <LayerView />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default ParserPage
