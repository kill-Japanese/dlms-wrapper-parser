# DLMS WRAPPER 在线解析工具

基于 Web 的 DLMS/COSEM 协议在线解析工具，支持完整的协议栈解包/打包，COSEM 数模导入，实时日志展示和双接收通道（WebSocket + HTTP）。

## 功能特性

### 协议栈支持
- **Wrapper 层** (IEC 62056-47) - 帧格式解析/封装
- **安全层** (general-glo-ciphering) - AES-GCM 加解密/认证
- **压缩层** (V.44 Packet Method) - ITU-T V.44 数据压缩/解压
- **应用层** (COSEM APDU) - DataNotification, Get/Set/Action, Initiate 等

### 核心功能
- 完整协议栈解包：Wrapper → 解密 → 解压 → APDU 解析 → OBIS 匹配
- 完整协议栈打包：APDU 编码 → 压缩 → 加密 → Wrapper 封装
- COSEM 数模导入（Excel 格式）
- OBIS 对象匹配与数据标注
- HTTP 文件上传解析
- WebSocket 实时数据流
- TCP Socket 服务器（设备推送数据接入）
- 解析过程日志与数据交互日志
- Push/Pull 操作支持

## 技术栈

### 后端
- Python 3.10+
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
│   ├── tests/                  # 单元测试和集成测试
│   │   ├── test_data/          #   测试数据生成
│   │   │   └── test_frames.py  #     DLMS 测试帧构造
│   │   ├── test_wrapper.py     #   Wrapper 层单元测试
│   │   └── test_full_stack.py  #   完整协议栈集成测试
│   ├── start.sh                # 后端启动脚本
│   └── requirements.txt        # Python 依赖
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── components/         # UI 组件
│   │   ├── pages/              # 页面组件
│   │   ├── services/           # API/WebSocket 封装
│   │   ├── store/              # Zustand 状态管理
│   │   ├── mocks/              # Mock 测试数据
│   │   │   ├── mockFrames.js   #   模拟帧数据
│   │   │   ├── mockDataModel.js#   模拟数模数据
│   │   │   └── mockWebSocket.js#   模拟 WebSocket 消息
│   │   └── utils/              # 工具函数
│   ├── package.json
│   └── vite.config.js
├── scripts/
│   └── setup.sh                # 项目初始化脚本
├── render.yaml                 # Render 部署配置
└── README.md
```

## 快速开始

### 一键初始化

```bash
# 安装前后端所有依赖
./scripts/setup.sh all

# 仅安装后端依赖
./scripts/setup.sh backend

# 仅安装前端依赖
./scripts/setup.sh frontend
```

### 本地开发

#### 后端启动

**方式一：使用启动脚本（推荐）**
```bash
cd backend
./start.sh dev        # 开发模式（自动重载）
./start.sh prod       # 生产模式
./start.sh test       # 运行测试
```

**方式二：手动启动**
```bash
cd backend
python -m venv venv
source venv/bin/activate
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

## 测试数据使用说明

### 后端测试数据

测试数据位于 `backend/tests/test_data/`，包含完整的 DLMS 协议帧生成工具。

#### 可用的测试帧

| 帧类型 | 说明 | 安全级别 |
|--------|------|----------|
| `plain_dn` | 明文 DataNotification | 无加密无压缩 |
| `encrypted_dn` | 加密 DataNotification | AES-GCM（认证+加密） |
| `compressed_dn` | 加密+压缩 DataNotification | AES-GCM + V.44 |
| `get_request` | GetRequest | 明文 |
| `get_response` | GetResponse | 明文 |

#### 测试密钥

```
Block Cipher Key: 00112233445566778899AABBCCDDEEFF
System Title:     4953453131303733 (ISK11073)
Invocation Counter: 1
```

#### 在代码中使用测试数据

```python
from tests.test_data import (
    get_plain_wrapper_frame,
    get_encrypted_wrapper_frame,
    get_get_request_wrapper_frame,
    TEST_BLOCK_CIPHER_KEY,
    TEST_SYSTEM_TITLE,
)
from app.utils.hex_utils import bytes_to_hex

# 获取明文 DataNotification 帧
frame = get_plain_wrapper_frame()
hex_data = bytes_to_hex(frame)

# 获取加密帧
enc_frame = get_encrypted_wrapper_frame()
```

### 前端 Mock 数据

前端 Mock 数据位于 `frontend/src/mocks/`，用于无后端情况下的开发测试。

```javascript
import { mockFrames, mockParseResult, mockDataModelObjects } from '@/mocks'

// 使用模拟帧数据
const frames = mockFrames

// 使用模拟解析结果
const result = mockParseResult

// 使用模拟数模数据
const objects = mockDataModelObjects
```

### 运行测试

```bash
cd backend

# 运行所有测试
python -m pytest tests/ -v

# 运行指定测试文件
python -m pytest tests/test_full_stack.py -v

# 运行 Wrapper 单元测试
python -m pytest tests/test_wrapper.py -v
```

## 协议栈数据流

### 解包方向（接收）
```
原始字节流 → Wrapper解析 → AES-GCM解密 → V.44解压 → APDU解析 → OBIS数模匹配 → 前端展示
```

### 打包方向（发送）
```
用户参数 → APDU编码 → V.44压缩 → AES-GCM加密 → Wrapper封装 → TCP/WebSocket发送
```

## API 文档概要

### 解析接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/parse/hex` | 十六进制数据解析 |
| POST | `/api/parse/file` | 文件上传解析 |
| POST | `/api/build` | 组帧构造 |

#### 解析请求示例

