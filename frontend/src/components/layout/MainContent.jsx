import { Outlet } from 'react-router-dom'
import { Card } from 'antd'

function MainContent({ children }) {
  return (
    <div style={{ height: '100%', minHeight: 'calc(100vh - 96px)' }}>
      {children || <Outlet />}
    </div>
  )
}

export default MainContent
