#!/bin/bash
#
# DLMS Wrapper Parser - 后端启动脚本
#
# 用法:
#   ./start.sh              # 生产模式启动
#   ./start.sh dev          # 开发模式启动（自动重载）
#   ./start.sh test         # 运行测试
#   ./start.sh tcp          # 启动TCP服务器模式
#

set -e

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}DLMS Wrapper Parser - Backend${NC}"
echo "================================"

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到 python3，请先安装 Python 3.10+${NC}"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}未检测到虚拟环境，正在创建...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}虚拟环境创建成功${NC}"
fi

# 激活虚拟环境
echo -e "${YELLOW}激活虚拟环境...${NC}"
source venv/bin/activate

# 检查依赖是否安装
if [ ! -f "venv/.deps_installed" ]; then
    echo -e "${YELLOW}安装 Python 依赖...${NC}"
    pip install --upgrade pip
    pip install -r requirements.txt
    touch venv/.deps_installed
    echo -e "${GREEN}依赖安装完成${NC}"
fi

# 默认配置
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-1}"
RELOAD=false

# 解析命令行参数
MODE="${1:-prod}"

case "$MODE" in
    dev)
        echo -e "${GREEN}启动模式: 开发模式${NC}"
        RELOAD=true
        export LOG_LEVEL="${LOG_LEVEL:-DEBUG}"
        ;;
    prod)
        echo -e "${GREEN}启动模式: 生产模式${NC}"
        export LOG_LEVEL="${LOG_LEVEL:-INFO}"
        ;;
    test)
        echo -e "${GREEN}运行测试...${NC}"
        python -m pytest tests/ -v
        exit $?
        ;;
    tcp)
        echo -e "${GREEN}启动模式: TCP服务器模式${NC}"
        export TCP_PORT="${TCP_PORT:-4059}"
        export AUTO_START_TCP="true"
        ;;
    *)
        echo -e "${RED}未知模式: $MODE${NC}"
        echo "用法: $0 [dev|prod|test|tcp]"
        exit 1
        ;;
esac

echo "主机: $HOST"
echo "端口: $PORT"
echo "日志级别: ${LOG_LEVEL:-INFO}"
echo ""

# 启动服务
echo -e "${GREEN}启动 FastAPI 服务...${NC}"
echo "API 文档: http://localhost:${PORT}/docs"
echo "健康检查: http://localhost:${PORT}/health"
echo ""

if [ "$RELOAD" = true ]; then
    exec uvicorn app.main:app \
        --host "$HOST" \
        --port "$PORT" \
        --reload \
        --log-level "${LOG_LEVEL:-info}"
else
    exec uvicorn app.main:app \
        --host "$HOST" \
        --port "$PORT" \
        --workers "$WORKERS" \
        --log-level "${LOG_LEVEL:-info}"
fi
