import { Descriptions, Tag, Typography, Space, Row, Col } from 'antd'
import { LockOutlined, KeyOutlined, SafetyOutlined } from '@ant-design/icons'
import HexViewer from '../common/HexViewer.jsx'

const { Text } = Typography

function CipherLayer({ data }) {
  if (!data) return null

  // 后端返回 snake_case 字段名
  const {
    security_control,
    security_control_byte,
    system_title,
    invocation_counter,
    gmac_tag,
    decrypt_success,
    cipher_info,
    extracted_from_frame,
    ciphered_data_hex,
  } = data

  // 从 cipher_info 中提取详细信息
  const encrypted = cipher_info?.encrypted
  const authenticated = cipher_info?.authenticated
  const compressed = cipher_info?.compressed
  const key_id = cipher_info?.key_id ?? 0
  const suite_id = cipher_info?.suite_id ?? 1

  // 密钥ID描述
  const keyIdText = key_id === 0 ? 'GUEK (单播)' : key_id === 1 ? 'GUBK (广播)' : `Key ${key_id}`

  return (
    <div>
      <Space style={{ marginBottom: 12 }} wrap>
        {decrypt_success ? (
          <Tag color="success" icon={<SafetyOutlined />}>已解密</Tag>
        ) : (
          <Tag color="warning" icon={<LockOutlined />}>未解密</Tag>
        )}
        {encrypted && <Tag color="orange">加密</Tag>}
        {authenticated && <Tag color="green">认证</Tag>}
        {compressed && <Tag color="blue">压缩</Tag>}
        <Tag color="purple">Suite {suite_id}</Tag>
      </Space>

      <Descriptions size="small" column={2} bordered>
        <Descriptions.Item label="安全控制字节">
          <Text code>{security_control}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="密钥类型">
          <Tag>{keyIdText}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="System Title" span={2}>
          <Text code copyable>{system_title}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="Invocation Counter" span={2}>
          <Text code>{invocation_counter}</Text>
          {extracted_from_frame && (
            <Tag color="cyan" style={{ marginLeft: 8 }}>从帧中提取</Tag>
          )}
        </Descriptions.Item>
        {gmac_tag && (
          <Descriptions.Item label="GMAC Tag" span={2}>
            <Text code>{gmac_tag}</Text>
          </Descriptions.Item>
        )}
      </Descriptions>

      {system_title && (
        <div style={{ marginTop: 12 }}>
          <Row gutter={[8, 8]}>
            <Col span={12}>
              <Text type="secondary" style={{ fontSize: 12 }}>System Title:</Text>
              <HexViewer hex={system_title} style={{ marginTop: 4 }} />
            </Col>
            <Col span={12}>
              <Text type="secondary" style={{ fontSize: 12 }}>Invocation Counter:</Text>
              <HexViewer
                hex={invocation_counter?.toString(16).padStart(8, '0') || ''}
                style={{ marginTop: 4 }}
              />
            </Col>
          </Row>
        </div>
      )}

      {ciphered_data_hex && (
        <div style={{ marginTop: 12 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>加密数据:</Text>
          <HexViewer hex={ciphered_data_hex} style={{ marginTop: 4, maxHeight: 80, overflow: 'auto' }} />
        </div>
      )}
    </div>
  )
}

export default CipherLayer
