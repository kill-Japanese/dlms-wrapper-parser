import { Layout, Menu } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  CodeOutlined,
  DatabaseOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  ExperimentOutlined
} from '@ant-design/icons'

const { Sider } = Layout

const menuItems = [
  {
    key: '/',
    icon: <CodeOutlined />,
    label: '解析器'
  },
  {
    key: '/datamodel',
    icon: <DatabaseOutlined />,
    label: '数模管理'
  },
  {
    key: '/stream',
    icon: <ThunderboltOutlined />,
    label: '实时流'
  },
  {
    key: '/logs',
    icon: <FileTextOutlined />,
    label: '日志'
  }
]

function Sidebar({ collapsed }) {
  const navigate = useNavigate()
  const location = useLocation()

  const handleClick = ({ key }) => {
    navigate(key)
  }

  return (
    <Sider
      trigger={null}
      collapsible
      collapsed={collapsed}
      width={220}
      style={{
        overflow: 'auto',
        height: '100vh',
        position: 'sticky',
        top: 0,
        left: 0
      }}
    >
      <div
        style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)'
        }}
      >
        {collapsed ? (
          <ExperimentOutlined style={{ fontSize: 24, color: '#fff' }} />
        ) : (
          <span style={{ color: '#fff', fontSize: 16, fontWeight: 600 }}>
            DLMS 工具箱
          </span>
        )}
      </div>

      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={handleClick}
        style={{ borderRight: 0 }}
      />
    </Sider>
  )
}

export default Sidebar