```json
POST /api/parse/hex
{
  "hex_data": "000100010010003d0f00000001...",
  "encryption_key": "00112233445566778899aabbccddeeff",
  "system_title": "4953453131303733"
}
```

#### 组帧请求示例

```json
POST /api/build
{
  "apdu_type": "getrequest",
  "params": {
    "class_id": 3,
    "obis": "0-0:1.0.0.255",
    "attribute_id": 2
  },
  "src_wport": 1,
  "dst_wport": 16,
  "encrypt": false
}
```

### 数模接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/datamodel/upload` | 上传数模 Excel |
| GET | `/api/datamodel/list` | 获取对象列表 |
| GET | `/api/datamodel/search` | OBIS 搜索匹配 |

### TCP/流接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tcp/status` | TCP 服务器状态 |
| POST | `/api/tcp/start` | 启动 TCP 服务 |
| POST | `/api/tcp/stop` | 停止 TCP 服务 |
| GET | `/api/tcp/clients` | 已连接设备列表 |
| POST | `/api/tcp/send` | 向设备发送数据 |
| WS | `/ws/stream` | WebSocket 实时流 |

### 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |

## 部署到 Render

### 前置条件

1. GitHub 账号
2. Render 账号（render.com）
3. 代码已推送到 GitHub 仓库

### 部署步骤

#### 方式一：Blueprint 部署（推荐）

1. Fork 本仓库到你的 GitHub 账号
2. 登录 Render 控制台 (https://dashboard.render.com)
3. 点击 **"New"** → **"Blueprint"**
4. 选择你 Fork 的仓库
5. Render 会自动读取 `render.yaml` 配置
6. （可选）在环境变量设置中配置默认加密密钥
7. 点击 **"Apply"** 开始部署

部署完成后会自动创建两个服务：
- `dlms-parser-backend` - Python FastAPI 后端 Web 服务
- `dlms-parser-frontend` - React 前端静态站点

#### 方式二：手动部署

**后端服务：**
1. 点击 **"New"** → **"Web Service"**
2. 连接 GitHub 仓库
3. 配置：
   - **Runtime**: Python
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. 选择实例规格（Starter 即可）
5. 点击 **"Create Web Service"**

**前端静态站点：**
1. 点击 **"New"** → **"Static Site"**
2. 连接 GitHub 仓库
3. 配置：
   - **Build Command**: `cd frontend && npm install && npm run build`
   - **Publish Directory**: `frontend/dist`
4. 添加环境变量：
   - `VITE_API_BASE_URL`: 后端服务的 URL（如 `https://your-backend.onrender.com`）
5. 点击 **"Create Static Site"**

### 环境变量配置

#### 后端环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `PYTHON_VERSION` | Python 版本 | 3.11.0 |
| `APP_NAME` | 应用名称 | DLMS Wrapper Parser |
| `APP_VERSION` | 应用版本 | 1.0.0 |
| `DEFAULT_ENCRYPTION_KEY` | 默认加密密钥（十六进制，可选） | 空 |
| `LOG_LEVEL` | 日志级别 (DEBUG/INFO/WARNING/ERROR) | INFO |
| `UPLOAD_DIR` | 上传文件目录 | /tmp/uploads |
| `LOG_DIR` | 日志目录 | /tmp/logs |
| `CORS_ORIGINS` | 允许的跨域源 | * |
| `TCP_PORT` | TCP 服务器端口 | 4059 |
| `PORT` | HTTP 服务端口（Render 自动设置） | 10000 |

#### 前端环境变量（构建时）

| 变量名 | 说明 |
|--------|------|
| `VITE_API_BASE_URL` | 后端 API 基础 URL |

### Render 部署注意事项

1. **TCP 不支持**：Render 的 Web Service 只支持 HTTP/HTTPS 和 WebSocket，不支持原生 TCP。TCP Server 功能在 Render 环境下无法对外提供服务。

2. **临时文件系统**：Render 的文件系统是临时的，应用重启或部署后数据会丢失。上传的数模文件只在当前实例存活期间有效。

3. **冷启动延迟**：Free/Starter 计划会有冷启动延迟，长时间无请求后服务会休眠。

4. **加密密钥安全**：生产环境不要将加密密钥提交到代码仓库，应在 Render 控制台的 Environment 页面手动设置。

5. **WebSocket 支持**：Render 支持 WebSocket 连接，可用于实时数据流传输。

## 运行测试

```bash
cd backend

# 运行所有测试
python -m pytest tests/ -v

# 运行集成测试
python -m pytest tests/test_full_stack.py -v

# 运行单元测试
python -m pytest tests/test_wrapper.py -v

# 生成测试覆盖率报告
python -m pytest tests/ --cov=app --cov-report=html
```

## 常见问题

### Q: 如何添加自定义测试帧？

在 `backend/tests/test_data/test_frames.py` 中使用 `build_data_notification_apdu` 函数构造自定义 APDU，然后通过 `build_wpd` 和 `build_ciphered` 进行封装。

### Q: V.44 压缩模块不可用怎么办？

V.44 模块是纯 Python 实现，位于 `backend/app/v44/`。如果导入失败，检查 Python 版本是否为 3.10+。

### Q: 解密失败怎么办？

1. 确认密钥是否正确（十六进制格式，32字符=16字节）
2. 确认 System Title 是否正确（16字符=8字节）
3. 确认 Invocation Counter 是否匹配

### Q: 如何导入数模 Excel？

在前端 "数据模型" 页面上传 Excel 文件，Excel 格式需包含：class_id、obis、name、description、unit、scaler 等列。

## 许可证

MIT License
