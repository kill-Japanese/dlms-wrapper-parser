import { Layout, Button, Space, Switch, Typography, Tooltip } from 'antd'
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  BulbOutlined,
  BulbFilled,
  GithubOutlined
} from '@ant-design/icons'

const { Header: AntHeader } = Layout
const { Title } = Typography

function Header({ collapsed, onToggleCollapsed, darkMode, onToggleTheme }) {
  return (
    <AntHeader
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 16px',
        background: darkMode ? '#001529' : '#fff',
        boxShadow: '0 1px 4px rgba(0, 21, 41, 0.08)',
        zIndex: 10
      }}
    >
      <Space size="middle" align="center">
        <Button
          type="text"
          icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={onToggleCollapsed}
          style={{ fontSize: '16px', width: 64, height: 64 }}
        />
        <Title level={4} style={{ margin: 0, color: darkMode ? '#fff' : 'rgba(0, 0, 0, 0.88)' }}>
          DLMS Wrapper 解析器
        </Title>
      </Space>

      <Space size="middle" align="center">
        <Tooltip title={darkMode ? '切换到亮色模式' : '切换到暗色模式'}>
          <Button
            type="text"
            icon={darkMode ? <BulbFilled /> : <BulbOutlined />}
            onClick={onToggleTheme}
            style={{ color: darkMode ? '#faad14' : 'inherit' }}
          />
        </Tooltip>
        <Tooltip title="GitHub">
          <Button type="text" icon={<GithubOutlined />} href="#" target="_blank" />
        </Tooltip>
      </Space>
    </AntHeader>
  )
}

export default Header
