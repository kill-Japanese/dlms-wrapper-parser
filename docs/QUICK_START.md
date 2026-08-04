# 快速上手指南

5 分钟将 DLMS Wrapper Parser 部署到 Render 并运行起来。

---

## 快速开始（3 步部署）

### 第 1 步：准备好代码仓库

确保你的 GitHub 仓库 `kill-Japanese/dlms-wrapper-parser` 的 main 分支已有完整代码（当前已就绪 ✅）。

### 第 2 步：Render 一键部署

1. 登录 [Render.com](https://render.com)（GitHub 账号直接登录）
2. 点击 **New +** → **Blueprint**
3. 选择 `dlms-wrapper-parser` 仓库
4. Blueprint Name 填 `dlms-parser`
5. 点击 **Apply**
6. 等待 3-5 分钟部署完成

### 第 3 步：验证访问

部署成功后：
- 前端：`https://dlms-parser-frontend.onrender.com`
- 后端 API 文档：`https://dlms-parser-backend.onrender.com/docs`

---

## 本地开发快速启动

### 后端启动

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- API 地址：http://localhost:8000
- API 文档：http://localhost:8000/docs

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

- 前端地址：http://localhost:3000
- API 已代理到后端（`/api` → `http://localhost:8000`）

---

## 功能使用指南

### 1. 解析 DLMS 帧数据

1. 打开「解析器」页面
2. 在左侧输入框粘贴十六进制数据
3. 配置安全参数（密钥、System Title 等）
4. 点击「解析」按钮
5. 右侧分层展示解析结果

### 2. 上传数模文件

1. 打开「数模管理」页面
2. 点击「上传数模」按钮
3. 选择 Excel 文件（支持 SABESP 格式）
4. 上传完成后可在列表中浏览所有对象
5. 支持按名称/OBIS 搜索

### 3. 实时流 / TCP 服务器

**注意：Render 平台不支持原生 TCP，此功能需本地部署或 VPS 部署。**

1. 打开「实时流」页面
2. 启动 TCP 服务器（默认端口 4059）
3. 设备连接后显示在设备列表中
4. 设备推送的数据实时显示在帧时间线中
5. 可选择设备并发送 GetRequest（Pull 操作）

### 4. 自动处理流程

收到 DataNotification 后自动执行预设操作：

1. 调用 `PUT /api/auto/config` 配置自动处理
2. 设置 `operation_mode = "pull_then_confirm"`
3. 添加预设 Pull 操作列表
4. 收到 DataNotification 后自动触发：Pull → Confirm

---

## 测试数据使用

### 测试密钥（仅用于测试）

```
Block Cipher Key: 00112233445566778899AABBCCDDEEFF
System Title: 4953453131303733 (ISK11073)
Invocation Counter: 1
```

### 测试帧数据

可在后端测试文件中找到完整测试帧：
- `backend/tests/test_data/test_frames.py`

快速测试：在后端运行
```bash
cd backend
python -m pytest tests/ -v
```

---

## API 速查

### 解析接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/parse/hex` | 解析十六进制数据 |
| POST | `/api/parse/file` | 解析上传的文件 |
| POST | `/api/build` | 构造 DLMS 帧 |

### 数模接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/datamodel/upload` | 上传数模 Excel |
| GET | `/api/datamodel/list` | 获取对象列表 |
| GET | `/api/datamodel/search` | 搜索 OBIS 对象 |

### TCP/流接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tcp/status` | TCP 服务器状态 |
| POST | `/api/tcp/start` | 启动 TCP 服务 |
| POST | `/api/tcp/stop` | 停止 TCP 服务 |
| GET | `/api/tcp/clients` | 已连接设备列表 |
| POST | `/api/tcp/send` | 向设备发送数据 |
| WS | `/ws/stream` | WebSocket 实时流 |

### 自动处理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/auto/config` | 获取自动处理配置 |
| PUT | `/api/auto/config` | 更新自动处理配置 |
| POST | `/api/auto/trigger` | 手动触发自动处理 |
| GET | `/api/auto/status` | 自动处理模块状态 |

### 其他

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/docs` | Swagger API 文档 |
| GET | `/redoc` | ReDoc API 文档 |

---

## 项目结构速览

```
dlms-wrapper-parser/
├── backend/                    # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py             # 入口
│   │   ├── routers/            # API 路由
│   │   ├── services/           # 业务逻辑
│   │   │   ├── dlms_stack.py   #   协议栈总控
│   │   │   ├── wrapper.py      #   Wrapper 层
│   │   │   ├── ciphering.py    #   AES-GCM 加解密
│   │   │   ├── compression.py  #   V.44 压缩
│   │   │   ├── apdu_parser.py  #   APDU 解析器
│   │   │   ├── datamodel.py    #   数模管理
│   │   │   ├── tcp_server.py   #   TCP 服务器
│   │   │   ├── auto_handler.py #   自动处理流程
│   │   │   └── log_manager.py  #   日志管理
│   │   ├── models/             # Pydantic 模型
│   │   ├── utils/              # 工具函数
│   │   └── v44/                # V.44 压缩模块
│   ├── tests/                  # 单元测试
│   └── requirements.txt
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── components/         # UI 组件
│   │   ├── pages/              # 页面组件
│   │   ├── store/              # Zustand 状态
│   │   ├── services/           # API 封装
│   │   └── mocks/              # Mock 数据
│   └── package.json
├── docs/                       # 文档
│   ├── RENDER_DEPLOYMENT.md    # Render 完整部署指南
│   └── QUICK_START.md          # 本文档
├── render.yaml                 # Render 部署配置
└── README.md                   # 项目说明
```

---

## 协议栈处理流程

### 解包（接收方向）

```
原始字节流
    ↓
Wrapper 解析（8字节头）
    ↓
加密层判断 → AES-GCM 解密
    ↓
压缩层判断 → V.44 解压
    ↓
APDU 解析 → DataNotification / GetResponse 等
    ↓
OBIS 数模匹配 → 对象名称标注
    ↓
前端展示
```

### 打包（发送方向）

```
用户参数（对象、操作类型）
    ↓
APDU 编码 → GetRequest / SetRequest 等
    ↓
V.44 压缩（可选）
    ↓
AES-GCM 加密（可选）
    ↓
Wrapper 封装（8字节头）
    ↓
TCP/WebSocket 发送
```

---

## 常见问题速查

**Q: Render 上 TCP 服务器能用吗？**
A: 不能。Render 只支持 HTTP/HTTPS/WebSocket。请用 WebSocket 方式接入，或部署到 VPS。

**Q: 上传的数模文件会丢失吗？**
A: 会。Render 文件系统是临时的，重启后丢失。每次使用重新上传即可。

**Q: 免费版响应慢？**
A: 15分钟无请求会休眠，首次访问需要 5-30 秒唤醒。付费版可解决。

**Q: 支持哪些 APDU 类型？**
A: DataNotification, GetRequest/Response, SetRequest/Response, ActionRequest/Response, EventNotification, GeneralGloCiphering 等。

**Q: 支持哪些 COSEM 数据类型？**
A: 所有标准类型：array, structure, bool, bit-string, int8-64, uint8-64, octet-string, visible-string, utf8-string, enum, float32/64, date-time, date, time, compact-array 等。

---

## 获得帮助

- 完整部署文档：[`docs/RENDER_DEPLOYMENT.md`](RENDER_DEPLOYMENT.md)
- API 文档：部署后访问 `/docs`
- 项目仓库：https://github.com/kill-Japanese/dlms-wrapper-parser
