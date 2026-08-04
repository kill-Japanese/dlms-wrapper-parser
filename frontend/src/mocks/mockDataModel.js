/**
 * 模拟数据模型 (COSEM Data Model)
 *
 * 包含常见的DLMS/COSEM对象定义，用于前端开发测试。
 * 模拟从Excel导入的数模数据。
 */

// COSEM 类定义
export const cosemClasses = [
  {
    class_id: 1,
    name: 'Data',
    description: '通用数据对象',
    attributes: [
      { id: 1, name: 'logical_name', description: '逻辑名（OBIS码）' },
      { id: 2, name: 'value', description: '值' },
    ],
    methods: [],
  },
  {
    class_id: 3,
    name: 'Register',
    description: '寄存器对象（带标度和单位）',
    attributes: [
      { id: 1, name: 'logical_name', description: '逻辑名（OBIS码）' },
      { id: 2, name: 'value', description: '当前值' },
      { id: 3, name: 'scaler_unit', description: '标度和单位' },
    ],
    methods: [
      { id: 1, name: 'reset', description: '重置' },
    ],
  },
  {
    class_id: 4,
    name: 'Extended Register',
    description: '扩展寄存器对象',
    attributes: [
      { id: 1, name: 'logical_name', description: '逻辑名（OBIS码）' },
      { id: 2, name: 'value', description: '当前值' },
      { id: 3, name: 'scaler_unit', description: '标度和单位' },
      { id: 4, name: 'status', description: '状态' },
      { id: 5, name: 'capture_time', description: '捕获时间' },
    ],
    methods: [],
  },
  {
    class_id: 5,
    name: 'Demand Register',
    description: '需量寄存器对象',
    attributes: [
      { id: 1, name: 'logical_name', description: '逻辑名（OBIS码）' },
      { id: 2, name: 'current_average_value', description: '当前平均值' },
      { id: 3, name: 'last_average_value', description: '上次平均值' },
    ],
    methods: [
      { id: 1, name: 'reset', description: '重置当前值' },
    ],
  },
  {
    class_id: 7,
    name: 'Profile Generic',
    description: '通用负荷曲线对象',
    attributes: [
      { id: 1, name: 'logical_name', description: '逻辑名（OBIS码）' },
      { id: 2, name: 'buffer', description: '数据缓冲区' },
      { id: 3, name: 'captured_objects', description: '捕获对象列表' },
      { id: 7, name: 'entries', description: '条目数' },
    ],
    methods: [
      { id: 1, name: 'reset', description: '清空缓冲区' },
    ],
  },
  {
    class_id: 8,
    name: 'Clock',
    description: '时钟对象',
    attributes: [
      { id: 1, name: 'logical_name', description: '逻辑名（OBIS码）' },
      { id: 2, name: 'time', description: '时间' },
      { id: 3, name: 'time_zone', description: '时区' },
      { id: 4, name: 'status', description: '时钟状态' },
    ],
    methods: [
      { id: 1, name: 'adjust_to_quarter', description: '调整到刻钟' },
      { id: 2, name: 'adjust_to_measuring_period', description: '调整到测量周期' },
      { id: 3, name: 'preset_adjusting_time', description: '预设调整时间' },
      { id: 4, name: 'shift_time', description: '偏移时间' },
    ],
  },
  {
    class_id: 15,
    name: 'Data Protection',
    description: '数据保护对象',
    attributes: [
      { id: 1, name: 'logical_name', description: '逻辑名（OBIS码）' },
    ],
    methods: [],
  },
  {
    class_id: 17,
    name: 'SAP Assignment',
    description: 'SAP分配对象',
    attributes: [
      { id: 1, name: 'logical_name', description: '逻辑名（OBIS码）' },
      { id: 2, name: 'sap_assignment_list', description: 'SAP分配列表' },
    ],
    methods: [],
  },
  {
    class_id: 19,
    name: 'Security Setup',
    description: '安全设置对象',
    attributes: [
      { id: 1, name: 'logical_name', description: '逻辑名（OBIS码）' },
      { id: 2, name: 'security_policy', description: '安全策略' },
      { id: 3, name: 'security_suite', description: '安全套件' },
    ],
    methods: [
      { id: 1, name: 'activate', description: '激活' },
    ],
  },
]

