# VPS 部署指南 - NB 设备 TCP 接入

## 适用场景

- NB-IoT / 蜂窝模组通过 **原始 TCP** 上报 DLMS/COSEM 数据
- 需要公网 IP + 固定 TCP 端口（默认 4059）
- Render / Heroku 等 PaaS 平台不支持公网 TCP，**必须使用 VPS**

## 前置条件

- 一台 VPS（推荐 Ubuntu 22.04 / Debian 12，1核 1G 即可）
- VPS 有公网 IP
- 防火墙/安全组已开放端口：8000（HTTP）和 4059（TCP）

## 一键部署（推荐）

```bash
# 1. 登录 VPS，克隆仓库
git clone https://github.com/kill-Japanese/dlms-wrapper-parser.git
cd dlms-wrapper-parser

# 2. 运行部署脚本（自动安装 Docker、构建、启动）
chmod +x deploy-vps.sh
./deploy-vps.sh
```

脚本会自动完成：
1. 检查并启动 Docker
2. 创建数据持久化目录
3. 构建镜像（前端 + 后端）
4. 启动容器
5. 输出公网访问地址

## 手动部署

```bash
# 安装 Docker（如未安装）
curl -fsSL https://get.docker.com | sh

# 克隆仓库
git clone https://github.com/kill-Japanese/dlms-wrapper-parser.git
cd dlms-wrapper-parser

# 创建数据目录
mkdir -p data

# 构建并启动
docker compose up -d --build

# 查看日志
docker compose logs -f
```

## 防火墙配置

```bash
# Ubuntu / Debian (UFW)
sudo ufw allow 8000/tcp   # HTTP API + Web 界面
sudo ufw allow 4059/tcp   # NB 设备 TCP 接入
sudo ufw reload

# CentOS / RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --permanent --add-port=4059/tcp
sudo firewall-cmd --reload
```

> 如果使用云服务商（阿里云/腾讯云/AWS），还需在**安全组规则**中放行上述端口。

## 部署验证

```bash
# 1. 健康检查
curl http://你的VPS_IP:8000/health
# 预期: {"status":"healthy","tcp_server_running":true,...}

# 2. TCP 端口测试
nc -zv 你的VPS_IP 4059
# 预期: Connection to 你的VPS_IP 4059 port [tcp/*] succeeded!

# 3. 打开 Web 界面
# 浏览器访问: http://你的VPS_IP:8000
```

## NB 设备配置

| 参数 | 值 |
|---|---|
| 服务器地址 | 你的VPS公网IP |
| TCP 端口 | 4059 |
| 协议 | DLMS/COSEM over TCP (Wrapper) |
| Wrapper 版本 | 1 |
| 源 WPort | 1（设备侧） |
| 目的 WPort | 16（服务器侧） |

## 运维命令

```bash
# 查看日志
docker compose logs -f

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 更新代码后重新部署
git pull origin main
docker compose up -d --build

# 查看容器状态
docker compose ps

# 进入容器调试
docker exec -it dlms-parser bash
```

## 端口说明

| 端口 | 协议 | 用途 |
|---|---|---|
| 8000 | HTTP | API + Web 界面 + WebSocket |
| 4059 | TCP | NB 设备 DLMS Wrapper 帧接入 |

## 数据持久化

| 容器路径 | 宿主机路径 | 说明 |
|---|---|---|
| /app/backend/app/services/data | ./data | Capture Objects 配置 |

## 加密密钥配置（可选）

如果 NB 设备发送加密数据，通过环境变量配置密钥：

```yaml
# docker-compose.yml 中添加环境变量
environment:
  - DEFAULT_ENCRYPTION_KEY=你的GUEK密钥十六进制
  # 或通过前端界面手动输入
```

## 常见问题

### Q: TCP 端口连不上？
1. 检查防火墙：`sudo ufw status`
2. 检查安全组规则（云服务商控制台）
3. 检查容器状态：`docker compose ps`
4. 检查 TCP 服务器：`curl http://localhost:8000/api/tcp/status`

### Q: Web 界面打不开？
1. 确认 8000 端口已开放
2. 检查健康检查：`curl http://localhost:8000/health`
3. 查看日志：`docker compose logs`

### Q: NB 设备数据收不到？
1. 确认 TCP 服务器已启动：`curl http://localhost:8000/api/tcp/status` → `running: true`
2. 确认 NB 设备配置的 IP 和端口正确
3. 查看连接列表：`curl http://localhost:8000/api/tcp/clients`
4. 检查 Wrapper 帧格式是否正确

## Render vs VPS 对比

| 维度 | Render | VPS + Docker |
|---|---|---|
| 公网 TCP | 不支持 | 支持 |
| HTTP API | 支持 | 支持 |
| WebSocket | 支持 | 支持 |
| 数据持久化 | 临时（重启丢失） | 持久化（数据卷） |
| 费用 | 免费层 | VPS 费用 |
| NB 设备 TCP 接入 | 不可用 | 完全支持 |
