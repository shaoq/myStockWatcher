#!/bin/bash
# 启动后端服务的脚本

echo "正在启动后端服务..."
cd "$(dirname "$0")"

# 检查依赖
if [ ! -f "requirements.txt" ]; then
    echo "错误: 找不到 requirements.txt"
    exit 1
fi

# 运行应用
python3 -m uvicorn app.main:app --reload --port 8000
