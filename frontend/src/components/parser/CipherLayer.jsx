import { Descriptions, Tag, Typography, Space, Row, Col } from 'antd'
import { LockOutlined, KeyOutlined, SafetyOutlined } from '@ant-design/icons'
import HexViewer from '../common/HexViewer.jsx'

const { Text } = Typography

function CipherLayer({ data }) {
  if (!data) return null

  const {
    enabled,
    securityControl,
    systemTitle,
    invocationCounter,
    keyId,
    decrypted,
    authenticationKey,
    blockCipherKey
  } = data

  return (
    <div>
      <Space style={{ marginBottom: 12 }}>
        {decrypted ? (
          <Tag color="success" icon={<SafetyOutlined />}>已解密</Tag>
        ) : (
          <Tag color="warning" icon={<LockOutlined />}>未解密</Tag>
        )}
        <Text type="secondary">安全控制: {securityControl}</Text>
      </Space>

      <Descriptions size="small" column={2} bordered>
        <Descriptions.Item label="安全控制字节">
          <Text code>{securityControl}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="密钥ID">
          <Tag>{keyId}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="System Title" span={2}>
          <Text code copyable>{systemTitle}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="Invocation Counter" span={2}>
          <Text code>{invocationCounter}</Text>
        </Descriptions.Item>
      </Descriptions>

      {systemTitle && (
        <div style={{ marginTop: 12 }}>
          <Row gutter={[8, 8]}>
            <Col span={12}>
              <Text type="secondary" style={{ fontSize: 12 }}>System Title:</Text>
              <HexViewer hex={systemTitle} style={{ marginTop: 4 }} />
            </Col>
            <Col span={12}>
              <Text type="secondary" style={{ fontSize: 12 }}>Invocation Counter:</Text>
              <HexViewer
                hex={invocationCounter?.toString(16).padStart(8, '0') || ''}
                style={{ marginTop: 4 }}
              />
            </Col>
          </Row>
        </div>
      )}

      {(blockCipherKey || authenticationKey) && (
        <div style={{ marginTop: 12, padding: 8, background: '#fffbe6', borderRadius: 4 }}>
          <Space>
            <KeyOutlined style={{ color: '#faad14' }} />
            <Text type="secondary" style={{ fontSize: 12 }}>
              使用配置的密钥进行解密
            </Text>
          </Space>
        </div>
      )}
    </div>
  )
}

export default CipherLayer
