#!/bin/bash
# ============================================================
# DLMS Wrapper Parser - VPS 一键部署脚本
# 用于在 VPS 上通过 Docker 部署，支持 NB 设备通过公网 TCP 接入
# ============================================================
# 用法：
#   chmod +x deploy-vps.sh
#   ./deploy-vps.sh
# ============================================================
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${GREEN}${BOLD}========================================${NC}"
echo -e "${GREEN}${BOLD}  DLMS Wrapper Parser - VPS 部署脚本${NC}"
echo -e "${GREEN}${BOLD}========================================${NC}"
echo ""

# ------------------------------------------------------------
# 切换到脚本所在目录（项目根目录）
# ------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ------------------------------------------------------------
# 检查 Docker 是否安装
# ------------------------------------------------------------
echo -e "${CYAN}[1/5] 检查 Docker ...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: 未检测到 Docker${NC}"
    echo ""
    echo "请先安装 Docker："
    echo "  curl -fsSL https://get.docker.com | sh"
    echo "  或参考: https://docs.docker.com/engine/install/"
    exit 1
fi
DOCKER_VERSION=$(docker --version 2>/dev/null)
echo -e "${GREEN}  已安装: ${DOCKER_VERSION}${NC}"
echo ""

# ------------------------------------------------------------
# 检查 Docker Compose 是否安装
# 兼容 docker-compose (v1) 和 docker compose (v2)
# ------------------------------------------------------------
echo -e "${CYAN}[2/5] 检查 Docker Compose ...${NC}"
COMPOSE_CMD=""
if docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
    echo -e "${GREEN}  已安装: $(docker compose version 2>/dev/null | head -1)${NC}"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
    echo -e "${GREEN}  已安装: $(docker-compose --version 2>/dev/null)${NC}"
else
    echo -e "${RED}错误: 未检测到 Docker Compose${NC}"
    echo ""
    echo "请安装 Docker Compose："
    echo "  方式1 (推荐): 安装 Docker Compose 插件"
    echo "    sudo apt-get update && sudo apt-get install docker-compose-plugin"
    echo "  方式2: 安装独立版本"
    echo "    参考: https://docs.docker.com/compose/install/"
    exit 1
fi
echo ""

# ------------------------------------------------------------
# 检查 Docker 服务是否运行
# ------------------------------------------------------------
echo -e "${CYAN}[3/5] 检查 Docker 服务状态 ...${NC}"
if ! docker info &> /dev/null 2>&1; then
    echo -e "${YELLOW}  Docker 服务未运行，尝试启动 ...${NC}"
    sudo systemctl start docker 2>/dev/null || {
        echo -e "${RED}错误: 无法启动 Docker 服务${NC}"
        echo "请手动启动: sudo systemctl start docker"
        exit 1
    }
    echo -e "${GREEN}  Docker 服务已启动${NC}"
else
    echo -e "${GREEN}  Docker 服务运行中${NC}"
fi
echo ""

# ------------------------------------------------------------
# 创建数据持久化目录
# ------------------------------------------------------------
echo -e "${CYAN}[4/5] 准备数据目录 ...${NC}"
mkdir -p ./data
echo -e "${GREEN}  数据目录已就绪: ./data (持久化 capture objects 配置)${NC}"
echo ""

# ------------------------------------------------------------
# 构建并启动容器
# ------------------------------------------------------------
echo -e "${CYAN}[5/5] 构建并启动容器 ...${NC}"
echo -e "${YELLOW}  正在构建镜像，首次构建可能需要几分钟，请耐心等待 ...${NC}"
echo ""
$COMPOSE_CMD up -d --build
echo ""

# 等待服务启动
echo -e "${YELLOW}  等待服务启动 ...${NC}"
sleep 3

# ------------------------------------------------------------
# 获取公网 IP
# ------------------------------------------------------------
PUBLIC_IP="未知"
for url in "https://ifconfig.me" "https://icanhazip.com" "https://api.ipify.org"; do
    PUBLIC_IP=$(curl -s --connect-timeout 5 "$url" 2>/dev/null | tr -d '[:space:]')
    if [ -n "$PUBLIC_IP" ] && [ "$PUBLIC_IP" != "未知" ]; then
        break
    fi
done

# 获取本机内网 IP（备用）
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "未知")

# ------------------------------------------------------------
# 检查容器运行状态
# ------------------------------------------------------------
CONTAINER_STATUS=$(docker inspect --format='{{.State.Status}}' dlms-parser 2>/dev/null || echo "未找到")

# ------------------------------------------------------------
# 输出部署结果
# ------------------------------------------------------------
echo ""
echo -e "${GREEN}${BOLD}========================================${NC}"
echo -e "${GREEN}${BOLD}  部署完成！${NC}"
echo -e "${GREEN}${BOLD}========================================${NC}"
echo ""
echo -e "${BOLD}容器状态:${NC} ${CONTAINER_STATUS}"
echo ""
echo -e "${BOLD}服务访问信息:${NC}"
echo -e "  ${CYAN}Web 界面:${NC}    http://${PUBLIC_IP}:8000"
echo -e "  ${CYAN}API 文档:${NC}    http://${PUBLIC_IP}:8000/docs"
echo -e "  ${CYAN}健康检查:${NC}    http://${PUBLIC_IP}:8000/health"
echo -e "  ${CYAN}TCP (NB):${NC}    ${PUBLIC_IP}:4059"
echo ""
if [ "$PUBLIC_IP" = "未知" ]; then
    echo -e "${YELLOW}提示: 无法自动获取公网 IP，请手动查看:${NC}"
    echo -e "  curl ifconfig.me"
    echo -e "  ${CYAN}内网 IP:${NC} ${LOCAL_IP}"
    echo ""
fi

echo -e "${YELLOW}${BOLD}防火墙提示:${NC}"
echo -e "  请确保以下端口已在防火墙/安全组中开放："
echo -e "    ${CYAN}sudo ufw allow 8000/tcp${NC}    # HTTP API + Web 界面"
echo -e "    ${CYAN}sudo ufw allow 4059/tcp${NC}    # NB 设备 TCP 接入"
echo ""
echo -e "  如果使用云服务商（阿里云/腾讯云/AWS 等），还需在"
echo -e "  安全组规则中放行上述端口。"
echo ""

echo -e "${BOLD}NB 设备接入配置:${NC}"
echo -e "  NB 设备需将服务器地址配置为: ${PUBLIC_IP}"
echo -e "  TCP 端口: 4059"
echo -e "  协议: DLMS/COSEM over TCP (Wrapper)"
echo ""

echo -e "${BOLD}常用运维命令:${NC}"
echo -e "  ${CYAN}查看日志:${NC}    $COMPOSE_CMD logs -f"
echo -e "  ${CYAN}停止服务:${NC}    $COMPOSE_CMD down"
echo -e "  ${CYAN}重启服务:${NC}    $COMPOSE_CMD restart"
echo -e "  ${CYAN}重新构建:${NC}    $COMPOSE_CMD up -d --build"
echo -e "  ${CYAN}查看状态:${NC}    $COMPOSE_CMD ps"
echo ""
echo -e "${GREEN}部署脚本执行完毕。${NC}"