// 模拟的数模对象列表
export const mockDataModelObjects = [
  // 电能相关
  {
    id: 1,
    class_id: 3,
    class_name: 'Register',
    obis: '1-0:1.8.0.255',
    name: '正向有功总电能',
    description: '总正向有功电能（累计）',
    unit: 'kWh',
    scaler: -2,
    attribute_id: 2,
    group: '电能计量',
  },
  {
    id: 2,
    class_id: 3,
    class_name: 'Register',
    obis: '1-0:2.8.0.255',
    name: '反向有功总电能',
    description: '总反向有功电能（累计）',
    unit: 'kWh',
    scaler: -2,
    attribute_id: 2,
    group: '电能计量',
  },
  {
    id: 3,
    class_id: 3,
    class_name: 'Register',
    obis: '1-0:1.8.1.255',
    name: '正向有功电能(费率1)',
    description: '费率1正向有功电能',
    unit: 'kWh',
    scaler: -2,
    attribute_id: 2,
    group: '电能计量',
  },
  {
    id: 4,
    class_id: 3,
    class_name: 'Register',
    obis: '1-0:1.8.2.255',
    name: '正向有功电能(费率2)',
    description: '费率2正向有功电能',
    unit: 'kWh',
    scaler: -2,
    attribute_id: 2,
    group: '电能计量',
  },
  {
    id: 5,
    class_id: 3,
    class_name: 'Register',
    obis: '1-0:3.8.0.255',
    name: '正向无功总电能',
    description: '总正向无功电能（累计）',
    unit: 'kvarh',
    scaler: -2,
    attribute_id: 2,
    group: '电能计量',
  },
  {
    id: 6,
    class_id: 3,
    class_name: 'Register',
    obis: '1-0:4.8.0.255',
    name: '反向无功总电能',
    description: '总反向无功电能（累计）',
    unit: 'kvarh',
    scaler: -2,
    attribute_id: 2,
    group: '电能计量',
  },
  // 电压电流
  {
    id: 7,
    class_id: 3,
    class_name: 'Register',
    obis: '1-0:32.7.0.255',
    name: 'A相电压',
    description: 'A相电压瞬时值',
    unit: 'V',
    scaler: -1,
    attribute_id: 2,
    group: '瞬时量',
  },
  {
    id: 8,
    class_id: 3,
    class_name: 'Register',
    obis: '1-0:52.7.0.255',
    name: 'B相电压',
    description: 'B相电压瞬时值',
    unit: 'V',
    scaler: -1,
    attribute_id: 2,
    group: '瞬时量',
  },
  {
    id: 9,
    class_id: 3,
    class_name: 'Register',
    obis: '1-0:72.7.0.255',
    name: 'C相电压',
    description: 'C相电压瞬时值',
    unit: 'V',
    scaler: -1,
    attribute_id: 2,
    group: '瞬时量',
  },
  {
    id: 10,
    class_id: 3,
    class_name: 'Register',
    obis: '1-0:31.7.0.255',
    name: 'A相电流',
    description: 'A相电流瞬时值',
    unit: 'A',
    scaler: -2,
    attribute_id: 2,
    group: '瞬时量',
  },
  {
    id: 11,
    class_id: 3,
    class_name: 'Register',
    obis: '1-0:51.7.0.255',
    name: 'B相电流',
    description: 'B相电流瞬时值',
    unit: 'A',
    scaler: -2,
    attribute_id: 2,
    group: '瞬时量',
  },
  {
    id: 12,
    class_id: 3,
    class_name: 'Register',
    obis: '1-0:71.7.0.255',
    name: 'C相电流',
    description: 'C相电流瞬时值',
    unit: 'A',
    scaler: -2,
    attribute_id: 2,
    group: '瞬时量',
  },
  {
    id: 13,
    class_id: 3,
    class_name: 'Register',
    obis: '1-0:1.7.0.255',
    name: '总有功功率',
    description: '三相总有功功率瞬时值',
    unit: 'kW',
    scaler: -3,
    attribute_id: 2,
    group: '瞬时量',
  },
  {
    id: 14,
    class_id: 3,
    class_name: 'Register',
    obis: '1-0:3.7.0.255',
    name: '总无功功率',
    description: '三相总无功功率瞬时值',
    unit: 'kvar',
    scaler: -3,
    attribute_id: 2,
    group: '瞬时量',
  },
  // 设备信息
  {
    id: 15,
    class_id: 1,
    class_name: 'Data',
    obis: '0-0:96.1.0.255',
    name: '设备序列号',
    description: '电表唯一标识序列号',
    unit: '',
    scaler: 0,
    attribute_id: 2,
    group: '设备信息',
  },
  {
    id: 16,
    class_id: 1,
    class_name: 'Data',
    obis: '0-0:96.1.1.255',
    name: '设备名称',
    description: '电表名称/型号',
    unit: '',
    scaler: 0,
    attribute_id: 2,
    group: '设备信息',
  },
  {
    id: 17,
    class_id: 1,
    class_name: 'Data',
    obis: '0-0:42.0.0.255',
    name: '制造厂商',
    description: '设备制造商名称',
    unit: '',
    scaler: 0,
    attribute_id: 2,
    group: '设备信息',
  },
  {
    id: 18,
    class_id: 1,
    class_name: 'Data',
    obis: '0-0:96.2.1.255',
    name: '固件版本',
    description: '固件版本号',
    unit: '',
    scaler: 0,
    attribute_id: 2,
    group: '设备信息',
  },
  // 时钟
  {
    id: 19,
    class_id: 8,
    class_name: 'Clock',
    obis: '0-0:1.0.0.255',
    name: '时钟',
    description: '电表时钟对象',
    unit: '',
    scaler: 0,
    attribute_id: 2,
    group: '时钟',
  },
  // 负荷曲线
  {
    id: 20,
    class_id: 7,
    class_name: 'Profile Generic',
    obis: '1-0:99.1.0.255',
    name: '负荷曲线1',
    description: '有功电能负荷曲线',
    unit: '',
    scaler: 0,
    attribute_id: 2,
    group: '负荷曲线',
  },
  // 安全
  {
    id: 21,
    class_id: 19,
    class_name: 'Security Setup',
    obis: '0-0:43.0.0.255',
    name: '安全设置',
    description: '安全策略和套件设置',
    unit: '',
    scaler: 0,
    attribute_id: 2,
    group: '安全',
  },
]

