# ============================================================
# DLMS Wrapper Parser - Docker 化部署
# 多阶段构建：第一阶段构建前端（Node.js），第二阶段运行后端（Python）
# ============================================================

# ------------------------------------------------------------
# Stage 1: 构建前端 (React + Vite)
# ------------------------------------------------------------
FROM node:18-alpine AS frontend-builder

WORKDIR /build

# 先复制 package 文件，利用 Docker 层缓存加速依赖安装
COPY frontend/package.json frontend/package-lock.json ./

# 安装前端依赖
RUN npm ci

# 复制前端源码
COPY frontend/ ./

# 构建时设置 API 基础地址为相对路径 /api
# 这样前端和后端通过同一个服务器（同源）访问，无需跨域
ENV VITE_API_BASE_URL=/api

# 构建生产版本
RUN npm run build

# ------------------------------------------------------------
# Stage 2: 运行后端 (Python FastAPI)
# ------------------------------------------------------------
FROM python:3.11-slim

WORKDIR /app

# 安装系统构建依赖（部分 Python 包可能需要编译 C 扩展）
# 安装后清理 apt 缓存以减小镜像体积
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# 安装后端 Python 依赖
# 先复制 requirements.txt 以利用层缓存
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# 复制后端源码
COPY backend/ ./backend/

# 将前端构建产物（dist）复制到后端静态文件目录
# 后端通过 StaticFiles 提供前端服务，实现单端口访问
COPY --from=frontend-builder /build/dist ./backend/app/static

# 设置环境变量
ENV HOST=0.0.0.0 \
    PORT=8000 \
    TCP_HOST=0.0.0.0 \
    TCP_PORT=4059 \
    TCP_AUTOSTART=true \
    CORS_ORIGINS=* \
    LOG_LEVEL=INFO \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 暴露端口：
#   8000 - HTTP API + 前端页面
#   4059 - TCP 端口，供 NB 设备通过公网接入
EXPOSE 8000 4059

WORKDIR /app/backend

# 启动命令：使用 uvicorn 运行 FastAPI 应用
# TCP 服务器通过 TCP_AUTOSTART=true 在应用启动时自动运行
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
