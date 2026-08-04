# DLMS WRAPPER 在线解析工具

基于 Web 的 DLMS/COSEM 协议在线解析工具，支持完整的协议栈解包/打包，COSEM 数模导入，实时日志展示和双接收通道（WebSocket + HTTP）。

## 功能特性

### 协议栈支持
- **Wrapper 层** (IEC 62056-47) - 帧格式解析/封装
- **安全层** (general-glo-ciphering) - AES-GCM 加解密/认证
- **压缩层** (V.44 Packet Method) - ITU-T V.44 数据压缩/解压
- **应用层** (COSEM APDU) - DataNotification, Get/Set/Action, Initiate 等

### 核心功能
- ✅ 完整协议栈解包：Wrapper → 解密 → 解压 → APDU 解析 → OBIS 匹配
- ✅ 完整协议栈打包：APDU 编码 → 压缩 → 加密 → Wrapper 封装
- ✅ COSEM 数模导入（Excel 格式）
- ✅ OBIS 对象匹配与数据标注
- ✅ HTTP 文件上传解析
- ✅ WebSocket 实时数据流
- ✅ TCP Socket 服务器（设备推送数据接入）
- ✅ 解析过程日志与数据交互日志
- ✅ Push/Pull 操作支持

## 技术栈

### 后端
- Python 3.11+
- FastAPI (Web 框架)
- Uvicorn (ASGI 服务器)
- Pydantic (数据验证)
- Cryptography (AES-GCM 加解密)
- OpenPyXL / Pandas (Excel 解析)
- V.44 纯 Python 实现（已通过 Gurux 标准验证）

### 前端
- React 18 + Vite
- Ant Design 5 (UI 组件库)
- Zustand (状态管理)
- React Router DOM (路由)
- Axios (HTTP 请求)
- Day.js (日期处理)

### 部署
- Render (后端 Web Service + 前端静态站点)
- GitHub (代码托管)

## 项目结构

```
dlms-wrapper-parser/
├── backend/                    # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py             # FastAPI 入口
│   │   ├── config.py           # 配置管理
│   │   ├── routers/            # API 路由
│   │   │   ├── parse.py        #   解析/组帧 API
│   │   │   ├── datamodel.py    #   数模管理 API
│   │   │   └── stream.py       #   TCP/WebSocket 流 API
│   │   ├── services/           # 业务逻辑层
│   │   │   ├── dlms_stack.py   #   协议栈总控
│   │   │   ├── wrapper.py      #   Wrapper 层
│   │   │   ├── ciphering.py    #   加解密层 (AES-GCM)
│   │   │   ├── compression.py  #   V.44 压缩层
│   │   │   ├── apdu_parser.py  #   APDU 解析器
│   │   │   ├── datamodel.py    #   数模管理与 OBIS 匹配
│   │   │   ├── tcp_server.py   #   TCP Socket 服务器
│   │   │   └── log_manager.py  #   日志管理
│   │   ├── models/             # Pydantic 数据模型
│   │   ├── utils/              # 工具函数
│   │   └── v44/                # V.44 压缩模块
│   ├── tests/                  # 单元测试
│   └── requirements.txt        # Python 依赖
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── components/         # UI 组件
│   │   ├── pages/              # 页面组件
│   │   ├── services/           # API/WebSocket 封装
│   │   ├── store/              # Zustand 状态管理
│   │   └── utils/              # 工具函数
│   ├── package.json
│   └── vite.config.js
├── render.yaml                 # Render 部署配置
└── README.md
```

## 快速开始

### 本地开发

#### 后端启动
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端 API 文档：http://localhost:8000/docs

#### 前端启动
```bash
cd frontend
npm install
npm run dev
```

前端访问：http://localhost:3000

### TCP 服务器

TCP 服务器默认监听 4059 端口（DLMS 标准端口），可通过环境变量 `TCP_PORT` 修改。

**注意**：Render 平台不支持原生 TCP 端口，TCP Server 功能用于本地开发和自部署场景。Render 环境下请使用 WebSocket 或 HTTP 方式接入数据。

## 协议栈数据流

### 解包方向（接收）
```
原始字节流 → Wrapper解析 → AES-GCM解密 → V.44解压 → APDU解析 → OBIS数模匹配 → 前端展示
```

### 打包方向（发送）
```
用户参数 → APDU编码 → V.44压缩 → AES-GCM加密 → Wrapper封装 → TCP/WebSocket发送
```

## API 接口

### 解析接口
- `POST /api/parse/hex` - 十六进制数据解析
- `POST /api/parse/file` - 文件上传解析
- `POST /api/build` - 组帧构造

### 数模接口
- `POST /api/datamodel/upload` - 上传数模 Excel
- `GET /api/datamodel/list` - 获取对象列表
- `GET /api/datamodel/search` - OBIS 搜索匹配

### TCP/流接口
- `GET /api/tcp/status` - TCP 服务器状态
- `POST /api/tcp/start` - 启动 TCP 服务
- `POST /api/tcp/stop` - 停止 TCP 服务
- `GET /api/tcp/clients` - 已连接设备列表
- `POST /api/tcp/send` - 向设备发送数据
- `WS /ws/stream` - WebSocket 实时流

## 部署到 Render

1. Fork 本仓库到你的 GitHub 账号
2. 登录 Render 控制台
3. 点击 "New" → "Blueprint"
4. 选择本仓库，Render 会自动读取 `render.yaml`
5. 点击 "Apply" 完成部署

部署后会自动创建两个服务：
- `dlms-parser-backend` - Python FastAPI 后端
- `dlms-parser-frontend` - React 静态站点

## 运行测试

```bash
cd backend
python -m pytest tests/ -v
```

## 许可证

MIT License
