/**
 * 模拟帧数据
 *
 * 包含各种DLMS协议帧的测试数据，用于前端开发和演示。
 * 无需后端服务即可测试UI组件。
 */

// 测试密钥配置
export const mockSecurityConfig = {
  blockCipherKey: '00112233445566778899aabbccddeeff',
  systemTitle: '4953453131303733',
  invocationCounter: 1,
  authenticationKey: '',
}

// 模拟帧数据列表
export const mockFrames = [
  {
    id: 'plain-dn',
    name: '明文 DataNotification',
    description: '无加密无压缩的DataNotification帧，包含3个数据项（uint32、octet-string、structure）',
    type: 'DataNotification',
    security: 'plain',
    hex: '000100010010003d0f00000001013600030000010000ff0206040003827000010000600100ff0209081234567890abcdef00030100010800ff020209060400bc614e110112',
    length: 69,
  },
  {
    id: 'encrypted-dn',
    name: '加密 DataNotification',
    description: 'AES-GCM加密的DataNotification帧（认证+加密），需要密钥解密',
    type: 'DataNotification',
    security: 'encrypted',
    hex: '000100010010005b134953453131303733040000000149efceb37f5076070508d86460e0edfc588f86911116af7741fef95e4b3f0688320fa353ea19a5a8b3aabae7abbf31087770409afe663ed82e760c63a892d93f24a68a5afb158c76819373c13f',
    length: 99,
    key: mockSecurityConfig.blockCipherKey,
    systemTitle: mockSecurityConfig.systemTitle,
    invocationCounter: 1,
  },
  {
    id: 'compressed-dn',
    name: '加密+压缩 DataNotification',
    description: 'AES-GCM加密 + V.44压缩的DataNotification帧',
    type: 'DataNotification',
    security: 'encrypted+compressed',
    hex: '0001000100100054174953453131303733040000000158efc5b17c3d40018b4d195a61e61ad4560985b2f367f7dd02fc9d4d2398c582534824f2d8020e6d5c90b1aea3a79638c6504603e062a50b285dfe9ae407218b1d9ff3fdb57c',
    length: 92,
    key: mockSecurityConfig.blockCipherKey,
    systemTitle: mockSecurityConfig.systemTitle,
    invocationCounter: 1,
  },
  {
    id: 'get-request',
    name: 'GetRequest (明文)',
    description: '读取Register类(0-0:1.0.0.255)属性2的Get请求',
    type: 'GetRequest',
    security: 'plain',
    hex: '0001000100100010c0010000000100030000010000ff0200',
    length: 24,
  },
  {
    id: 'get-response',
    name: 'GetResponse (明文)',
    description: '返回uint32值(230000)的Get响应',
    type: 'GetResponse',
    security: 'plain',
    hex: '000100100001000dc1010000000100060400038270',
    length: 21,
  },
]

