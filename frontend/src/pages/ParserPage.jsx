import { Row, Col, Card, Space, Divider, Typography } from 'antd'
import { SecurityScanOutlined } from '@ant-design/icons'
import HexInput from '../components/parser/HexInput.jsx'
import ParseControls from '../components/parser/ParseControls.jsx'
import LayerView from '../components/parser/LayerView.jsx'
import useParserStore from '../store/parserStore.js'

const { Title, Text } = Typography

function ParserPage() {
  const { securityConfig, updateSecurityConfig, direction } = useParserStore()

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
            <div>
              <Space align="center" style={{ marginBottom: 12 }}>
                <SecurityScanOutlined />
                <Text strong>安全配置</Text>
              </Space>
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <Space.Compact style={{ width: '100%' }}>
                  <span style={{ width: 100, display: 'inline-flex', alignItems: 'center' }}>
                    密钥:
                  </span>
                  <input
                    type="text"
                    placeholder="Block Cipher Key"
                    value={securityConfig.blockCipherKey}
                    onChange={(e) => updateSecurityConfig({ blockCipherKey: e.target.value })}
                    style={{ flex: 1, padding: '4px 8px', border: '1px solid #d9d9d9', borderRadius: 4 }}
                  />
                </Space.Compact>
                <Space.Compact style={{ width: '100%' }}>
                  <span style={{ width: 100, display: 'inline-flex', alignItems: 'center' }}>
                    System Title:
                  </span>
                  <input
                    type="text"
                    placeholder="System Title"
                    value={securityConfig.systemTitle}
                    onChange={(e) => updateSecurityConfig({ systemTitle: e.target.value })}
                    style={{ flex: 1, padding: '4px 8px', border: '1px solid #d9d9d9', borderRadius: 4 }}
                  />
                </Space.Compact>
                <Space.Compact style={{ width: '100%' }}>
                  <span style={{ width: 100, display: 'inline-flex', alignItems: 'center' }}>
                    计数器:
                  </span>
                  <input
                    type="number"
                    placeholder="Invocation Counter"
                    value={securityConfig.invocationCounter}
                    onChange={(e) => updateSecurityConfig({ invocationCounter: parseInt(e.target.value) || 0 })}
                    style={{ flex: 1, padding: '4px 8px', border: '1px solid #d9d9d9', borderRadius: 4 }}
                  />
                </Space.Compact>
                <Space>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <input
                      type="checkbox"
                      checked={securityConfig.useCiphering}
                      onChange={(e) => updateSecurityConfig({ useCiphering: e.target.checked })}
                    />
                    启用加密
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <input
                      type="checkbox"
                      checked={securityConfig.useCompression}
                      onChange={(e) => updateSecurityConfig({ useCompression: e.target.checked })}
                    />
                    启用压缩
                  </label>
                </Space>
              </Space>
            </div>
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
