#!/bin/bash
#
# DLMS Wrapper Parser - 项目管理脚本
#
# 用法:
#   ./scripts/setup.sh           # 初始化项目（安装前后端依赖）
#   ./scripts/setup.sh backend   # 仅安装后端依赖
#   ./scripts/setup.sh frontend  # 仅安装前端依赖
#

set -e

# 切换到项目根目录
cd "$(dirname "$0")/.."

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}DLMS Wrapper Parser - 项目初始化${NC}"
echo "=================================="

TARGET="${1:-all}"

setup_backend() {
    echo ""
    echo -e "${YELLOW}设置后端环境...${NC}"

    cd backend

    if [ ! -d "venv" ]; then
        echo "创建 Python 虚拟环境..."
        python3 -m venv venv
    fi

    source venv/bin/activate

    echo "安装 Python 依赖..."
    pip install --upgrade pip
    pip install -r requirements.txt

    echo ""
    echo -e "${GREEN}后端环境设置完成${NC}"
    echo "启动命令: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
    echo "或使用: ./backend/start.sh dev"

    cd ..
}

setup_frontend() {
    echo ""
    echo -e "${YELLOW}设置前端环境...${NC}"

    cd frontend

    if command -v npm &> /dev/null; then
        echo "安装 Node.js 依赖..."
        npm install
        echo ""
        echo -e "${GREEN}前端环境设置完成${NC}"
        echo "启动命令: cd frontend && npm run dev"
    else
        echo -e "${RED}错误: 未找到 npm，请先安装 Node.js${NC}"
        exit 1
    fi

    cd ..
}

case "$TARGET" in
    backend)
        setup_backend
        ;;
    frontend)
        setup_frontend
        ;;
    all)
        setup_backend
        setup_frontend
        ;;
    *)
        echo -e "${RED}未知目标: $TARGET${NC}"
        echo "用法: $0 [backend|frontend|all]"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}项目初始化完成！${NC}"
echo ""
echo "快速启动:"
echo "  后端: cd backend && ./start.sh dev"
echo "  前端: cd frontend && npm run dev"
echo ""
echo "运行测试:"
echo "  后端: cd backend && python -m pytest tests/ -v"
