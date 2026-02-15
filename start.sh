#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
NC='\033[0m' # No Color

# 日志前缀函数 - 为日志添加时间戳和服务名前缀
log_prefix() {
    local prefix=$1
    local color=$2
    while IFS= read -r line; do
        echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] [${prefix}]${NC} $line"
    done
}

echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}   股票信息和价格检查应用 - 启动中心   ${NC}"
echo -e "${BLUE}=======================================${NC}"

# 端口清理函数
cleanup_port() {
    local port=$1
    local pid=$(lsof -ti :$port)
    if [ ! -z "$pid" ]; then
        echo -e "${GREEN}[清理]${NC} 端口 $port 已被占用 (PID: $pid)，正在释放..."
        kill -9 $pid 2>/dev/null
        sleep 1
    fi
}

# 1. 环境检查
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到 python3，请先安装 Python。${NC}"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo -e "${RED}错误: 未找到 npm，请先安装 Node.js。${NC}"
    exit 1
fi

# 2. 目录准备
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if [ ! -d "backend/app" ]; then
    echo -e "${RED}错误: 找不到 backend/app 目录。${NC}"
    exit 1
fi

# 3. 端口清理 (9000 和 3000)
cleanup_port 9000
cleanup_port 3000

# 4. 前端依赖检查
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${GREEN}[提醒]${NC} 未发现前端 node_modules，正在尝试安装..."
    cd "$ROOT_DIR/frontend" && npm install
    cd "$ROOT_DIR"
fi

# 5. 定义启动函数
start_backend() {
    echo -e "${GREEN}[后端]${NC} 正在启动 FastAPI (端口 9000)..."
    cd "$ROOT_DIR/backend"
    # 激活 conda 环境并启动后端服务
    source ~/miniconda3/etc/profile.d/conda.sh && conda activate mylearn12 && \
    python3 -m uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload 2>&1 | log_prefix "后端" "$YELLOW" &
    backend_pid=$!
}

start_frontend() {
    echo -e "${GREEN}[前端]${NC} 正在启动 Vite (端口 3000)..."
    cd "$ROOT_DIR/frontend"
    # 使用 log_prefix 为日志添加时间戳和前缀
    npm run dev -- --port 3000 --host 2>&1 | log_prefix "前端" "$CYAN" &
    frontend_pid=$!
}

# 6. 信号捕获与资源回收
exit_handler() {
    echo -e "\n${BLUE}正在停止所有服务并清理资源...${NC}"
    [ ! -z "$backend_pid" ] && kill $backend_pid 2>/dev/null
    [ ! -z "$frontend_pid" ] && kill $frontend_pid 2>/dev/null

    # 彻底清理残留
    local b_pids=$(lsof -ti :9000)
    local f_pids=$(lsof -ti :3000)
    [ ! -z "$b_pids" ] && kill -9 $b_pids 2>/dev/null
    [ ! -z "$f_pids" ] && kill -9 $f_pids 2>/dev/null

    echo -e "${BLUE}服务已安全停止。${NC}"
    exit
}

trap exit_handler SIGINT SIGTERM EXIT

# 7. 顺序启动
start_backend
sleep 3 # 等待后端初始化

if ! lsof -i :9000 > /dev/null; then
    echo -e "${RED}错误: 后端服务启动失败，请查看上方输出。${NC}"
    exit 1
fi

start_frontend
sleep 2

echo -e "${BLUE}=======================================${NC}"
echo -e "${GREEN}🚀 所有服务运行中！${NC}"
echo -e "API 文档: ${BLUE}http://localhost:9000/docs${NC}"
echo -e "前端地址: ${BLUE}http://localhost:3000${NC}"
echo -e "按 ${RED}Ctrl+C${NC} 停止服务"
echo -e "${BLUE}=======================================${NC}"

# 保持脚本运行
wait
