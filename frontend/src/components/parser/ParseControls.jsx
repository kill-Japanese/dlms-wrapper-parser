import { Button, Space, Segmented, message } from 'antd'
import {
  PlayCircleOutlined,
  ExportOutlined,
  SwapOutlined,
  ClearOutlined
} from '@ant-design/icons'
import useParserStore from '../../store/parserStore.js'
import { parseWrapper, packWrapper } from '../../services/parser.js'

function ParseControls() {
  const {
    rawHex,
    direction,
    setDirection,
    setParseResult,
    setLoading,
    loading,
    securityConfig,
    addToHistory,
    reset
  } = useParserStore()

  const handleParse = async () => {
    if (!rawHex.trim()) {
      message.warning('请先输入十六进制数据')
      return
    }

    setLoading(true)
    try {
      // 模拟解析过程
      await new Promise((resolve) => setTimeout(resolve, 500))

      // 模拟解析结果
      const mockResult = {
        success: true,
        wrapper: {
          version: 1,
          srcWPort: 1,
          dstWPort: 16,
          length: 256,
          header: 'E6E700'
        },
        cipher: {
          enabled: securityConfig.useCiphering,
          securityControl: '10',
          systemTitle: securityConfig.systemTitle || '534D535800000000',
          invocationCounter: securityConfig.invocationCounter || 1,
          keyId: 0,
          decrypted: securityConfig.useCiphering
        },
        compression: {
          enabled: securityConfig.useCompression,
          algorithm: 'gzip',
          originalSize: 320,
          compressedSize: 208,
          ratio: 0.65
        },
        apdu: {
          type: 'GET-RESPONSE',
          data: {
            invokeId: 1,
            result: 'success',
            data: {
              type: 'structure',
              value: [
                { type: 'long-unsigned', value: 1, name: 'Attribute' },
                { type: 'double-long-unsigned', value: 12345, name: 'Value' }
              ]
            }
          }
        }
      }

      setParseResult(mockResult)
      addToHistory({
        hex: rawHex.substring(0, 50) + '...',
        direction,
        success: true
      })
      message.success('解析成功')
    } catch (error) {
      message.error(error.message || '解析失败')
    } finally {
      setLoading(false)
    }
  }

  const handlePack = async () => {
    if (!rawHex.trim()) {
      message.warning('请先输入数据')
      return
    }

    setLoading(true)
    try {
      // 模拟打包过程
      await new Promise((resolve) => setTimeout(resolve, 500))
      message.success('打包成功')
    } catch (error) {
      message.error(error.message || '打包失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSwapDirection = () => {
    setDirection(direction === 'unpack' ? 'pack' : 'unpack')
  }

  const handleClear = () => {
    reset()
    message.info('已清空')
  }

  const handleAction = () => {
    if (direction === 'unpack') {
      handleParse()
    } else {
      handlePack()
    }
  }

  return (
    <Space direction="vertical" size="small" style={{ width: '100%' }}>
      <Space style={{ width: '100%' }}>
        <Segmented
          value={direction}
          onChange={setDirection}
          options={[
            { label: '解包', value: 'unpack' },
            { label: '打包', value: 'pack' }
          ]}
        />
        <Button
          icon={<SwapOutlined />}
          onClick={handleSwapDirection}
          size="small"
        />
        <div style={{ flex: 1 }} />
        <Button icon={<ClearOutlined />} onClick={handleClear} size="small">
          清空
        </Button>
      </Space>

      <Button
        type="primary"
        icon={direction === 'unpack' ? <PlayCircleOutlined /> : <ExportOutlined />}
        onClick={handleAction}
        loading={loading}
        block
        size="large"
      >
        {direction === 'unpack' ? '解析' : '打包'}
      </Button>
    </Space>
  )
}

export default ParseControls
