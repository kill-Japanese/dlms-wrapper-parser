import { Button, Space, Segmented, message } from 'antd'
import {
  PlayCircleOutlined,
  ExportOutlined,
  SwapOutlined,
  ClearOutlined
} from '@ant-design/icons'
import useParserStore from '../../store/parserStore.js'
import useLogStore from '../../store/logStore.js'
import { parseHex, buildFrame } from '../../services/parser.js'

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
    reset,
    autoFillFromParseResult
  } = useParserStore()

  const { addParseLog, setParseLogs } = useLogStore()

  const handleParse = async () => {
    if (!rawHex.trim()) {
      message.warning('请先输入十六进制数据')
      return
    }

    setLoading(true)
    try {
      // 调用后端解析API，传递所有安全配置参数
      const result = await parseHex(rawHex, securityConfig)

      setParseResult(result)
      addToHistory({
        hex: rawHex.substring(0, 50) + (rawHex.length > 50 ? '...' : ''),
        direction,
        success: true
      })

      // 从解析结果中自动回填 System Title 和 Invocation Counter
      autoFillFromParseResult(result)

      // 将解析日志添加到日志store
      if (result.parse_logs && result.parse_logs.length > 0) {
        const logs = result.parse_logs.map((log, index) => ({
          id: Date.now() + index,
          timestamp: log.timestamp || new Date().toISOString(),
          level: log.level || 'info',
          step: log.step || '',
          message: log.message || ''
        }))
        setParseLogs(logs)
      } else {
        // 如果没有详细日志，添加一条总结日志
        addParseLog({
          level: 'info',
          step: 'complete',
          message: result.errors && result.errors.length > 0
            ? `解析完成，有 ${result.errors.length} 个警告`
            : '解析成功'
        })
      }

      if (result.errors && result.errors.length > 0) {
        message.warning(`解析完成，但有 ${result.errors.length} 个警告`)
      } else {
        message.success('解析成功')
      }
    } catch (error) {
      message.error(error.message || '解析失败')
      console.error('Parse error:', error)
      // 记录错误日志
      addParseLog({
        level: 'error',
        step: 'parse',
        message: error.message || '解析失败'
      })
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
      // 调用后端组帧API
      const result = await buildFrame(
        'DataNotification',
        {},
        {
          srcWPort: 1,
          dstWPort: 16,
          encrypt: securityConfig.useCiphering,
          guek: securityConfig.guek,
          gubk: securityConfig.gubk,
          ak: securityConfig.ak,
          kek: securityConfig.kek,
          systemTitle: securityConfig.systemTitle,
          invocationCounter: securityConfig.invocationCounter,
          keyId: securityConfig.selectedKeyType === 'gubk' ? 1 : 0
        }
      )

      if (result.success) {
        message.success('打包成功')
        setParseResult({
          raw_hex: result.hex_data,
          frame_length: result.frame_length
        })
        addToHistory({
          hex: result.hex_data.substring(0, 50) + (result.hex_data.length > 50 ? '...' : ''),
          direction,
          success: true
        })
      } else {
        message.error(result.message || '打包失败')
      }
    } catch (error) {
      message.error(error.message || '打包失败')
      console.error('Pack error:', error)
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
