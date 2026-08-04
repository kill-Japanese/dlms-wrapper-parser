import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout, ConfigProvider, theme } from 'antd'
import { useState } from 'react'
import Header from './components/layout/Header.jsx'
import Sidebar from './components/layout/Sidebar.jsx'
import MainContent from './components/layout/MainContent.jsx'
import ParserPage from './pages/ParserPage.jsx'
import DataModelPage from './pages/DataModelPage.jsx'
import StreamPage from './pages/StreamPage.jsx'
import LogsPage from './pages/LogsPage.jsx'
import PullPresetsPage from './pages/PullPresetsPage.jsx'

const { Content } = Layout

function App() {
  const [collapsed, setCollapsed] = useState(false)
  const [darkMode, setDarkMode] = useState(false)

  const toggleCollapsed = () => {
    setCollapsed(!collapsed)
  }

  const toggleTheme = () => {
    setDarkMode(!darkMode)
  }

  return (
    <ConfigProvider
      theme={{
        algorithm: darkMode ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: { colorPrimary: '#1677ff' }
      }}
    >
      <Layout style={{ minHeight: '100vh' }}>
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
