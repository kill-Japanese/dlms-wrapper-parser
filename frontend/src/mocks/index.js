/**
 * Mock 数据模块入口
 *
 * 导出所有mock数据，方便前端开发时引用。
 *
 * 使用方式：
 * import { mockFrames, mockDataModel } from '@/mocks'
 */

export * from './mockFrames.js'
export * from './mockDataModel.js'
export * from './mockWebSocket.js'

// 默认导出
import mockFramesModule from './mockFrames.js'
import mockDataModelModule from './mockDataModel.js'
import mockWebSocketModule from './mockWebSocket.js'

export default {
  frames: mockFramesModule,
  dataModel: mockDataModelModule,
  websocket: mockWebSocketModule,
}
