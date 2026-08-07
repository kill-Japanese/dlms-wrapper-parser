import { Button, Space, Segmented, message } from 'antd'
import {
  PlayCircleOutlined,
  ExportOutlined,
  SwapOutlined,
  ClearOutlined
} from '@ant-design/icons'
import useParserStore from '../../store/parserStore.js'
import useLogStore from '../../store/logStore.js'
import { parseHex, buildFrame, packageApdu } from '../../services/parser.js'

function ParseControls() {
  const {
    rawHex,
    direction,
    setDirection,
    setParseResult,
    setLoading,
    loading,
    setError,
    securityConfig,
    addToHistory,
    reset,
    autoFillFromParseResult
  } = useParserStore()

  const { addParseLog, setParseLogs } = useLogStore()

  // 检查解析结果是否有效（至少 wrapper 层或 APDU 层解析成功）
  const hasValidParseResult = (result) => {
    if (!result || typeof result !== 'object') {
      return false
    }
    // wrapper 层有效
    if (result.wrapper && typeof result.wrapper === 'object' && Object.keys(result.wrapper).length > 0) {
      return true
    }
    // 或者 APDU 层有效（直接解析原始APDU，无Wrapper）
    if (result.apdu && typeof result.apdu === 'object' && Object.keys(result.apdu).length > 0) {
      return true
    }
    return false
  }

  // 获取解析错误详情
  const getParseErrorMessage = (result) => {
    if (!result || typeof result !== 'object') {
      return '服务器返回数据格式错误'
    }
    // 优先使用 result 中的错误信息
    if (result.error) {
      return result.error
    }
    if (result.message) {
      return result.message
    }
    if (result.errors && result.errors.length > 0) {
      return result.errors.join('; ')
    }
    if (!result.wrapper && !result.apdu) {
      return '无法解析帧格式：未检测到有效的 Wrapper 帧或 APDU 数据'
    }
    return '解析失败：未识别的帧格式'
  }

  const handleParse = async () => {
    if (!rawHex.trim()) {
      message.warning('请先输入十六进制数据')
      return
    }

    setLoading(true)
    setError(null)
    try {
      // 调用后端解析API，传递所有安全配置参数
      const result = await parseHex(rawHex, securityConfig)
      console.log('Parse result:', result)
      console.log('Parse result - wrapper:', result?.wrapper)
      console.log('Parse result - ciphering:', result?.ciphering)
      console.log('Parse result - compression:', result?.compression)
      console.log('Parse result - apdu:', result?.apdu)

      // 检查解析结果是否有效
      if (!hasValidParseResult(result)) {
        const errorMsg = getParseErrorMessage(result)
        console.error('Parse failed - invalid result:', result)

        // 即使失败也保存结果，以便 LayerView 显示错误详情
        setParseResult(result)
        setError(errorMsg)

        addToHistory({
          hex: rawHex.substring(0, 50) + (rawHex.length > 50 ? '...' : ''),
          direction,
          success: false
        })

        // 记录错误日志
        addParseLog({
          level: 'error',
          step: 'parse',
          message: errorMsg
        })

        // 显示详细的错误信息
        const errorDetail = result?.errors && result.errors.length > 0
          ? `${errorMsg}\n\n错误详情：\n${result.errors.map((e, i) => `${i + 1}. ${e}`).join('\n')}`
          : errorMsg
        message.error(errorDetail, 5)
        return
      }

      // 解析成功 - 保存结果
      setParseResult(result)
      setError(null)
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
          level: result.errors && result.errors.length > 0 ? 'warning' : 'info',
          step: 'complete',
          message: result.errors && result.errors.length > 0
            ? `解析完成，有 ${result.errors.length} 个警告`
            : '解析成功'
        })
      }

      // 根据是否有警告显示不同消息
      if (result.errors && result.errors.length > 0) {
        message.warning(`解析完成，但有 ${result.errors.length} 个警告`)
      } else {
        message.success('解析成功')
      }
    } catch (error) {
      console.error('Parse error:', error)

      // 区分不同类型的错误
      let errorMsg = error.message || '解析失败'
      if (error.status === 404) {
        errorMsg = '接口不存在，请检查后端版本是否支持解析功能'
      } else if (error.status === 500) {
        errorMsg = `服务器错误：${error.message || '未知错误'}`
      } else if (!error.status) {
        errorMsg = '无法连接到后端服务，请检查后端是否启动'
      }

      setError(errorMsg)
      message.error(errorMsg, 5)

      // 记录错误日志
      addParseLog({
        level: 'error',
        step: 'parse',
        message: errorMsg
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
      // 判断输入是否为原始APDU hex数据（以已知APDU tag开头）
      // 按IEC 62056-6 / Gurux标准:
      // GetRequest=0xC0, SetRequest=0xC1, EventNotification=0xC2, ActionRequest=0xC3,
      // GetResponse=0xC4, SetResponse=0xC5, ActionResponse=0xC7,
      // DataNotification=0x0F
      const hexStr = rawHex.trim().replace(/\s/g, '')
      const firstByte = parseInt(hexStr.substring(0, 2), 16)
      const isRawApdu = [0x0F, 0xC0, 0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xC7].includes(firstByte)

      let result
      if (isRawApdu) {
        // 原始APDU打包：V.44压缩 + AES-GCM加密 + Wrapper封装
        const needsEncryption = securityConfig.useCiphering
        const needsCompression = securityConfig.useCompression

        if (needsEncryption && !securityConfig.systemTitle) {
          message.error('加密打包需要提供系统标题(System Title)')
          setLoading(false)
          return
        }

        result = await packageApdu(hexStr, {
          compress: needsCompression,
          encrypt: needsEncryption,
          systemTitle: securityConfig.systemTitle || '0000000000000000',
          guek: securityConfig.guek,
          gubk: securityConfig.gubk,
          ak: securityConfig.ak,
          invocationCounter: securityConfig.invocationCounter,
          keyId: securityConfig.selectedKeyType === 'gubk' ? 1 : 0,
          withWrapper: false,
        })
      } else {
        // 通过APDU类型+参数构建
        result = await buildFrame(
          'DataNotification',
          {},
          {
            srcWPort: 1,
            dstWPort: 16,
            encrypt: securityConfig.useCiphering,
            compress: securityConfig.useCompression,
            guek: securityConfig.guek,
            gubk: securityConfig.gubk,
            ak: securityConfig.ak,
            kek: securityConfig.kek,
            systemTitle: securityConfig.systemTitle,
            invocationCounter: securityConfig.invocationCounter,
            keyId: securityConfig.selectedKeyType === 'gubk' ? 1 : 0
          }
        )
      }

      if (result.success) {
        message.success('打包成功')
        setParseResult({
          raw_hex: result.hex_data,
          frame_length: result.frame_length,
          apdu_hex: result.apdu_hex || '',
          compress: result.compress,
          encrypt: result.encrypt,
          sc_flags: result.sc_flags || '',
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
      let errorMsg = error.message || '打包失败'
      if (error.status === 404) {
        errorMsg = '接口不存在，请检查后端版本'
      } else if (!error.status) {
        errorMsg = '无法连接到后端服务，请检查后端是否启动'
      }
      message.error(errorMsg, 5)
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