// 获取所有分组
export function getGroups() {
  const groups = [...new Set(mockDataModelObjects.map(obj => obj.group))]
  return groups.map(group => ({
    name: group,
    count: mockDataModelObjects.filter(obj => obj.group === group).length,
  }))
}

// 按分组获取对象
export function getObjectsByGroup(groupName) {
  return mockDataModelObjects.filter(obj => obj.group === groupName)
}

// 搜索对象
export function searchObjects(keyword) {
  if (!keyword) return mockDataModelObjects
  const kw = keyword.toLowerCase()
  return mockDataModelObjects.filter(
    obj =>
      obj.obis.toLowerCase().includes(kw) ||
      obj.name.toLowerCase().includes(kw) ||
      obj.description.toLowerCase().includes(kw) ||
      obj.class_name.toLowerCase().includes(kw)
  )
}

// 根据OBIS匹配对象
export function matchByObis(classId, obis) {
  return mockDataModelObjects.find(
    obj => obj.class_id === classId && obj.obis === obis
  )
}

// 获取统计信息
export function getStats() {
  return {
    totalObjects: mockDataModelObjects.length,
    totalClasses: new Set(mockDataModelObjects.map(o => o.class_id)).size,
    totalGroups: getGroups().length,
    groups: getGroups(),
  }
}

export default {
  cosemClasses,
  mockDataModelObjects,
  getGroups,
  getObjectsByGroup,
  searchObjects,
  matchByObis,
  getStats,
}
