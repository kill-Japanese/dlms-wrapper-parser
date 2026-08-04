import { Descriptions, Tag, Typography, Progress, Space } from 'antd'
import { CompressOutlined, ArrowsAltOutlined } from '@ant-design/icons'
import { formatBytes } from '../../utils/formatters.js'

const { Text } = Typography

function CompressionLayer({ data }) {
  if (!data) return null

  const { enabled, algorithm, originalSize, compressedSize, ratio, decompressed } = data

  const compressionPercent = ratio ? Math.round((1 - ratio) * 100) : 0

  return (
    <div>
      <Space style={{ marginBottom: 12 }}>
        {enabled ? (
          <Tag color="success" icon={<CompressOutlined />}>
            {decompressed ? '已解压' : '已压缩'}
          </Tag>
        ) : (
          <Tag color="default">未压缩</Tag>
        )}
        {algorithm && <Tag color="blue">{algorithm}</Tag>}
      </Space>

      <Descriptions size="small" column={2} bordered>
        <Descriptions.Item label="压缩算法">
          <Text>{algorithm || 'N/A'}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="状态">
          {decompressed ? (
            <Tag color="success">已解压</Tag>
          ) : enabled ? (
            <Tag color="warning">已压缩</Tag>
          ) : (
            <Tag color="default">未压缩</Tag>
          )}
        </Descriptions.Item>
        <Descriptions.Item label="原始大小">
          <Space>
            <ArrowsAltOutlined />
            <Text strong>{formatBytes(originalSize)}</Text>
          </Space>
        </Descriptions.Item>
        <Descriptions.Item label="压缩后大小">
          <Space>
            <CompressOutlined />
            <Text strong>{formatBytes(compressedSize)}</Text>
          </Space>
        </Descriptions.Item>
      </Descriptions>

      {ratio && (
        <div style={{ marginTop: 12 }}>
          <Space direction="vertical" style={{ width: '100%' }} size={4}>
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                压缩比
              </Text>
              <Text strong style={{ fontSize: 12 }}>
                {(ratio * 100).toFixed(1)}%
              </Text>
            </Space>
            <Progress
              percent={compressionPercent}
              size="small"
              status="success"
              format={() => `节省 ${compressionPercent}%`}
            />
          </Space>
        </div>
      )}
    </div>
  )
}

export default CompressionLayer
