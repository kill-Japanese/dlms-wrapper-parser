import { useState } from 'react'
import { Row, Col, Card, Space, Divider, Typography, Collapse, Select, InputNumber, Checkbox, Tooltip, Input, Tag, Alert } from 'antd'
import {
  SecurityScanOutlined,
  DownOutlined,
  UpOutlined,
  KeyOutlined,
  SafetyCertificateOutlined,
  LockOutlined,
  UnlockOutlined,
  SyncOutlined
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
  { value: 'guek', label: 'GUEK (EK - 单播加密密钥)' },
  { value: 'gubk', label: 'GUBK (广播加密密钥)' },
  { value: 'custom', label: '自定义 / 全部密钥' }
]

// 密钥字段配置 - 明确区分 EK（加密密钥）和 AK（认证密钥）
const KEY_FIELDS = [
  {
    key: 'guek',
    label: 'GUEK (EK)',
    fullName: 'Global Unicast Encryption Key',
    description: '全局单播加密密钥 (EK) - 用于单播通信的数据加密/解密，对应SC字节bit 0',
    placeholder: '输入GUEK加密密钥（十六进制，16字节）',
    category: 'encryption'
  },
  {
    key: 'gubk',
    label: 'GUBK (EK)',
    fullName: 'Global Unicast Broadcast Key',
    description: '广播加密密钥 (EK) - 用于广播通信的数据加密/解密，对应SC字节bit 3-4=01',
    placeholder: '输入GUBK广播加密密钥（十六进制，16字节）',
    category: 'encryption'
  },
  {
    key: 'ak',
    label: 'AK',
    fullName: 'Authentication Key',
    description: '认证密钥 (AK) - 用于消息认证和GMAC标签验证，对应SC字节bit 1',
    placeholder: '输入AK认证密钥（十六进制，16字节）',
    category: 'authentication'
  },
  {
    key: 'kek',
    label: 'KEK',
    fullName: 'Key Encryption Key',
    description: '密钥加密密钥 - 用于加密保护其他密钥（如密钥交换时）',
    placeholder: '输入KEK密钥加密密钥（十六进制，16字节）',
    category: 'other'
  }
]

function SecurityConfigPanel() {
  const {
    securityConfig,
    updateSecurityConfig,
    securityPanelExpanded,
    toggleSecurityPanel,
    parseResult
  } = useParserStore()

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

  // 从解析结果中提取的ST/IC信息
  const extractedSt = parseResult?.ciphering?.system_title
  const extractedIc = parseResult?.ciphering?.invocation_counter
  const hasExtractedInfo = parseResult?.ciphering?.extracted_from_frame && extractedSt

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
          {/* 从帧中提取信息的提示 */}
          {hasExtractedInfo && (
            <Alert
              message={
                <Space>
                  <SyncOutlined spin={false} />
                  <span>
                    从帧中提取: <Tag color="blue">ST: {extractedSt}</Tag>
                    <Tag color="green">IC: {extractedIc}</Tag>
                    {securityConfig.autoFillFromFrame && (
                      <Tag color="cyan">已自动回填</Tag>
                    )}
                  </span>
                </Space>
              }
              type="info"
              showIcon={false}
              size="small"
              style={{ padding: '6px 12px' }}
            />
          )}

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

          {/* 加密密钥 (EK) 区域 */}
          <div style={{
            padding: '8px 12px',
            background: '#f0f7ff',
            borderRadius: 6,
            border: '1px solid #bae0ff'
          }}>
            <Text type="secondary" style={{ fontSize: 12, fontWeight: 600 }}>
              <LockOutlined style={{ marginRight: 4 }} />
              加密密钥 (EK - Encryption Key)
            </Text>
            <Space direction="vertical" size="small" style={{ width: '100%', marginTop: 8 }}>
              {KEY_FIELDS.filter(f => f.category === 'encryption').map((field) => {
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
                        width: 100,
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

          {/* 认证密钥 (AK) 区域 */}
          <div style={{
            padding: '8px 12px',
            background: '#f6ffed',
            borderRadius: 6,
            border: '1px solid #b7eb8f'
          }}>
            <Text type="secondary" style={{ fontSize: 12, fontWeight: 600 }}>
              <SafetyCertificateOutlined style={{ marginRight: 4 }} />
              认证密钥 (AK - Authentication Key)
            </Text>
            <Space direction="vertical" size="small" style={{ width: '100%', marginTop: 8 }}>
              {KEY_FIELDS.filter(f => f.category === 'authentication').map((field) => {
                const showField = securityConfig.selectedKeyType === 'custom' ||
                  field.key === 'ak' ||
                  securityConfig.useCiphering  // 加密时通常需要AK

                if (!showField) return null

                return (
                  <Tooltip
                    key={field.key}
                    title={`${field.fullName} - ${field.description}`}
                    placement="right"
                  >
                    <Space.Compact style={{ width: '100%' }}>
                      <span style={{
                        width: 100,
                        display: 'inline-flex',
                        alignItems: 'center',
                        fontSize: 12,
                        fontWeight: 500
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

          {/* KEK - 其他密钥 */}
          {securityConfig.selectedKeyType === 'custom' && (
            <div style={{
              padding: '8px 12px',
              background: '#fffbe6',
              borderRadius: 6,
              border: '1px solid #ffe58f'
            }}>
              <Text type="secondary" style={{ fontSize: 12, fontWeight: 600 }}>
                <KeyOutlined style={{ marginRight: 4 }} />
                其他密钥
              </Text>
              <Space direction="vertical" size="small" style={{ width: '100%', marginTop: 8 }}>
                {KEY_FIELDS.filter(f => f.category === 'other').map((field) => (
                  <Tooltip
                    key={field.key}
                    title={`${field.fullName} - ${field.description}`}
                    placement="right"
                  >
                    <Space.Compact style={{ width: '100%' }}>
                      <span style={{
                        width: 100,
                        display: 'inline-flex',
                        alignItems: 'center',
                        fontSize: 12
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
                ))}
              </Space>
            </div>
          )}

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

          {/* 启用选项 */}
          <Space style={{ width: '100%', justifyContent: 'space-around', flexWrap: 'wrap' }}>
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
            <Checkbox
              checked={securityConfig.autoFillFromFrame}
              onChange={(e) => handleCheckboxChange('autoFillFromFrame', e.target.checked)}
            >
              自动回填ST/IC
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