// 模拟解析结果（明文DataNotification）
export const mockParseResult = {
  frameId: 'mock-frame-001',
  timestamp: new Date().toISOString(),
  rawHex: mockFrames[0].hex,
  wrapper: {
    version: 1,
    src_wport: 1,
    dst_wport: 16,
    data_length: 61,
    payload_hex: '0f00000001013600030000010000ff0206040003827000010000600100ff0209081234567890abcdef00030100010800ff020209060400bc614e110112',
  },
  ciphering: null,
  compression: null,
  apdu: {
    tag: 15,
    type_name: 'DataNotification',
    invoke_id: 1,
    datetime: null,
    items: [
      {
        class_id: 3,
        obis: '0-0:1.0.0.255',
        attribute_id: 2,
        data_type: 'double-long-unsigned',
        value: 230000,
        raw_hex: '060400038270',
      },
      {
        class_id: 1,
        obis: '0-0:96.1.0.255',
        attribute_id: 2,
        data_type: 'octet-string',
        value: '1234567890abcdef',
        raw_hex: '09081234567890abcdef',
      },
      {
        class_id: 3,
        obis: '1-0:1.8.0.255',
        attribute_id: 2,
        data_type: 'structure',
        value: [12345678, 18],
        raw_hex: '0209060400bc614e110112',
      },
    ],
    notification_body_hex: '013600030000010000ff0206040003827000010000600100ff0209081234567890abcdef00030100010800ff020209060400bc614e110112',
    raw_hex: mockFrames[0].hex.substring(16),
  },
  matched_objects: [
    {
      class_id: 3,
      obis: '1-0:1.8.0.255',
      name: '正向有功总电能',
      description: '总正向有功电能（kWh）',
      unit: 'kWh',
      scaler: -2,
    },
    {
      class_id: 1,
      obis: '0-0:96.1.0.255',
      name: '设备序列号',
      description: '电表唯一标识',
      unit: '',
      scaler: 0,
    },
  ],
  parse_logs: [
    { level: 'info', step: 'input', message: '输入数据 69 字节', timestamp: new Date().toISOString() },
    { level: 'info', step: 'wrapper', message: 'Wrapper解析成功: version=1, src=1, dst=16, length=61', timestamp: new Date().toISOString() },
    { level: 'debug', step: 'ciphering', message: '未检测到加密', timestamp: new Date().toISOString() },
    { level: 'info', step: 'apdu', message: 'APDU解析成功: type=DataNotification (tag=15)', timestamp: new Date().toISOString() },
  ],
  errors: [],
}

// 模拟加密帧解析结果
export const mockEncryptedParseResult = {
  frameId: 'mock-frame-002',
  timestamp: new Date().toISOString(),
  rawHex: mockFrames[1].hex,
  wrapper: {
    version: 1,
    src_wport: 1,
    dst_wport: 16,
    data_length: 91,
    payload_hex: '134953453131303733040000000149efceb37f5076070508d86460e0edfc588f86911116af7741fef95e4b3f0688320fa353ea19a5a8b3aabae7abbf31087770409afe663ed82e760c63a892d93f24a68a5afb158c76819373c13f',
  },
  ciphering: {
    security_control: '13',
    security_control_byte: 19,
    system_title: '4953453131303733',
    invocation_counter: 1,
    ciphered_data_hex: '49efceb37f5076070508d86460e0edfc588f86911116af7741fef95e4b3f0688320fa353ea19a5a8b3aabae7abbf31087770409afe663ed82e760c63a892d93f24',
    gmac_tag: 'a68a5afb158c76819373c13f',
    decrypt_success: true,
    cipher_info: {
      encrypted: true,
      authenticated: true,
      compressed: false,
      key_id: 1,
    },
  },
  compression: null,
  apdu: {
    tag: 15,
    type_name: 'DataNotification',
    invoke_id: 1,
    items: [],
    raw_hex: '0f00000001013600030000010000ff0206040003827000010000600100ff0209081234567890abcdef00030100010800ff020209060400bc614e110112',
  },
  matched_objects: [],
  parse_logs: [
    { level: 'info', step: 'input', message: '输入数据 99 字节', timestamp: new Date().toISOString() },
    { level: 'info', step: 'wrapper', message: 'Wrapper解析成功: version=1, src=1, dst=16, length=91', timestamp: new Date().toISOString() },
    { level: 'info', step: 'ciphering', message: '检测到加密帧', timestamp: new Date().toISOString() },
    { level: 'info', step: 'ciphering', message: '解密成功，明文 61 字节', timestamp: new Date().toISOString() },
    { level: 'info', step: 'apdu', message: 'APDU解析成功: type=DataNotification (tag=15)', timestamp: new Date().toISOString() },
  ],
  errors: [],
}

// 获取默认帧
export function getDefaultFrame() {
  return mockFrames[0]
}

// 根据ID获取帧
export function getFrameById(id) {
  return mockFrames.find(f => f.id === id)
}

// 获取帧名称列表（用于下拉选择）
export function getFrameList() {
  return mockFrames.map(f => ({
    id: f.id,
    name: f.name,
    description: f.description,
    type: f.type,
    security: f.security,
  }))
}

export default {
  mockFrames,
  mockSecurityConfig,
  mockParseResult,
  mockEncryptedParseResult,
  getDefaultFrame,
  getFrameById,
  getFrameList,
}
