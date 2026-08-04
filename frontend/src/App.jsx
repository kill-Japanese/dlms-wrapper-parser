import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout, ConfigProvider, theme, Alert } from 'antd'
import { useState, useEffect } from 'react'
import Header from './components/layout/Header.jsx'
import Sidebar from './components/layout/Sidebar.jsx'
import MainContent from './components/layout/MainContent.jsx'
import ParserPage from './pages/ParserPage.jsx'
import DataModelPage from './pages/DataModelPage.jsx'
import StreamPage from './pages/StreamPage.jsx'
import LogsPage from './pages/LogsPage.jsx'
import PullPresetsPage from './pages/PullPresetsPage.jsx'
import useAppStore from './store/appStore.js'

const { Content } = Layout

function App() {
  const [collapsed, setCollapsed] = useState(false)
  const [darkMode, setDarkMode] = useState(false)

  const { backendHealth, checkBackendHealth } = useAppStore()

  // 页面加载时检查后端健康状态
  useEffect(() => {
    checkBackendHealth()

    // 每60秒重新检查一次
    const interval = setInterval(() => {
      checkBackendHealth()
    }, 60000)

    return () => clearInterval(interval)
  }, [])

  const toggleCollapsed = () => {
    setCollapsed(!collapsed)
  }

  const toggleTheme = () => {
    setDarkMode(!darkMode)
  }

  const isBackendUnhealthy = backendHealth.status === 'unhealthy'

  return (
    <ConfigProvider
      theme={{
        algorithm: darkMode ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: { colorPrimary: '#1677ff' }
      }}
    >
      <Layout style={{ minHeight: '100vh' }}>
        {/* 后端连接警告横幅 */}
        {isBackendUnhealthy && (
          <Alert
            message="后端服务连接失败"
            description={
              <span>
                {backendHealth.error || '无法连接到后端服务，部分功能可能无法正常使用。'}
                {' '}请检查后端服务是否已启动，或联系管理员。
                {backendHealth.version && (
                  <span> (版本: {backendHealth.version})</span>
                )}
              </span>
            }
            type="error"
            showIcon
            closable
            style={{ margin: 0 }}
          />
        )}

        <Sidebar collapsed={collapsed} />
        <Layout>
          <Header
            collapsed={collapsed}
            onToggleCollapsed={toggleCollapsed}
            darkMode={darkMode}
            onToggleTheme={toggleTheme}
          />
          <Content style={{ margin: '16px' }}>
            <MainContent>
              <Routes>
                <Route path="/" element={<ParserPage />} />
                <Route path="/datamodel" element={<DataModelPage />} />
                <Route path="/stream" element={<StreamPage />} />
                <Route path="/logs" element={<LogsPage />} />
                <Route path="/pull-presets" element={<PullPresetsPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </MainContent>
          </Content>
        </Layout>
      </Layout>
    </ConfigProvider>
  )
}

export default App
