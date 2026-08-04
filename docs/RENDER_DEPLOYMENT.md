# Render 完整部署指南

本文档详细介绍如何将 DLMS Wrapper Parser 项目部署到 Render 平台。

---

## 目录

1. [部署前准备](#1-部署前准备)
2. [方式一：Blueprint 一键部署（推荐）](#2-方式一blueprint-一键部署推荐)
3. [方式二：手动分别部署](#3-方式二手动分别部署)
4. [部署后验证](#4-部署后验证)
5. [环境变量配置](#5-环境变量配置)
6. [常见问题](#6-常见问题)
7. [更新与重新部署](#7-更新与重新部署)

---

## 1. 部署前准备

### 1.1 所需账号

- ✅ **GitHub 账号** - 代码托管（已有）
- ✅ **Render 账号** - 平台部署
  - 注册地址：https://render.com/
  - 可使用 GitHub 账号直接登录

### 1.2 代码仓库

- 仓库地址：`https://github.com/kill-Japanese/dlms-wrapper-parser`
- 确保代码已推送到 GitHub 仓库的 main 分支
- 仓库根目录包含 `render.yaml` 配置文件

### 1.3 Render 免费计划说明

| 服务类型 | 免费额度 | 限制 |
|----------|----------|------|
| Web Service | 750小时/月 | 15分钟无请求则休眠，休眠后首次请求需等待 |
| Static Site | 无限 | 100GB 带宽/月 |
| PostgreSQL | 90天免费 | 需绑定信用卡 |

> **注意**：本项目使用 Web Service + Static Site，均在免费额度内。

---

## 2. 方式一：Blueprint 一键部署（推荐）

使用 `render.yaml` 配置文件，一键部署前后端两个服务。

### 步骤 1：登录 Render

访问 https://render.com/ ，使用 GitHub 账号登录。

### 步骤 2：创建 Blueprint

1. 点击右上角 **"New +"** 按钮
2. 在下拉菜单中选择 **"Blueprint"**

### 步骤 3：选择仓库

1. 点击 **"Connect account"** 授权 Render 访问你的 GitHub 账号
2. 授权完成后，在仓库列表中找到 `dlms-wrapper-parser`
3. 点击 **"Connect"** 按钮

### 步骤 4：配置 Blueprint

1. Render 会自动读取仓库根目录的 `render.yaml` 文件
2. **Blueprint Name**: 输入一个名称，例如 `dlms-parser`
3. **Branch**: 选择 `main`
4. 检查服务列表：
   - `dlms-parser-backend` (Python Web Service)
   - `dlms-parser-frontend` (Static Site)
5. 检查环境变量（可稍后修改）

### 步骤 5：应用部署

1. 点击 **"Apply"** 按钮
2. Render 开始创建并部署两个服务
3. 部署过程大约需要 3-5 分钟

### 步骤 6：等待部署完成

在 Render 控制面板可以看到两个服务的部署状态：
- 黄色 = 部署中
- 绿色 = 部署成功
- 红色 = 部署失败

部署成功后，每个服务会显示一个 `onrender.com` 的域名。

---

## 3. 方式二：手动分别部署

如果你不想使用 Blueprint，可以手动分别创建后端和前端服务。

### 3.1 部署后端（Web Service）

1. 点击 **"New +"** → **"Web Service"**
2. 选择 `dlms-wrapper-parser` 仓库，点击 **"Connect"**
3. 配置服务：
   - **Name**: `dlms-parser-backend`
   - **Region**: 选择离你近的区域（如 Singapore）
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `cd backend && pip install -r requirements.txt`
   - **Start Command**: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Starter（免费）
4. 点击 **"Create Web Service"**
5. 等待部署完成（约 2-3 分钟）
6. 记下后端服务的 URL，例如：`https://dlms-parser-backend.onrender.com`

### 3.2 部署前端（Static Site）

1. 点击 **"New +"** → **"Static Site"**
2. 选择 `dlms-wrapper-parser` 仓库，点击 **"Connect"**
3. 配置服务：
   - **Name**: `dlms-parser-frontend`
   - **Region**: 与后端相同
   - **Branch**: `main`
   - **Build Command**: `cd frontend && npm install && npm run build`
   - **Publish directory**: `frontend/dist`
4. 点击 **"Create Static Site"**
5. **重要**：添加 SPA 路由重写规则：
   - 进入前端服务的 **"Redirects and Rewrites"** 页面
   - 点击 **"Add Rule"**
   - **Type**: `Rewrite`
   - **Source**: `/*`
   - **Destination**: `/index.html`
   - 点击 **"Save"**
6. 配置环境变量（在 **Environment** 页面）：
   - **Key**: `VITE_API_BASE_URL`
   - **Value**: 你的后端服务URL，例如 `https://dlms-parser-backend.onrender.com`
   - 点击 **"Save Changes"**
7. 触发重新部署（环境变量修改后需重新构建）
8. 等待部署完成（约 2-3 分钟）
9. 记下前端服务的 URL

---

## 4. 部署后验证

### 4.1 验证后端服务

访问后端 URL + `/health`，例如：
```
https://dlms-parser-backend.onrender.com/health
```

应该返回：
```json
{"status":"ok"}
```

访问 API 文档：
```
https://dlms-parser-backend.onrender.com/docs
```

应该能看到 Swagger UI 界面。

### 4.2 验证前端服务

访问前端 URL，例如：
```
https://dlms-parser-frontend.onrender.com
```

应该能看到 DLMS Wrapper Parser 的主界面。

### 4.3 验证前后端通信

1. 在前端页面打开浏览器开发者工具（F12）
2. 切换到 **Network（网络）** 标签
3. 在前端操作一些功能（如上传数模文件）
4. 检查网络请求是否成功发送到后端
5. 确认没有 CORS 跨域错误

### 4.4 验证 WebSocket

在前端的"实时流"页面：
1. 点击连接 WebSocket
2. 检查连接状态是否变为"已连接"
3. 发送测试数据，检查是否有响应

---

## 5. 环境变量配置

### 5.1 后端环境变量

在 Render 后端服务的 **Environment** 页面配置：

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| `PYTHON_VERSION` | 否 | 3.11.0 | Python 版本 |
| `APP_NAME` | 否 | DLMS Wrapper Parser | 应用名称 |
| `APP_VERSION` | 否 | 1.0.0 | 应用版本 |
| `LOG_LEVEL` | 否 | INFO | 日志级别：DEBUG/INFO/WARNING/ERROR |
| `CORS_ORIGINS` | 否 | * | 允许的跨域源，逗号分隔 |
| `UPLOAD_DIR` | 否 | /tmp/uploads | 上传文件目录 |
| `LOG_DIR` | 否 | /tmp/logs | 日志目录 |
| `DEFAULT_ENCRYPTION_KEY` | 否 | 空 | 默认加密密钥（十六进制） |
| `TCP_PORT` | 否 | 4059 | TCP服务器端口（Render不支持外部访问） |

### 5.2 前端环境变量

在 Render 前端服务的 **Environment** 页面配置：

| 变量名 | 必需 | 说明 |
|--------|------|------|
| `VITE_API_BASE_URL` | 是 | 后端 API 地址，例如 `https://dlms-parser-backend.onrender.com` |

> **注意**：前端环境变量在**构建时**注入，修改后需要重新触发构建才能生效。

### 5.3 设置环境变量的步骤

1. 进入 Render 服务详情页
2. 点击左侧菜单的 **"Environment"**
3. 在 **"Environment Variables"** 部分添加/修改变量
4. 点击 **"Save Changes"**
5. 如果是前端服务，需要点击 **"Manual Deploy"** → **"Deploy latest commit"** 重新构建

---

## 6. 常见问题

### Q1: 后端部署失败怎么办？

**排查步骤：**
1. 进入后端服务详情页
2. 查看 **"Logs"** 中的错误信息
3. 常见原因：
   - 依赖安装失败 → 检查 `requirements.txt`
   - 启动命令错误 → 确认 `uvicorn app.main:app` 路径正确
   - 端口错误 → 必须使用 `$PORT` 变量

### Q2: 前端页面空白怎么办？

**排查步骤：**
1. 打开浏览器开发者工具（F12）
2. 查看 Console 中的错误信息
3. 常见原因：
   - API 地址配置错误 → 检查 `VITE_API_BASE_URL`
   - 构建路径错误 → 确认 `staticPublishPath: frontend/dist`
   - 路由刷新 404 → 检查 Rewrite 规则是否配置

### Q3: CORS 跨域错误怎么办？

**解决方案：**
1. 后端默认允许所有来源（`CORS_ORIGINS=*`）
2. 如果设置了具体域名，确保前端域名在白名单中
3. 检查请求的 `Origin` 头是否正确

### Q4: Render 上可以用 TCP Server 吗？

**答案：不可以。**
- Render 的 Web Service 只支持 HTTP/HTTPS 和 WebSocket
- 原生 TCP 端口无法对外暴露
- **替代方案**：
  1. 设备端使用 WebSocket 连接（推荐）
  2. 设备端使用 HTTP POST 推送数据
  3. 部署到支持 TCP 的平台（如 AWS EC2, DigitalOcean, VPS）

### Q5: 免费版休眠了怎么办？

**现象：** 15分钟无请求后，服务会进入休眠状态，首次请求需要 5-30 秒唤醒。

**解决方案：**
1. 使用 UptimeRobot 等服务定时 ping 你的后端（免费）
2. 升级到 Render 的付费计划（Starter 以上不休眠）
3. 在前端添加加载提示，告知用户首次加载可能较慢

### Q6: 上传的数模文件会丢失吗？

**答案：会的。**
- Render 的文件系统是临时的，服务重启/重新部署后数据会丢失
- **解决方案**：
  1. 每次使用时重新上传（适合临时调试）
  2. 集成 Render Disks（付费，持久化存储）
  3. 使用对象存储（如 AWS S3, Cloudflare R2）

### Q7: 如何查看应用日志？

1. 进入 Render 服务详情页
2. 点击左侧菜单的 **"Logs"**
3. 可以看到实时日志输出
4. 支持搜索和下载日志

---

## 7. 更新与重新部署

### 7.1 自动部署

代码推送到 GitHub 的 `main` 分支后，Render 会自动触发重新部署。

### 7.2 手动部署

1. 进入服务详情页
2. 点击右上角的 **"Manual Deploy"** 按钮
3. 选择 **"Deploy latest commit"**
4. 等待部署完成

### 7.3 回滚版本

1. 进入服务详情页
2. 点击 **"Events"** 标签
3. 找到要回滚的部署记录
4. 点击 **"Roll back"** 按钮

---

## 8. 费用估算

### 免费计划

| 服务 | 费用 | 说明 |
|------|------|------|
| Web Service | $0 | 750小时/月，休眠后自动唤醒 |
| Static Site | $0 | 无限使用，100GB带宽/月 |
| **总计** | **$0/月** | |

### 付费升级（Starter）

| 服务 | 费用 | 说明 |
|------|------|------|
| Web Service | $7/月 | 512MB RAM，不休眠 |
| Static Site | $0 | 不变 |
| **总计** | **$7/月** | |

> 更多定价信息：https://render.com/pricing

---

## 9. 性能优化建议

1. **启用 gzip 压缩**：Render 默认已启用
2. **前端资源优化**：Vite 构建已包含 tree-shaking 和代码分割
3. **后端连接池**：数据库连接池配置（当前无数据库，不适用）
4. **CDN 加速**：Render Static Site 自带 CDN
5. **缓存策略**：静态资源设置合适的 Cache-Control

---

## 10. 安全建议

1. **密钥管理**：
   - 不要在代码中硬编码密钥
   - 使用 Render 环境变量存储敏感信息
   - 环境变量不会在日志中暴露

2. **HTTPS**：
   - Render 默认提供 HTTPS
   - 所有 `onrender.com` 子域名都有 SSL 证书

3. **CORS**：
   - 生产环境设置具体的前端域名，不要使用 `*`
   - 在 `CORS_ORIGINS` 环境变量中配置

4. **访问控制**：
   - 如需要，可在 Render 中添加 Basic Auth 保护
   - 或在应用层实现用户登录

---

## 相关链接

- [Render 官方文档](https://render.com/docs)
- [Render Python 部署指南](https://render.com/docs/deploy-python)
- [Render Static Site 部署指南](https://render.com/docs/deploy-static-sites)
- [Render 环境变量](https://render.com/docs/environment-variables)
- [Render Blueprint 语法](https://render.com/docs/yaml-spec)
